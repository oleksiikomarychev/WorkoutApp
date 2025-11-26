import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..exceptions import (
    ActiveSessionNotFoundException,
    SessionNotFoundException,
    WorkoutNotFoundException,
)
from ..metrics import (
    SESSION_CACHE_ERRORS_TOTAL,
    SESSION_CACHE_HITS_TOTAL,
    SESSION_CACHE_MISSES_TOTAL,
    WORKOUT_SESSIONS_STARTED_TOTAL,
)
from ..models import Workout, WorkoutExercise, WorkoutSession, WorkoutSet
from ..redis_client import (
    SESSION_DETAIL_TTL_SECONDS,
    get_redis,
    invalidate_session_cache,
    session_detail_key,
    session_list_key,
)
from .user_max_client import UserMaxClient

logger = structlog.get_logger(__name__)
SOCIAL_GATEWAY_URL = (os.getenv("SOCIAL_GATEWAY_URL") or "http://gateway:8000/api/v1/social").rstrip("/")
INTERNAL_GATEWAY_SECRET = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()


class SessionService:
    def __init__(self, db: AsyncSession, user_max_client: Optional[UserMaxClient] = None, user_id: str = None):
        self.db = db
        self.user_max_client = user_max_client or UserMaxClient()
        self.user_id = user_id

    async def _get_cached_session(self, session_id: int) -> Optional[dict]:
        redis = await get_redis()
        if not redis:
            return None
        key = session_detail_key(self.user_id, session_id)
        try:
            cached_value = await redis.get(key)
            if cached_value:
                SESSION_CACHE_HITS_TOTAL.inc()
                return json.loads(cached_value)
            SESSION_CACHE_MISSES_TOTAL.inc()
        except Exception as exc:
            SESSION_CACHE_ERRORS_TOTAL.inc()
            logger.warning("session_cache_get_failed", key=key, error=str(exc))
        return None

    async def _set_cached_session(self, session_id: int, payload: dict) -> None:
        redis = await get_redis()
        if not redis:
            return
        key = session_detail_key(self.user_id, session_id)
        try:
            await redis.set(key, json.dumps(payload), ex=SESSION_DETAIL_TTL_SECONDS)
        except Exception as exc:
            SESSION_CACHE_ERRORS_TOTAL.inc()
            logger.warning("session_cache_set_failed", key=key, error=str(exc))

    async def _get_cached_session_list(self) -> Optional[List[dict]]:
        redis = await get_redis()
        if not redis:
            return None
        key = session_list_key(self.user_id)
        try:
            cached_value = await redis.get(key)
            if cached_value:
                SESSION_CACHE_HITS_TOTAL.inc()
                return json.loads(cached_value)
            SESSION_CACHE_MISSES_TOTAL.inc()
        except Exception as exc:
            SESSION_CACHE_ERRORS_TOTAL.inc()
            logger.warning("session_list_cache_get_failed", key=key, error=str(exc))
        return None

    async def _set_cached_session_list(self, payload: List[dict]) -> None:
        redis = await get_redis()
        if not redis:
            return
        key = session_list_key(self.user_id)
        try:
            await redis.set(key, json.dumps(payload), ex=SESSION_DETAIL_TTL_SECONDS)
        except Exception as exc:
            SESSION_CACHE_ERRORS_TOTAL.inc()
            logger.warning("session_list_cache_set_failed", key=key, error=str(exc))

    async def start_workout_session(self, workout_id: int, started_at: datetime | None = None) -> WorkoutSession:
        result = await self.db.execute(
            select(Workout).filter(Workout.id == workout_id).filter(Workout.user_id == self.user_id)
        )
        workout = result.scalars().first()
        if not workout:
            raise WorkoutNotFoundException(workout_id)

        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id)
            .filter(WorkoutSession.user_id == self.user_id)
            .filter(WorkoutSession.status == "active")
        )
        active = result.scalars().first()
        if active:
            return active

        if started_at is None:
            started_at = datetime.now(timezone.utc)
        elif started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        naive_started_at = started_at.replace(tzinfo=None)

        session = WorkoutSession(
            workout_id=workout_id,
            started_at=naive_started_at,
            status="active",
            user_id=self.user_id,
        )
        self.db.add(session)
        if not workout.started_at:
            workout.started_at = naive_started_at
        await self.db.commit()
        await self.db.refresh(session)

        try:
            WORKOUT_SESSIONS_STARTED_TOTAL.inc()
        except Exception:
            logger.exception("Failed to increment WORKOUT_SESSIONS_STARTED_TOTAL")

        await invalidate_session_cache(self.user_id, session_ids=[session.id])
        return session

    async def _serialize_session(self, session: WorkoutSession) -> dict:
        return {
            "id": session.id,
            "workout_id": session.workout_id,
            "user_id": session.user_id,
            "status": session.status,
            "started_at": session.started_at,
            "finished_at": session.finished_at,
            "progress": session.progress,
            "macro_suggestion": session.macro_suggestion,
        }

    async def get_active_session(self, workout_id: int) -> WorkoutSession:
        cached_list = await self._get_cached_session_list()
        if cached_list is not None:
            for payload in cached_list:
                if payload.get("workout_id") == workout_id and payload.get("status") == "active":
                    session = WorkoutSession(**payload)
                    return session

        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id)
            .filter(WorkoutSession.user_id == self.user_id)
            .filter(WorkoutSession.status == "active")
        )
        session = result.scalars().first()
        if not session:
            raise ActiveSessionNotFoundException(workout_id)
        await self._set_cached_session(session.id, self._serialize_session(session))
        return session

    async def get_session_history(self, workout_id: int) -> list[WorkoutSession]:
        cached_list = await self._get_cached_session_list()
        if cached_list is not None:
            filtered = [WorkoutSession(**payload) for payload in cached_list if payload.get("workout_id") == workout_id]
            if filtered:
                return filtered

        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id)
            .filter(WorkoutSession.user_id == self.user_id)
            .order_by(WorkoutSession.id.desc())
        )
        sessions = result.scalars().all()
        if sessions:
            serialized = [self._serialize_session(s) for s in sessions]
            await self._set_cached_session_list(serialized)
        return sessions

    async def get_all_sessions(self) -> List[WorkoutSession]:
        cached_list = await self._get_cached_session_list()
        if cached_list is not None:
            return [WorkoutSession(**payload) for payload in cached_list]

        result = await self.db.execute(
            select(WorkoutSession).filter(WorkoutSession.user_id == self.user_id).order_by(WorkoutSession.id.desc())
        )
        sessions = result.scalars().all()
        if sessions:
            serialized = [self._serialize_session(s) for s in sessions]
            await self._set_cached_session_list(serialized)
        return sessions

    async def get_session_by_id(self, session_id: int) -> WorkoutSession | None:
        cached = await self._get_cached_session(session_id)
        if cached:
            return WorkoutSession(**cached)
        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.id == session_id)
            .filter(WorkoutSession.user_id == self.user_id)
        )
        session = result.scalars().first()
        if session:
            await self._set_cached_session(session_id, self._serialize_session(session))
        return session

    async def finish_session(self, session_id: int) -> WorkoutSession:
        session = await self.get_session_by_id(session_id)
        if not session:
            raise SessionNotFoundException(session_id)
        if session.status == "finished":
            return session

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.status = "finished"
        session.finished_at = finished_at
        result = await self.db.execute(
            select(Workout)
            .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
            .filter(Workout.id == session.workout_id)
        )
        workout = result.scalars().first()

        if workout:
            if not workout.completed_at:
                workout.completed_at = finished_at
            workout.status = "completed"

        await self.db.commit()
        await self.db.refresh(session)
        await invalidate_session_cache(self.user_id, session_ids=[session.id])

        return session

    async def _post_social_workout_completion(self, workout_id: int, session: WorkoutSession) -> None:
        if not SOCIAL_GATEWAY_URL:
            return

        url = f"{SOCIAL_GATEWAY_URL}/posts"
        headers = {"X-User-Id": self.user_id}
        if INTERNAL_GATEWAY_SECRET:
            headers["X-Internal-Secret"] = INTERNAL_GATEWAY_SECRET

        content = f"Completed workout #{workout_id}"

        attachment: Dict[str, object] = {"type": "workout_session"}
        try:
            if session.started_at and session.finished_at:
                try:
                    started = session.started_at
                    finished = session.finished_at
                    duration_seconds = (finished - started).total_seconds()
                    if duration_seconds > 0:
                        attachment["duration_minutes"] = int(duration_seconds // 60)
                except Exception:
                    pass
        except Exception:
            pass

        attachments = []
        if len(attachment) > 1:
            attachments.append(attachment)

        payload: Dict[str, object] = {
            "content": content,
            "scope": "public",
            "context_resource": {
                "type": "workout",
                "id": workout_id,
                "owner_id": self.user_id,
            },
            "attachments": attachments,
        }

        timeout = httpx.Timeout(3.0, connect=1.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                await client.post(url, headers=headers, json=payload)
            except Exception:
                logger.warning(
                    "_post_social_workout_completion: request failed | workout_id=%s session_id=%s",
                    workout_id,
                    session.id,
                )
                return

    async def update_progress(
        self,
        session_id: int,
        instance_id: int,
        set_id: int,
        completed: bool,
    ) -> WorkoutSession:
        session = await self.get_session_by_id(session_id)
        if not session:
            raise SessionNotFoundException(session_id)

        raw_progress = session.progress or {}
        if not isinstance(raw_progress, dict):
            raw_progress = {}
        progress = dict(raw_progress)

        raw_completed = progress.get("completed")
        if not isinstance(raw_completed, dict):
            raw_completed = {}
        completed_map = dict(raw_completed)

        key = str(int(instance_id))
        current_list = list(completed_map.get(key) or [])

        if completed:
            if set_id not in current_list:
                current_list.append(set_id)
        else:
            current_list = [sid for sid in current_list if sid != set_id]

        completed_map[key] = current_list
        progress["completed"] = completed_map
        session.progress = progress

        await self.db.commit()
        await self.db.refresh(session)
        await invalidate_session_cache(self.user_id, session_ids=[session_id])
        return session

    async def _prepare_user_max_payload(
        self, workout: Workout, session: WorkoutSession, finished_at: datetime
    ) -> Optional[list[dict]]:
        """Build payload for user-max-service using exercises-service sets.

        Rationale: Manual workouts store sets in exercises-service, not in
        workouts-service tables. Session progress tracks completion by exercise
        instance/set IDs from exercises-service. Therefore we fetch instances
        by workout_id from exercises-service and filter by completed sets.
        """
        completed_map = self._extract_completed_sets(session)
        logger.info(
            "_prepare_user_max_payload | workout_id=%s session_id=%s completed_map=%s",
            workout.id,
            session.id,
            completed_map,
        )

        # Fetch instances with sets from exercises-service
        instances = await self._fetch_instances_from_exercises_service(workout.id)

        entries: Dict[Tuple[int, int], float] = {}
        if instances:
            for inst in instances:
                try:
                    instance_id = int(inst.get("id")) if inst.get("id") is not None else None
                except Exception:
                    instance_id = None
                # Get only sets that are marked completed for this instance
                completed_set_ids: Set[int] = set()
                if instance_id is not None:
                    completed_set_ids = completed_map.get(instance_id, set())
                if not completed_set_ids:
                    continue

                try:
                    exercise_id = int(inst.get("exercise_list_id"))
                except Exception:
                    # Skip if exercise id is invalid
                    continue

                for s in inst.get("sets") or []:
                    try:
                        sid = int(s.get("id"))
                    except Exception:
                        continue
                    if sid not in completed_set_ids:
                        continue
                    entry = self._build_entry_from_dict(exercise_id, s)
                    if not entry:
                        continue
                    key = (entry["exercise_id"], entry["rep_max"])
                    entries[key] = max(entries.get(key, 0.0), entry["max_weight"])

        # Fallback: if still no entries and workouts-service has embedded sets,
        # try to build from those (generated workouts path)
        if not entries and workout.exercises:
            for exercise in workout.exercises:
                completed_set_ids = completed_map.get(exercise.id)
                if not completed_set_ids:
                    continue
                for w_set in exercise.sets:
                    if w_set.id not in completed_set_ids:
                        continue
                    entry = self._build_entry(exercise.exercise_id, w_set)
                    if not entry:
                        continue
                    key = (entry["exercise_id"], entry["rep_max"])
                    entries[key] = max(entries.get(key, 0.0), entry["max_weight"])

        if not entries:
            logger.warning(
                "No entries to sync to user-max | workout_id=%s session_id=%s",
                workout.id,
                session.id,
            )
            return None

        workout_date = finished_at.date() if finished_at else datetime.utcnow().date()
        payload = [
            {
                "exercise_id": ex_id,
                "rep_max": rep_max,
                "max_weight": max_weight,
                "date": workout_date,
            }
            for (ex_id, rep_max), max_weight in entries.items()
        ]
        logger.info(
            "Prepared user_max payload | workout_id=%s session_id=%s entries_count=%d",
            workout.id,
            session.id,
            len(payload),
        )
        return payload

    async def _compute_macro_suggestion(self, applied_plan_id: int) -> Optional[dict]:
        """Call plans-service run-macros and return a compact suggestion payload for the client UI."""
        base_url = os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005").rstrip("/")
        url = f"{base_url}/plans/applied-plans/{applied_plan_id}/run-macros"
        headers = {"X-User-Id": self.user_id}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(url, headers=headers)
                if res.status_code != 200:
                    logger.warning(
                        "SessionService.run-macros non-200 | applied_plan_id=%s status=%s body=%s",
                        applied_plan_id,
                        res.status_code,
                        res.text,
                    )
                    return None
                data = res.json() or {}
                preview = data.get("preview") or []
                # Summarize planned plan-level changes and patches
                inject_count = 0
                for item in preview:
                    for ch in item.get("plan_changes") or []:
                        if ch.get("type") == "Inject_Mesocycle":
                            inject_count += 1
                has_patches = any((item.get("patches") for item in preview))
                if inject_count == 0 and not has_patches:
                    return None
                return {
                    "applied_plan_id": applied_plan_id,
                    "summary": {
                        "inject_mesocycles": inject_count,
                        "has_patches": bool(has_patches),
                    },
                    "apply_url": f"/api/v1/plans/applied-plans/{applied_plan_id}/apply-macros",
                    "method": "POST",
                }
        except Exception:
            logger.exception(
                "SessionService._compute_macro_suggestion failed | applied_plan_id=%s",
                applied_plan_id,
            )
            return None

    def _extract_completed_sets(self, session: WorkoutSession) -> Dict[int, Set[int]]:
        raw_progress = session.progress if isinstance(session.progress, dict) else {}
        raw_completed = raw_progress.get("completed") if isinstance(raw_progress.get("completed"), dict) else {}
        result: Dict[int, Set[int]] = {}
        for instance_id_raw, set_ids in raw_completed.items():
            try:
                instance_id = int(instance_id_raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(set_ids, list):
                continue
            parsed_ids: Set[int] = set()
            for sid in set_ids:
                try:
                    parsed_ids.add(int(sid))
                except (TypeError, ValueError):
                    continue
            if parsed_ids:
                result[instance_id] = parsed_ids
        return result

    def _build_entry(self, exercise_id: int, w_set: WorkoutSet) -> Optional[dict]:
        reps = self._safe_int(w_set.volume)
        if reps is None or reps <= 0:
            logger.debug(
                "_build_entry: invalid reps | exercise_id=%s set_id=%s volume=%s",
                exercise_id,
                w_set.id,
                w_set.volume,
            )
            return None
        weight = self._safe_float(w_set.working_weight)
        if weight is None or weight <= 0:
            logger.debug(
                "_build_entry: invalid weight | exercise_id=%s set_id=%s working_weight=%s",
                exercise_id,
                w_set.id,
                w_set.working_weight,
            )
            return None
        rir = self._estimate_rir(w_set.effort)
        rep_max = reps + rir
        rep_max = max(1, min(rep_max, 30))
        logger.debug(
            "_build_entry: success | exercise_id=%s set_id=%s reps=%s weight=%s effort=%s rir=%s rep_max=%s",
            exercise_id,
            w_set.id,
            reps,
            weight,
            w_set.effort,
            rir,
            rep_max,
        )
        return {
            "exercise_id": exercise_id,
            "rep_max": rep_max,
            "max_weight": weight,
        }

    def _build_entry_from_dict(self, exercise_id: int, s: dict) -> Optional[dict]:
        """Build entry from an exercises-service set dict.

        Expected keys: 'reps', 'weight', and either 'effort' or 'rpe'.
        """
        reps = self._safe_int(s.get("reps"))
        if reps is None or reps <= 0:
            return None
        weight = self._safe_float(s.get("weight"))
        if weight is None or weight <= 0:
            return None
        # Prefer latest user-entered RPE over any stale 'effort' saved from templates
        effort_val = s.get("rpe")
        if effort_val is None:
            effort_val = s.get("effort")
        rir = self._estimate_rir(effort_val)
        rep_max = reps + rir
        rep_max = max(1, min(rep_max, 30))
        return {
            "exercise_id": exercise_id,
            "rep_max": rep_max,
            "max_weight": weight,
        }

    def _estimate_rir(self, effort_value: Optional[float]) -> int:
        if effort_value is None:
            return 0
        try:
            eff = float(effort_value)
        except (TypeError, ValueError):
            return 0
        if eff <= 4:
            rir = eff
        else:
            rir = max(0.0, 10.0 - eff)
        return max(0, min(round(rir), 10))

    def _safe_int(self, value: Optional[float]) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_float(self, value: Optional[float]) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def _fetch_instances_from_exercises_service(self, workout_id: int) -> list[dict]:
        base_url = os.getenv("EXERCISES_SERVICE_URL")
        if not base_url:
            logger.warning("EXERCISES_SERVICE_URL is not set; cannot fetch instances")
            return []
        base_url = base_url.rstrip("/")
        url = f"{base_url}/exercises/instances/workouts/{workout_id}/instances"
        headers = {"X-User-Id": self.user_id}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list):
                        return data
        except Exception:
            logger.exception("Failed to fetch instances from exercises-service for workout_id=%s", workout_id)
        return []
