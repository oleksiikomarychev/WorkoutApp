from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..exceptions import ActiveSessionNotFoundException, SessionNotFoundException, WorkoutNotFoundException
from ..models import Workout, WorkoutExercise, WorkoutSession, WorkoutSet
from .user_max_client import UserMaxClient
import logging
import httpx

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, db: AsyncSession, user_max_client: Optional[UserMaxClient] = None):
        self.db = db
        self.user_max_client = user_max_client or UserMaxClient()

    async def start_workout_session(self, workout_id: int, started_at: datetime | None = None) -> WorkoutSession:
        result = await self.db.execute(select(Workout).filter(Workout.id == workout_id))
        workout = result.scalars().first()
        if not workout:
            raise WorkoutNotFoundException(workout_id)

        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id, WorkoutSession.status == "active")
        )
        active = result.scalars().first()
        if active:
            return active

        if started_at is None:
            started_at = datetime.now(timezone.utc)
        elif started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        naive_started_at = started_at.replace(tzinfo=None)

        session = WorkoutSession(workout_id=workout_id, started_at=naive_started_at, status="active")
        self.db.add(session)
        if not workout.started_at:
            workout.started_at = naive_started_at
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_active_session(self, workout_id: int) -> WorkoutSession:
        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id, WorkoutSession.status == "active")
        )
        session = result.scalars().first()
        if not session:
            raise ActiveSessionNotFoundException(workout_id)
        return session

    async def get_session_history(self, workout_id: int) -> list[WorkoutSession]:
        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id)
            .order_by(WorkoutSession.id.desc())
        )
        return result.scalars().all()

    async def get_all_sessions(self) -> List[WorkoutSession]:
        result = await self.db.execute(
            select(WorkoutSession)
            .order_by(WorkoutSession.id.desc())
        )
        return result.scalars().all()

    async def finish_session(self, session_id: int) -> WorkoutSession:
        result = await self.db.execute(select(WorkoutSession).filter(WorkoutSession.id == session_id))
        session = result.scalars().first()
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

        sync_payload = None
        if workout:
            if not workout.completed_at:
                workout.completed_at = finished_at
            workout.status = "completed"
            try:
                sync_payload = await self._prepare_user_max_payload(workout, session, finished_at)
            except Exception:
                logger.exception("SessionService._prepare_user_max_payload failed")

        await self.db.commit()
        await self.db.refresh(session)

        if sync_payload:
            await self.user_max_client.push_entries(sync_payload)

        return session

    async def update_progress(self, session_id: int, instance_id: int, set_id: int, completed: bool = True) -> WorkoutSession:
        result = await self.db.execute(select(WorkoutSession).filter(WorkoutSession.id == session_id))
        session = result.scalars().first()
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
        raw_list = completed_map.get(key)
        if isinstance(raw_list, list):
            current_list = list(raw_list)
        else:
            current_list = []

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
            workout.id, session.id, completed_map
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

                for s in (inst.get("sets") or []):
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
                workout.id, session.id
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
            workout.id, session.id, len(payload)
        )
        return payload

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
                exercise_id, w_set.id, w_set.volume
            )
            return None
        weight = self._safe_float(w_set.working_weight)
        if weight is None or weight <= 0:
            logger.debug(
                "_build_entry: invalid weight | exercise_id=%s set_id=%s working_weight=%s",
                exercise_id, w_set.id, w_set.working_weight
            )
            return None
        rir = self._estimate_rir(w_set.effort)
        rep_max = reps + rir
        rep_max = max(1, min(rep_max, 30))
        logger.debug(
            "_build_entry: success | exercise_id=%s set_id=%s reps=%s weight=%s effort=%s rir=%s rep_max=%s",
            exercise_id, w_set.id, reps, weight, w_set.effort, rir, rep_max
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
        effort_val = s.get("effort")
        if effort_val is None:
            effort_val = s.get("rpe")
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
        base_url = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002").rstrip("/")
        url = f"{base_url}/exercises/instances/workouts/{workout_id}/instances"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list):
                        return data
        except Exception:
            logger.exception("Failed to fetch instances from exercises-service for workout_id=%s", workout_id)
        return []
