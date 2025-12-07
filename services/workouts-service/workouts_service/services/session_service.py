import os
from datetime import UTC, datetime

import httpx
import structlog
from backend_common.cache import CacheHelper, CacheMetrics
from backend_common.http_client import ServiceClient
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
    def __init__(self, db: AsyncSession, user_max_client: UserMaxClient | None = None, user_id: str = None):
        self.db = db
        self.user_max_client = user_max_client or UserMaxClient()
        self.user_id = user_id
        self._cache = CacheHelper(
            get_redis=get_redis,
            metrics=CacheMetrics(
                hits=SESSION_CACHE_HITS_TOTAL,
                misses=SESSION_CACHE_MISSES_TOTAL,
                errors=SESSION_CACHE_ERRORS_TOTAL,
            ),
            default_ttl=SESSION_DETAIL_TTL_SECONDS,
        )

    async def _get_cached_session(self, session_id: int) -> dict | None:
        return await self._cache.get(session_detail_key(self.user_id, session_id))

    async def _set_cached_session(self, session_id: int, payload: dict) -> None:
        await self._cache.set(session_detail_key(self.user_id, session_id), payload)

    async def _get_cached_session_list(self) -> list[dict] | None:
        return await self._cache.get(session_list_key(self.user_id))

    async def _set_cached_session_list(self, payload: list[dict]) -> None:
        await self._cache.set(session_list_key(self.user_id), payload)

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
            started_at = datetime.now(UTC)
        elif started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)

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

    def _serialize_session(self, session: WorkoutSession) -> dict:
        started_at = session.started_at
        finished_at = session.finished_at
        if isinstance(started_at, datetime):
            started_at = started_at.isoformat()
        if isinstance(finished_at, datetime):
            finished_at = finished_at.isoformat()
        return {
            "id": session.id,
            "workout_id": session.workout_id,
            "user_id": session.user_id,
            "status": session.status,
            "started_at": started_at,
            "finished_at": finished_at,
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

    async def get_all_sessions(self) -> list[WorkoutSession]:
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

        finished_at = datetime.now(UTC).replace(tzinfo=None)
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

        attachment: dict[str, object] = {"type": "workout_session"}
        try:
            if session.started_at and session.finished_at:
                try:
                    started = session.started_at
                    finished = session.finished_at
                    duration_seconds = (finished - started).total_seconds()
                    if duration_seconds > 0:
                        attachment["duration_minutes"] = int(duration_seconds // 60)
                except (TypeError, ValueError, AttributeError):
                    pass
        except (TypeError, AttributeError):
            pass

        attachments = []
        if len(attachment) > 1:
            attachments.append(attachment)

        payload: dict[str, object] = {
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
            except httpx.RequestError as exc:
                logger.warning(
                    "_post_social_workout_completion: request failed | workout_id=%s session_id=%s error=%s",
                    workout_id,
                    session.id,
                    exc,
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

        progress = dict(session.progress or {})
        completed_map = dict(progress.get("completed") or {})

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
    ) -> list[dict] | None:
        completed_map = self._extract_completed_sets(session)
        total_completed_sets = sum(len(v) for v in completed_map.values())
        logger.info(
            "_prepare_user_max_payload | workout_id=%s session_id=%s completed_instances=%d completed_sets=%d",
            workout.id,
            session.id,
            len(completed_map),
            total_completed_sets,
        )
        logger.debug(
            "_prepare_user_max_payload_detail | workout_id=%s session_id=%s completed_map=%s",
            workout.id,
            session.id,
            completed_map,
        )

        instances = await self._fetch_instances_from_exercises_service(workout.id)

        entries: dict[tuple[int, int], float] = {}
        for inst in instances:
            instance_id = int(inst["id"])
            completed_set_ids = completed_map.get(instance_id, set())
            if not completed_set_ids:
                continue

            exercise_id = int(inst["exercise_list_id"])
            for s in inst.get("sets") or []:
                sid = int(s["id"])
                if sid not in completed_set_ids:
                    continue
                entry = self._build_entry_from_dict(exercise_id, s)
                if not entry:
                    continue
                key = (entry["exercise_id"], entry["rep_max"])
                entries[key] = max(entries.get(key, 0.0), entry["max_weight"])

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

    async def _compute_macro_suggestion(self, applied_plan_id: int) -> dict | None:
        base_url = os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005").rstrip("/")
        url = f"{base_url}/plans/applied-plans/{applied_plan_id}/run-macros"
        headers = {"X-User-Id": self.user_id}

        async with ServiceClient(timeout=6.0) as client:
            resp = await client.post(url, headers=headers, expected_status=200, applied_plan_id=applied_plan_id)
        if not resp.success:
            return None

        data = resp.data or {}
        preview = data.get("preview") or []

        inject_count = 0
        for item in preview:
            for ch in item.get("plan_changes") or []:
                if ch.get("type") == "Inject_Mesocycle":
                    inject_count += 1
        has_patches = any(item.get("patches") for item in preview)
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

    def _extract_completed_sets(self, session: WorkoutSession) -> dict[int, set[int]]:
        progress = session.progress or {}
        completed = progress.get("completed", {})
        result: dict[int, set[int]] = {}
        for instance_id_raw, set_ids in completed.items():
            try:
                instance_id = int(instance_id_raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(set_ids, list):
                continue
            parsed_ids = {int(sid) for sid in set_ids if isinstance(sid, int | str)}
            if parsed_ids:
                result[instance_id] = parsed_ids
        return result

    def _build_entry(self, exercise_id: int, w_set: WorkoutSet) -> dict | None:
        reps = int(w_set.volume) if w_set.volume else 0
        if reps <= 0:
            return None
        weight = float(w_set.working_weight) if w_set.working_weight else 0.0
        if weight <= 0:
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

    def _build_entry_from_dict(self, exercise_id: int, s: dict) -> dict | None:
        reps = int(s["reps"])
        if reps <= 0:
            return None
        weight = float(s["weight"])
        if weight <= 0:
            return None

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

    def _estimate_rir(self, effort_value: float | None) -> int:
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

    async def _fetch_instances_from_exercises_service(self, workout_id: int) -> list[dict]:
        base_url = os.getenv("EXERCISES_SERVICE_URL")
        if not base_url:
            logger.warning("EXERCISES_SERVICE_URL is not set; cannot fetch instances")
            return []
        base_url = base_url.rstrip("/")
        url = f"{base_url}/exercises/instances/workouts/{workout_id}/instances"
        headers = {"X-User-Id": self.user_id}
        async with ServiceClient(timeout=5.0) as client:
            data = await client.get_json(url, headers=headers, default=[], workout_id=workout_id)
        return data if isinstance(data, list) else []
