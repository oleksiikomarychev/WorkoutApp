import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

import httpx
import pytz
import structlog
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models, schemas
from ..exceptions import WorkoutNotFoundException
from ..metrics import (
    GENERATED_WORKOUTS_CREATED_TOTAL,
    WORKOUT_CACHE_ERRORS_TOTAL,
    WORKOUT_CACHE_HITS_TOTAL,
    WORKOUT_CACHE_MISSES_TOTAL,
    WORKOUTS_CREATED_TOTAL,
)
from ..redis_client import (
    WORKOUT_DETAIL_TTL_SECONDS,
    WORKOUT_LIST_TTL_SECONDS,
    get_redis,
    invalidate_workout_cache,
    workout_detail_key,
    workout_list_key,
)
from ..schemas.workout import WorkoutCreate, WorkoutListResponse, WorkoutResponse, WorkoutUpdate
from ..schemas.workout_generation import WorkoutGenerationItem, WorkoutGenerationRequest
from ..workout_calculation import WorkoutCalculator
from .rpc_client import PlansServiceRPC, RpeServiceRPC

logger = structlog.get_logger(__name__)


class WorkoutService:
    def __init__(
        self,
        db: AsyncSession,
        plans_rpc: PlansServiceRPC,
        exercises_rpc: Any = None,
        user_id: str = None,
        rpe_rpc: RpeServiceRPC | None = None,
        request_headers: dict[str, str] | None = None,
    ):
        self.db = db
        self.plans_rpc = plans_rpc
        self.exercises_rpc = exercises_rpc
        self.user_id = user_id
        self.rpe_rpc = rpe_rpc
        self.request_headers = request_headers or {}

    async def _get_cached_workout(self, workout_id: int) -> Optional[dict]:
        redis = await get_redis()
        if not redis:
            return None
        key = workout_detail_key(self.user_id, workout_id)
        try:
            cached_value = await redis.get(key)
            if cached_value:
                WORKOUT_CACHE_HITS_TOTAL.inc()
                return json.loads(cached_value)
            WORKOUT_CACHE_MISSES_TOTAL.inc()
        except Exception as exc:
            WORKOUT_CACHE_ERRORS_TOTAL.inc()
            logger.warning("workout_cache_get_failed", key=key, error=str(exc))
        return None

    async def _set_cached_workout(self, workout_id: int, payload: dict) -> None:
        redis = await get_redis()
        if not redis:
            return
        key = workout_detail_key(self.user_id, workout_id)
        try:
            await redis.set(key, json.dumps(payload), ex=WORKOUT_DETAIL_TTL_SECONDS)
        except Exception as exc:
            WORKOUT_CACHE_ERRORS_TOTAL.inc()
            logger.warning("workout_cache_set_failed", key=key, error=str(exc))

    async def _get_cached_workouts_list(self, status: str | None) -> Optional[List[dict]]:
        redis = await get_redis()
        if not redis:
            return None
        key = workout_list_key(self.user_id, status)
        try:
            cached_value = await redis.get(key)
            if cached_value:
                WORKOUT_CACHE_HITS_TOTAL.inc()
                return json.loads(cached_value)
            WORKOUT_CACHE_MISSES_TOTAL.inc()
        except Exception as exc:
            WORKOUT_CACHE_ERRORS_TOTAL.inc()
            logger.warning("workout_list_cache_get_failed", key=key, error=str(exc))
        return None

    async def _set_cached_workouts_list(self, status: str | None, payload: List[dict]) -> None:
        redis = await get_redis()
        if not redis:
            return
        key = workout_list_key(self.user_id, status)
        try:
            await redis.set(key, json.dumps(payload), ex=WORKOUT_LIST_TTL_SECONDS)
        except Exception as exc:
            WORKOUT_CACHE_ERRORS_TOTAL.inc()
            logger.warning("workout_list_cache_set_failed", key=key, error=str(exc))

    def _convert_to_naive_utc(self, dt: datetime) -> datetime:
        """Convert aware datetime to naive UTC datetime"""
        if dt.tzinfo is not None:
            dt = dt.astimezone(pytz.utc)
            return dt.replace(tzinfo=None)
        return dt

    async def create_workout(self, payload: WorkoutCreate, plan_workout_id: int = None) -> WorkoutResponse:
        # Convert payload to dict and filter only valid ORM columns to avoid
        # passing unexpected kwargs like 'day' to SQLAlchemy model constructor.
        raw_data = payload.model_dump()
        valid_fields = {f.name for f in models.Workout.__table__.columns}
        filtered_data = {k: v for k, v in raw_data.items() if k in valid_fields}

        # Log any invalid/ignored fields for observability (e.g., 'day', 'exercises')
        ignored = set(raw_data.keys()) - valid_fields
        if ignored:
            logger.warning(f"Ignoring invalid fields in WorkoutCreate: {', '.join(sorted(ignored))}")

        # Convert timezone-aware datetimes to naive UTC
        for field in ["scheduled_for", "completed_at", "started_at"]:
            if field in filtered_data and filtered_data[field] is not None:
                filtered_data[field] = self._convert_to_naive_utc(filtered_data[field])

        # 'plan_workout_id' is not a column on Workout; ignore if provided
        if plan_workout_id is not None:
            logger.warning("'plan_workout_id' argument is ignored: column does not exist on models.Workout")

        item = models.Workout(**filtered_data)
        item.user_id = self.user_id
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)

        try:
            WORKOUTS_CREATED_TOTAL.labels(source="manual").inc()
        except Exception:
            logger.exception("Failed to increment WORKOUTS_CREATED_TOTAL for manual workout")

        workout_dict = {
            "id": item.id,
            "name": item.name,
            "applied_plan_id": item.applied_plan_id,
            "plan_order_index": item.plan_order_index,
            "scheduled_for": item.scheduled_for,
            "completed_at": item.completed_at,
            "notes": item.notes,
            "status": item.status,
            "started_at": item.started_at,
            "duration_seconds": item.duration_seconds,
            "rpe_session": item.rpe_session,
            "location": item.location,
            "readiness_score": item.readiness_score,
            "workout_type": item.workout_type,
            "exercises": [],
        }

        return WorkoutResponse.model_validate(workout_dict)

    async def get_workout(self, workout_id: int) -> schemas.workout.WorkoutResponse:
        cached = await self._get_cached_workout(workout_id)
        if cached:
            return schemas.workout.WorkoutResponse.model_validate(cached)

        result = await self.db.execute(
            select(models.Workout)
            .options(selectinload(models.Workout.exercises).selectinload(models.WorkoutExercise.sets))
            .where(models.Workout.id == workout_id)
            .where(models.Workout.user_id == self.user_id)
        )
        workout = result.scalars().first()
        if not workout:
            raise WorkoutNotFoundException(workout_id)

        workout_dict = {
            "id": workout.id,
            "name": workout.name,
            "applied_plan_id": workout.applied_plan_id,
            "plan_order_index": workout.plan_order_index,
            "scheduled_for": workout.scheduled_for,
            "completed_at": workout.completed_at,
            "notes": workout.notes,
            "status": workout.status,
            "started_at": workout.started_at,
            "duration_seconds": workout.duration_seconds,
            "rpe_session": workout.rpe_session,
            "location": workout.location,
            "readiness_score": workout.readiness_score,
            "workout_type": workout.workout_type,
            "exercises": [
                {
                    "id": ex.id,
                    "exercise_id": ex.exercise_id,
                    "sets": [
                        {
                            "id": s.id,
                            "intensity": s.intensity,
                            "effort": s.effort,
                            "volume": s.volume,
                            "working_weight": s.working_weight,
                            "set_type": s.set_type,
                        }
                        for s in ex.sets
                    ],
                }
                for ex in workout.exercises
            ],
        }

        await self._set_cached_workout(workout_id, workout_dict)
        return schemas.workout.WorkoutResponse.model_validate(workout_dict)

    async def list_workouts(
        self,
        skip: int = 0,
        limit: int = 100,
        type: Optional[str] = None,
        status: Optional[str] = None,
        applied_plan_id: Optional[int] = None,
    ) -> list[WorkoutListResponse]:
        # Only use cache if no filters other than type are applied
        use_cache = (applied_plan_id is None) and (status is None)

        if use_cache:
            cache_status = type or "all"
            cached_list = await self._get_cached_workouts_list(cache_status)
            if cached_list is not None:
                return [WorkoutListResponse.model_validate(w) for w in cached_list]

        query = select(models.Workout).where(models.Workout.user_id == self.user_id)
        if type:
            if type not in ["manual", "generated"]:
                raise HTTPException(status_code=400, detail=f"Invalid workout type: {type}")
            query = query.where(models.Workout.workout_type == type)
        if status:
            query = query.where(models.Workout.status == status)
        if applied_plan_id is not None:
            query = query.where(models.Workout.applied_plan_id == applied_plan_id)

        # Apply sorting: completed workouts usually sort by completed_at desc, others by scheduled_for
        if status == "completed":
            query = query.order_by(models.Workout.completed_at.desc())
        else:
            query = query.order_by(models.Workout.scheduled_for.desc())

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        workouts = result.scalars().all()

        workout_dicts = []
        for workout in workouts:
            # Convert to dict to avoid DetachedInstanceError
            workout_dict = {
                "id": workout.id,
                "name": workout.name,
                "applied_plan_id": workout.applied_plan_id,
                "plan_order_index": workout.plan_order_index,
                "scheduled_for": workout.scheduled_for,
                "status": workout.status,
                "workout_type": workout.workout_type,
            }
            workout_dicts.append(workout_dict)

        if use_cache:
            cache_status = type or "all"
            await self._set_cached_workouts_list(cache_status, workout_dicts)
        return [WorkoutListResponse.model_validate(w) for w in workout_dicts]

    async def update_workout(self, workout_id: int, payload: WorkoutUpdate) -> WorkoutResponse:
        # Fetch the ORM model directly (not the Pydantic response)
        result = await self.db.execute(
            select(models.Workout)
            .options(selectinload(models.Workout.exercises).selectinload(models.WorkoutExercise.sets))
            .where(models.Workout.id == workout_id)
            .where(models.Workout.user_id == self.user_id)
        )
        item = result.scalars().first()
        if not item:
            raise WorkoutNotFoundException(workout_id)

        # Update attributes on the ORM model
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(item, k, v)

        await self.db.commit()
        result = await self.db.execute(
            select(models.Workout)
            .options(selectinload(models.Workout.exercises).selectinload(models.WorkoutExercise.sets))
            .where(models.Workout.id == workout_id)
            .where(models.Workout.user_id == self.user_id)
        )
        item = result.scalars().first()

        # Convert ORM model to Pydantic response
        workout_dict = {
            "id": item.id,
            "name": item.name,
            "applied_plan_id": item.applied_plan_id,
            "plan_order_index": item.plan_order_index,
            "scheduled_for": item.scheduled_for,
            "completed_at": item.completed_at,
            "notes": item.notes,
            "status": item.status,
            "started_at": item.started_at,
            "duration_seconds": item.duration_seconds,
            "rpe_session": item.rpe_session,
            "location": item.location,
            "readiness_score": item.readiness_score,
            "workout_type": item.workout_type,
            "exercises": [
                {
                    "id": ex.id,
                    "exercise_id": ex.exercise_id,
                    "sets": [
                        {
                            "id": s.id,
                            "intensity": s.intensity,
                            "effort": s.effort,
                            "volume": s.volume,
                            "working_weight": s.working_weight,
                            "set_type": s.set_type,
                        }
                        for s in ex.sets
                    ],
                }
                for ex in item.exercises
            ],
        }

        await invalidate_workout_cache(self.user_id, workout_ids=[workout_id])
        await self._set_cached_workout(workout_id, workout_dict)
        return WorkoutResponse.model_validate(workout_dict)

    async def delete_workout(self, workout_id: int) -> None:
        # Fetch the ORM model directly for deletion
        result = await self.db.execute(
            select(models.Workout)
            .filter(models.Workout.id == workout_id)
            .filter(models.Workout.user_id == self.user_id)
        )
        item = result.scalars().first()
        if not item:
            raise WorkoutNotFoundException(workout_id)
        await self.db.delete(item)
        await self.db.commit()
        await invalidate_workout_cache(self.user_id, workout_ids=[workout_id])

    async def create_workouts_batch(self, workouts_data: list[WorkoutCreate]) -> list[dict]:
        created_workouts = []
        for data in workouts_data:
            # Convert to dict and filter only valid fields
            item_data = data.model_dump()
            valid_fields = {f.name for f in models.Workout.__table__.columns}
            filtered_data = {k: v for k, v in item_data.items() if k in valid_fields}

            # Log any invalid fields
            invalid_fields = set(item_data.keys()) - valid_fields
            if invalid_fields:
                logger.warning(f"Ignoring invalid fields: {', '.join(invalid_fields)}")

            # Convert timezone-aware datetimes to naive UTC
            for field in ["scheduled_for", "completed_at", "started_at"]:
                if field in filtered_data and filtered_data[field] is not None:
                    filtered_data[field] = self._convert_to_naive_utc(filtered_data[field])

            workout = models.Workout(**filtered_data)
            workout.user_id = self.user_id
            self.db.add(workout)
            await self.db.flush()

            # Return consistent dictionary format
            workout_dict = {
                "id": workout.id,
                "name": workout.name,
                "applied_plan_id": workout.applied_plan_id,
                "plan_order_index": workout.plan_order_index,
                "scheduled_for": workout.scheduled_for,
                "status": workout.status,
                "workout_type": workout.workout_type,
            }
            created_workouts.append(workout_dict)

        await self.db.commit()

        try:
            WORKOUTS_CREATED_TOTAL.labels(source="batch").inc(len(created_workouts))
        except Exception:
            logger.exception("Failed to increment WORKOUTS_CREATED_TOTAL for batch create")

        return created_workouts

    async def _create_workout(
        self,
        workout_item: WorkoutGenerationItem,
        request: WorkoutGenerationRequest,
        microcycle_id: int = None,
    ) -> models.Workout:
        """Create a workout from generation item"""
        scheduled_for = workout_item.scheduled_for
        if isinstance(scheduled_for, str):
            scheduled_for = datetime.fromisoformat(scheduled_for)

        return models.Workout(
            name=workout_item.name,
            scheduled_for=scheduled_for,
            plan_order_index=workout_item.plan_order_index,
            calendar_plan_id=request.calendar_plan_id,
            microcycle_id=microcycle_id,
            workout_type="generated",
        )

    async def _create_workout_exercise(self, workout: models.Workout, exercise: dict) -> models.WorkoutExercise:
        """Create workout exercise from exercise data"""
        exercise_id = exercise.get("exercise_id") if isinstance(exercise, dict) else exercise.exercise_id
        return models.WorkoutExercise(workout_id=workout.id, exercise_id=exercise_id)

    async def _create_workout_set(self, workout_exercise: models.WorkoutExercise, set_data: dict) -> models.WorkoutSet:
        """Create workout set from set data"""
        intensity = set_data.get("intensity") if isinstance(set_data, dict) else set_data.intensity
        effort = set_data.get("effort") if isinstance(set_data, dict) else set_data.effort
        volume = set_data.get("volume") if isinstance(set_data, dict) else set_data.volume
        working_weight = set_data.get("working_weight") if isinstance(set_data, dict) else set_data.working_weight

        return models.WorkoutSet(
            exercise_id=workout_exercise.id,
            intensity=intensity,
            effort=effort,
            volume=volume,
            working_weight=working_weight,
        )

    async def generate_workouts(self, request: WorkoutGenerationRequest) -> tuple[list[int], int, int]:
        workout_ids: list[int] = []

        logger.info(
            "[WORKOUT_SERVICE] Generating %s workouts for applied_plan_id=%s, user_id=%s",
            len(request.workouts),
            request.applied_plan_id,
            self.user_id,
        )

        # Allow generating additional workouts for an existing applied_plan_id (no early idempotent return)

        try:
            # Pre-fetch user-max ids per exercise to enable weight computation
            calculator = WorkoutCalculator()
            all_exercise_ids: set[int] = set()
            for w in request.workouts:
                for ex in w.exercises:
                    all_exercise_ids.add(int(ex.exercise_id))
            user_max_list = await calculator._fetch_user_maxes(list(all_exercise_ids))
            # Build maps: exercise_id -> user_max_id
            user_max_by_ex: dict[int, dict] = {}
            for um in user_max_list or []:
                try:
                    user_max_by_ex[int(um.get("exercise_id"))] = um
                except Exception:
                    continue
            for idx, workout_item in enumerate(request.workouts):
                # Create workout
                scheduled_for = workout_item.scheduled_for
                if isinstance(scheduled_for, str):
                    scheduled_for = datetime.fromisoformat(scheduled_for)

                logger.debug(
                    "[WORKOUT_SERVICE] Creating workout %s/%s: %s",
                    idx + 1,
                    len(request.workouts),
                    workout_item.name,
                )

                workout = models.Workout(
                    name=workout_item.name,
                    scheduled_for=scheduled_for,
                    plan_order_index=workout_item.plan_order_index,
                    applied_plan_id=request.applied_plan_id,
                    workout_type="generated",
                    user_id=self.user_id,
                )
                self.db.add(workout)
                await self.db.flush()
                logger.debug(f"[WORKOUT_SERVICE] Created workout id={workout.id}")

                # Create exercises and sets
                for ex_idx, exercise in enumerate(workout_item.exercises):
                    workout_exercise = models.WorkoutExercise(
                        workout_id=workout.id,
                        exercise_id=exercise.exercise_id,
                        user_id=self.user_id,
                    )
                    self.db.add(workout_exercise)
                    await self.db.flush()
                    logger.debug(
                        "[WORKOUT_SERVICE] Created workout_exercise id=%s for exercise_id=%s",
                        workout_exercise.id,
                        exercise.exercise_id,
                    )

                    for set_idx, set_data in enumerate(exercise.sets):
                        intensity = set_data.intensity
                        effort = set_data.effort
                        volume = set_data.volume
                        working_weight = set_data.working_weight

                        # Determine if we need to call RPE compute:
                        need_core_fill = sum(v is not None for v in (intensity, effort, volume)) >= 2 and (
                            intensity is None or effort is None or volume is None
                        )
                        need_weight = bool(getattr(request, "compute_weights", False)) and (working_weight is None)

                        if self.rpe_rpc and (need_core_fill or need_weight):
                            try:
                                um = user_max_by_ex.get(int(exercise.exercise_id))
                                user_max_id = int(um.get("id")) if um and um.get("id") is not None else None
                                compute_res = await self.rpe_rpc.compute(
                                    intensity=intensity,
                                    effort=effort,
                                    volume=volume,
                                    user_max_id=user_max_id,
                                    rounding_step=getattr(request, "rounding_step", 2.5),
                                    rounding_mode=getattr(request, "rounding_mode", "nearest"),
                                    headers=self.request_headers,
                                    user_id=self.user_id,
                                )
                                intensity = compute_res.get("intensity", intensity)
                                effort = compute_res.get("effort", effort)
                                volume = compute_res.get("volume", volume)
                                if need_weight:
                                    ww = compute_res.get("weight")
                                    if ww is not None:
                                        working_weight = ww
                            except Exception as e:
                                logger.warning(
                                    "[WORKOUT_SERVICE] RPE compute failed, proceeding with provided values: %s",
                                    e,
                                )

                        workout_set = models.WorkoutSet(
                            exercise_id=workout_exercise.id,
                            intensity=intensity,
                            effort=effort,
                            volume=volume,
                            working_weight=working_weight,
                        )
                        self.db.add(workout_set)
                        await self.db.flush()

                workout_ids.append(workout.id)

            logger.info(
                "[WORKOUT_SERVICE] Committing transaction with %s workouts",
                len(workout_ids),
            )
            await self.db.commit()
            logger.info(
                "[WORKOUT_SERVICE] Successfully committed workout_ids: %s",
                workout_ids,
            )

            try:
                GENERATED_WORKOUTS_CREATED_TOTAL.inc(len(workout_ids))
                WORKOUTS_CREATED_TOTAL.labels(source="generated").inc(len(workout_ids))
            except Exception:
                logger.exception("Failed to increment generated workout counters")

            return workout_ids, len(workout_ids), 0
        except IntegrityError as e:
            logger.error(
                "[WORKOUT_SERVICE] IntegrityError during workout generation (likely duplicate): %s",
                e,
            )
            await self.db.rollback()
            # If we hit a duplicate constraint, fetch existing workouts and return them
            if request.applied_plan_id:
                logger.info(
                    "[WORKOUT_SERVICE] Fetching existing workouts for applied_plan_id=%s",
                    request.applied_plan_id,
                )
                existing_result = await self.db.execute(
                    select(models.Workout)
                    .where(
                        models.Workout.user_id == self.user_id,
                        models.Workout.applied_plan_id == request.applied_plan_id,
                    )
                    .order_by(models.Workout.plan_order_index)
                )
                existing_workouts = existing_result.scalars().all()
                if existing_workouts:
                    existing_ids = [w.id for w in existing_workouts]
                    logger.info(
                        "[WORKOUT_SERVICE] Returning existing workout_ids: %s",
                        existing_ids,
                    )
                    return existing_ids, 0, len(existing_ids)
            raise
        except Exception as e:
            logger.error(f"[WORKOUT_SERVICE] Error during workout generation: {e}")
            await self.db.rollback()
            logger.error("[WORKOUT_SERVICE] Transaction rolled back")
            raise

    async def get_next_generated_workout(self) -> models.Workout:
        """
        Fetches the next generated workout (scheduled for the nearest future)
        """
        current_time = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(models.Workout)
            .options(selectinload(models.Workout.exercises).selectinload(models.WorkoutExercise.sets))
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.workout_type == "generated")
            .where(models.Workout.status != "completed")  # Only include not completed
            .where(models.Workout.scheduled_for > current_time)  # Only future workouts
            .order_by(models.Workout.scheduled_for.asc())  # Order by time
            .limit(1)
        )
        workout = result.scalars().first()
        if not workout:
            logger.info("No upcoming generated workouts found")
            raise HTTPException(status_code=404, detail="No upcoming generated workouts found")

        # Convert to dict to avoid DetachedInstanceError
        workout_dict = {
            "id": workout.id,
            "name": workout.name,
            "applied_plan_id": workout.applied_plan_id,
            "plan_order_index": workout.plan_order_index,
            "scheduled_for": workout.scheduled_for,
            "completed_at": workout.completed_at,
            "notes": workout.notes,
            "status": workout.status,
            "started_at": workout.started_at,
            "duration_seconds": workout.duration_seconds,
            "rpe_session": workout.rpe_session,
            "location": workout.location,
            "readiness_score": workout.readiness_score,
            "workout_type": workout.workout_type,
            "exercises": [],  # We don't need exercises for this response
        }
        return schemas.workout.WorkoutResponse.model_validate(workout_dict)

    async def get_next_workout_in_plan(self, current_workout_id: int) -> models.Workout:
        """
        Get the next workout in the same plan after the current workout
        """
        logger.info("Searching next workout for current_workout_id=%s", current_workout_id)

        # Get current workout to know its plan and order index
        current_result = await self.db.execute(
            select(models.Workout)
            .filter(models.Workout.id == current_workout_id)
            .filter(models.Workout.user_id == self.user_id)
        )
        current_workout = current_result.scalars().first()

        if not current_workout:
            logger.warning(f"Current workout {current_workout_id} not found")
            raise WorkoutNotFoundException(current_workout_id)

        logger.info(
            "Current workout: id=%s, applied_plan_id=%s, order_index=%s",
            current_workout.id,
            current_workout.applied_plan_id,
            current_workout.plan_order_index,
        )

        result = await self.db.execute(
            select(models.Workout)
            .options(selectinload(models.Workout.exercises).selectinload(models.WorkoutExercise.sets))
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.applied_plan_id == current_workout.applied_plan_id)
            .where(models.Workout.plan_order_index > current_workout.plan_order_index)
            .where(or_(models.Workout.status != "completed", models.Workout.status is None))
            .order_by(models.Workout.plan_order_index.asc())
            .limit(1)
        )
        next_workout = result.scalars().first()

        if not next_workout:
            logger.warning(
                "No next workout found for applied_plan_id=%s after order_index=%s",
                current_workout.applied_plan_id,
                current_workout.plan_order_index,
            )
            raise HTTPException(status_code=404, detail="No next workout found in this plan")

        logger.info(
            "Found next workout: id=%s, order_index=%s",
            next_workout.id,
            next_workout.plan_order_index,
        )

        # Convert to dict to avoid DetachedInstanceError
        workout_dict = {
            "id": next_workout.id,
            "name": next_workout.name,
            "applied_plan_id": next_workout.applied_plan_id,
            "plan_order_index": next_workout.plan_order_index,
            "scheduled_for": next_workout.scheduled_for,
            "completed_at": next_workout.completed_at,
            "notes": next_workout.notes,
            "status": next_workout.status,
            "started_at": next_workout.started_at,
            "duration_seconds": next_workout.duration_seconds,
            "rpe_session": next_workout.rpe_session,
            "location": next_workout.location,
            "readiness_score": next_workout.readiness_score,
            "workout_type": next_workout.workout_type,
            "exercises": [
                {
                    "id": ex.id,
                    "exercise_id": ex.exercise_id,
                    "sets": [
                        {
                            "id": s.id,
                            "intensity": s.intensity,
                            "effort": s.effort,
                            "volume": s.volume,
                            "working_weight": s.working_weight,
                        }
                        for s in ex.sets
                    ],
                }
                for ex in next_workout.exercises
            ],
        }
        return schemas.workout.WorkoutResponse.model_validate(workout_dict)

    async def get_first_generated_workout(self) -> models.Workout:
        """
        Fetches the first generated workout (with smallest id)
        """
        result = await self.db.execute(
            select(models.Workout)
            .options(selectinload(models.Workout.exercises).selectinload(models.WorkoutExercise.sets))
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.workout_type == "generated")
            .order_by(models.Workout.id.asc())
            .limit(1)
        )
        workout = result.scalars().first()
        if not workout:
            raise HTTPException(status_code=404, detail="No generated workouts found")

        # Convert to dict to avoid DetachedInstanceError
        workout_dict = {
            "id": workout.id,
            "name": workout.name,
            "applied_plan_id": workout.applied_plan_id,
            "plan_order_index": workout.plan_order_index,
            "scheduled_for": workout.scheduled_for,
            "completed_at": workout.completed_at,
            "notes": workout.notes,
            "status": workout.status,
            "started_at": workout.started_at,
            "duration_seconds": workout.duration_seconds,
            "rpe_session": workout.rpe_session,
            "location": workout.location,
            "readiness_score": workout.readiness_score,
            "workout_type": workout.workout_type,
            "exercises": [],  # We don't need exercises for this response
        }
        return schemas.workout.WorkoutResponse.model_validate(workout_dict)

    async def get_workouts_by_microcycle_ids(self, microcycle_ids: list[int]) -> list[models.Workout]:
        """
        Fetches workouts associated with the given microcycle IDs.
        """
        logger.debug("Fetching workouts for microcycle IDs: %s", microcycle_ids)
        if not microcycle_ids:
            return []

        stmt = (
            select(models.Workout)
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.microcycle_id.in_(microcycle_ids))
        )
        result = await self.db.execute(stmt)
        workouts = result.scalars().all()
        logger.debug("Found %s workouts for microcycle IDs %s", len(workouts), microcycle_ids)
        return workouts

    async def shift_schedule_in_plan(
        self,
        *,
        applied_plan_id: int,
        from_order_index: int,
        delta_days: int,
        delta_index: int,
        exclude_ids: list[int] | None = None,
        only_future: bool = True,
        baseline_date: datetime | None = None,
    ) -> dict:
        """Shift plan_order_index and scheduled_for for workouts in a plan.

        - Select workouts for this user and applied_plan_id with plan_order_index >= from_order_index
          and not in exclude_ids.
        - plan_order_index += delta_index for all selected.
        - scheduled_for += delta_days for rows where scheduled_for is not null and
          (not only_future or scheduled_for >= baseline_date).
        Returns a summary with affected_count and details.
        """
        try:
            exclude_ids = exclude_ids or []
            affected = 0
            logger.info(
                "[SHIFT_SCHEDULE] user_id=%s applied_plan_id=%s from_index=%s "
                "delta_days=%s delta_index=%s exclude=%s only_future=%s baseline=%s",
                self.user_id,
                applied_plan_id,
                from_order_index,
                delta_days,
                delta_index,
                len(exclude_ids),
                only_future,
                baseline_date,
            )
            # Select target rows with deterministic order
            stmt = (
                select(models.Workout)
                .where(models.Workout.user_id == self.user_id)
                .where(models.Workout.applied_plan_id == applied_plan_id)
                .where(models.Workout.plan_order_index >= from_order_index)
                .order_by(models.Workout.plan_order_index.asc())
            )
            if exclude_ids:
                stmt = stmt.where(~models.Workout.id.in_(exclude_ids))

            # Apply row-level locking to prevent concurrent shifts touching same rows
            result = await self.db.execute(stmt.with_for_update())
            items: list[models.Workout] = list(result.scalars().all())

            if not items:
                logger.info("[SHIFT_SCHEDULE] affected_count=0 (no rows matched)")
                return {"affected_count": 0, "shifted_ids": []}

            # Two-phase bump to avoid UNIQUE (user_id, applied_plan_id, plan_order_index) violation
            TEMP_OFFSET = 1_000_000
            # Phase 1: bump indices far away
            for w in items:
                if w.plan_order_index is None:
                    # should not happen due to filter, but guard anyway
                    w.plan_order_index = int(from_order_index) + TEMP_OFFSET
                else:
                    w.plan_order_index = int(w.plan_order_index) + TEMP_OFFSET
            await self.db.flush()

            # Phase 2: place to final positions and adjust dates
            for w in items:
                # final index
                w.plan_order_index = int(w.plan_order_index) - TEMP_OFFSET + int(delta_index)
                # shift date if allowed
                if w.scheduled_for is not None:
                    if (not only_future) or (baseline_date is None) or (w.scheduled_for >= baseline_date):
                        w.scheduled_for = w.scheduled_for + timedelta(days=int(delta_days))
                affected += 1

            # Collect ids before commit to avoid attribute access on expired instances
            shifted_ids = [int(w.id) for w in items]
            await self.db.commit()
            logger.info("[SHIFT_SCHEDULE] affected_count=%s", affected)
            return {"affected_count": affected, "shifted_ids": shifted_ids}
        except Exception as e:
            logger.error("[SHIFT_SCHEDULE] error: %s", e)
            await self.db.rollback()
            raise

    async def shift_applied_plan_schedule_from_date(
        self,
        applied_plan_id: int,
        cmd: schemas.AppliedPlanScheduleShiftCommand,
    ) -> dict:
        """Shift or restructure scheduled_for dates for workouts in an applied plan starting from a calendar date.

        This supports:
        - Shifting workouts by N days ("shift" mode)
        - Restructuring gaps between workouts ("set_rest" mode)
        - Inserting extra rest days via patterns (every N, at index, etc.)
        - Filtering by date range (from_date, to_date)
        - Filtering by status and future-only
        """

        raw_mode = getattr(cmd, "mode", None)
        mode = "preview" if raw_mode == "preview" else "apply"
        dry_run = mode == "preview"

        # Short-circuit only if it's a simple shift of 0 days (no-op) in apply mode
        # AND no other structural changes are requested.
        if (
            cmd.action_type == "shift"
            and cmd.days == 0
            and cmd.new_rest_days is None
            and cmd.add_rest_every_n_workouts is None
            and not cmd.add_rest_at_indices
            and not dry_run
        ):
            return {
                "workouts_shifted": 0,
                "days": 0,
                "action_type": cmd.action_type,
                "mode": mode,
            }

        from_dt = cmd.from_date
        if isinstance(from_dt, datetime):
            from_dt = self._convert_to_naive_utc(from_dt)
            from_day_start = datetime(from_dt.year, from_dt.month, from_dt.day)
        else:
            from_day_start = from_dt

        stmt = (
            select(models.Workout)
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.applied_plan_id == applied_plan_id)
            .where(models.Workout.scheduled_for != None)  # noqa: E711
            .where(models.Workout.scheduled_for >= from_day_start)
        )

        # Apply to_date filter if provided
        if cmd.to_date:
            to_dt = cmd.to_date
            if isinstance(to_dt, datetime):
                to_dt = self._convert_to_naive_utc(to_dt)
                # Include the entire 'to_date' day (exclusive of next day start)
                to_day_end = datetime(to_dt.year, to_dt.month, to_dt.day) + timedelta(days=1)
                stmt = stmt.where(models.Workout.scheduled_for < to_day_end)

        # Skip completed workouts based on completed_at, and optionally filter by status
        stmt = stmt.where(models.Workout.completed_at.is_(None))
        if cmd.status_in:
            stmt = stmt.where(models.Workout.status.in_(cmd.status_in))

        if cmd.only_future:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            stmt = stmt.where(models.Workout.scheduled_for >= now_utc)

        stmt = stmt.order_by(models.Workout.scheduled_for.asc())
        result = await self.db.execute(stmt)
        workouts: list[models.Workout] = list(result.scalars().all())

        if not workouts:
            logger.info(
                "applied_plan_schedule_shift_no_matches",
                user_id=self.user_id,
                applied_plan_id=applied_plan_id,
                from_date=from_day_start.isoformat(),
                days=cmd.days,
            )
            return {
                "workouts_shifted": 0,
                "days": cmd.days,
                "action_type": cmd.action_type,
                "mode": mode,
            }

        shifted_ids: list[int] = []
        shifted_count = 0

        # Capture original dates to calculate gaps correctly
        original_dates = [w.scheduled_for for w in workouts]

        # 1. Handle the first workout
        current_date = original_dates[0]
        if cmd.days != 0:
            current_date += timedelta(days=int(cmd.days))
            # Apply change if date is different
            if workouts[0].scheduled_for != current_date:
                if not dry_run:
                    workouts[0].scheduled_for = current_date
                    if workouts[0].id is not None:
                        shifted_ids.append(int(workouts[0].id))
                shifted_count += 1

        # 2. Iterate subsequent workouts
        for i in range(1, len(workouts)):
            w = workouts[i]

            # A. Determine Base Gap
            if cmd.new_rest_days is not None:
                # Fixed gap mode
                base_gap = cmd.new_rest_days + 1
            else:
                # Preserve original gap logic
                orig_prev = original_dates[i - 1]
                orig_curr = original_dates[i]
                if orig_prev and orig_curr:
                    base_gap = (orig_curr - orig_prev).days
                else:
                    base_gap = 1  # Fallback
                # Safety: gap should be at least 0 (same day) or 1
                if base_gap < 0:
                    base_gap = 0

            # B. Determine Extra Gap (Pattern-based insertion)
            extra_days = 0

            # Case 1: Every N workouts
            # i is 0-based index in this list.
            # "After every 4th workout" usually means after index 3, 7, etc.
            # If the user says "add rest after every 4 workouts", it means
            # between workout 4 and 5, there is extra rest.
            # In 0-indexed list: workout 4 is index 3.
            # So if (i) % N == 0?
            # Example: N=2. After 2nd workout (index 1).
            # We are currently at workout i (index 1). We are determining its date relative to i-1 (index 0).
            # The gap is BETWEEN i-1 and i.
            # If we want "rest after 1st workout", that's gap between index 0 and 1.
            # So if (i) % N == 0?
            # Let's trace: N=2. Add rest after 2nd workout.
            # i=0 (1st workout).
            # i=1 (2nd workout). Gap between 0 and 1. No extra rest yet.
            # i=2 (3rd workout). Gap between 1 and 2. This is "after 2nd workout".
            # So if (i) % N == 0 means:
            # i=2, N=2 -> match. Correct.
            # i=4, N=2 -> match. Correct (after 4th workout).
            if cmd.add_rest_every_n_workouts and (i % cmd.add_rest_every_n_workouts == 0):
                extra_days += cmd.add_rest_days_amount

            # Case 2: Specific indices
            # "After workout #4" means gap between #4 and #5.
            # In list, #4 is index 3. #5 is index 4.
            # We are calculating date for index 4.
            # So we check if (i-1) + 1 (1-based index of PREVIOUS workout) is in list?
            # Or if user provided 0-based indices?
            # Let's assume user thinks 1-based (workout #1, #2...).
            # If user says "after #4", they mean gap after the 4th workout processed.
            # i starts at 1.
            # Previous workout was i-1 (index wise), which is the (i-1)+1 = i-th workout in the sequence.
            # So if 'i' is in the list of "insert after X"?
            # Let's define 'add_rest_at_indices' as "1-based index of the workout AFTER WHICH we insert rest".
            # If i=4 (5th workout), we are calculating gap after 4th workout (i=3).
            # So if we want to insert rest after 4th workout, we insert it when calculating date for 5th workout.
            # So we check if (i) is in add_rest_at_indices?
            # Example: add after #1. List=[1].
            # i=1 (2nd workout). We want extra gap here.
            # if 1 in [1] -> True. Correct.
            if cmd.add_rest_at_indices and i in cmd.add_rest_at_indices:
                extra_days += cmd.add_rest_days_amount

            target_date = current_date + timedelta(days=base_gap + extra_days)

            # Apply
            if w.scheduled_for != target_date:
                if not dry_run:
                    w.scheduled_for = target_date
                    if w.id is not None:
                        shifted_ids.append(int(w.id))
                shifted_count += 1

            current_date = target_date

        if not dry_run:
            await self.db.commit()
            if shifted_ids:
                await invalidate_workout_cache(self.user_id, workout_ids=shifted_ids)

        logger.info(
            "applied_plan_schedule_shift_completed",
            user_id=self.user_id,
            applied_plan_id=applied_plan_id,
            from_date=from_day_start.isoformat(),
            days=cmd.days,
            workouts_shifted=shifted_count,
            action_type=cmd.action_type,
            mode=mode,
        )
        return {
            "workouts_shifted": shifted_count,
            "days": cmd.days,
            "action_type": cmd.action_type,
            "mode": mode,
        }

    async def apply_applied_plan_mass_edit(
        self,
        applied_plan_id: int,
        cmd: schemas.AppliedPlanMassEditCommand,
    ) -> schemas.AppliedPlanMassEditResult:
        """Apply mass edit actions to exercise instances/sets for an applied plan."""

        flt = cmd.filter
        actions = cmd.actions

        async def create_exercise_instance_for_workout(
            workout_id: int,
            spec: schemas.AppliedAddExerciseInstance,
        ) -> dict | None:
            """Create a new exercise instance in the given workout via exercises-service.

            This is used by high-level mass edit actions that add new exercises
            (actions.add_exercise_instances). It mirrors the public
            /exercises/instances/workouts/{workout_id}/instances endpoint and
            applies backend fallbacks when no sets are explicitly provided.
            """

            base_url = os.getenv("EXERCISES_SERVICE_URL")
            if not base_url:
                logger.warning("EXERCISES_SERVICE_URL is not set; cannot create exercise instance")
                return None
            base_url = base_url.rstrip("/")
            url = f"{base_url}/exercises/instances/workouts/{workout_id}/instances"
            headers = {"X-User-Id": self.user_id}

            sets_payload: list[dict] = []
            # 1) Direct mapping from spec.sets when present
            for s in spec.sets or []:
                payload_set: dict[str, Any] = {}

                # Reps are required by exercises-service SetService.normalize_sets.
                # Use volume as the primary source for reps; if missing, fall back to 1.
                reps_val: int | None = None
                if s.volume is not None:
                    try:
                        reps_val = int(s.volume)
                    except Exception:
                        reps_val = None
                if reps_val is None:
                    reps_val = 1
                payload_set["reps"] = reps_val
                payload_set["volume"] = reps_val

                if s.intensity is not None:
                    payload_set["intensity"] = s.intensity
                if s.weight is not None:
                    payload_set["weight"] = s.weight
                if s.effort is not None:
                    payload_set["effort"] = s.effort
                if payload_set:
                    sets_payload.append(payload_set)

            # 2) Backend fallback: if no sets were provided by the LLM, try to
            #    copy set patterns from the most recent existing instance of
            #    this exercise (within the same applied plan).
            if not sets_payload:
                try:
                    ex_def_id = int(spec.exercise_definition_id)
                except Exception:
                    ex_def_id = None
                if ex_def_id is not None:
                    history_list = history_instances_by_ex_def.get(ex_def_id) or []
                    # Walk from the latest seen instance backwards
                    for inst in reversed(history_list):
                        src_sets = inst.get("sets") or []
                        for s in src_sets:
                            if not isinstance(s, dict):
                                continue
                            payload_set: dict[str, Any] = {}
                            volume_src = s.get("volume")
                            if volume_src is None:
                                volume_src = s.get("reps")
                            if volume_src is not None:
                                try:
                                    v_int = int(volume_src)
                                    payload_set["volume"] = v_int
                                    payload_set["reps"] = v_int
                                except Exception:
                                    pass
                            intensity_src = s.get("intensity")
                            if intensity_src is not None:
                                payload_set["intensity"] = intensity_src
                            weight_src = s.get("weight")
                            if weight_src is None:
                                weight_src = s.get("working_weight")
                            if weight_src is not None:
                                payload_set["weight"] = weight_src
                            effort_src = s.get("effort")
                            if effort_src is None:
                                effort_src = s.get("rpe")
                            if effort_src is not None:
                                payload_set["effort"] = effort_src
                            if payload_set:
                                sets_payload.append(payload_set)
                        if sets_payload:
                            break

            # 3) Final safety: if still nothing, create one minimal visible set
            if not sets_payload:
                sets_payload.append({"volume": 1, "reps": 1})

            body: dict[str, Any] = {
                "exercise_list_id": spec.exercise_definition_id,
                "sets": sets_payload,
            }
            if spec.notes is not None:
                body["notes"] = spec.notes
            if spec.order is not None:
                body["order"] = spec.order

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    res = await client.post(url, headers=headers, json=body)
                    if res.status_code in (200, 201):
                        data = res.json()
                        if isinstance(data, dict):
                            return data
                    logger.warning(
                        "applied_mass_edit_create_instance_non_2xx",
                        status_code=res.status_code,
                        body=res.text,
                        workout_id=workout_id,
                    )
            except Exception:
                logger.exception(
                    "applied_mass_edit_create_instance_failed",
                    workout_id=workout_id,
                )
            return None

        async def fetch_instances_for_workout(workout_id: int) -> list[dict]:
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
                    logger.warning(
                        "applied_mass_edit_instances_non_200",
                        status_code=res.status_code,
                        body=res.text,
                        workout_id=workout_id,
                    )
            except Exception:
                logger.exception(
                    "applied_mass_edit_instances_failed",
                    workout_id=workout_id,
                )
            return []

        async def replace_exercise_instance(inst: dict, new_ex_def_id: int, new_ex_name: str | None = None) -> bool:
            instance_id = inst.get("id")
            if not isinstance(instance_id, int):
                return False
            base_url = os.getenv("EXERCISES_SERVICE_URL")
            if not base_url:
                logger.warning("EXERCISES_SERVICE_URL is not set; cannot replace exercise instance")
                return False
            base_url = base_url.rstrip("/")
            url = f"{base_url}/exercises/instances/{instance_id}"
            headers = {"X-User-Id": self.user_id}

            sets_payload: list[dict[str, Any]] = []
            for s in inst.get("sets") or []:
                if not isinstance(s, dict):
                    continue
                payload_set = dict(s)
                reps_val = payload_set.get("reps")
                if reps_val is None:
                    volume_val = payload_set.get("volume")
                    try:
                        reps_val = int(volume_val) if volume_val is not None else 1
                    except Exception:
                        reps_val = 1
                    payload_set["reps"] = reps_val
                payload_set["volume"] = payload_set.get("volume", reps_val)
                sets_payload.append(payload_set)
            if not sets_payload:
                sets_payload.append({"reps": 1, "volume": 1})

            body: dict[str, Any] = {
                "exercise_list_id": new_ex_def_id,
                "sets": sets_payload,
            }
            if inst.get("notes") is not None:
                body["notes"] = inst.get("notes")
            if inst.get("order") is not None:
                body["order"] = inst.get("order")
            if new_ex_name:
                body["exercise_name"] = new_ex_name

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    res = await client.put(url, headers=headers, json=body)
                    if res.status_code in (200, 201):
                        inst["exercise_list_id"] = new_ex_def_id
                        return True
                    logger.warning(
                        "applied_mass_edit_replace_instance_non_2xx",
                        status_code=res.status_code,
                        body=res.text,
                        instance_id=instance_id,
                    )
            except Exception:
                logger.exception(
                    "applied_mass_edit_replace_instance_failed",
                    instance_id=instance_id,
                )
            return False

        async def update_set(instance_id: int, set_id: int, payload: dict) -> bool:
            if not payload:
                return False
            base_url = os.getenv("EXERCISES_SERVICE_URL")
            if not base_url:
                logger.warning("EXERCISES_SERVICE_URL is not set; cannot update set")
                return False
            base_url = base_url.rstrip("/")
            url = f"{base_url}/exercises/instances/{instance_id}/sets/{set_id}"
            headers = {"X-User-Id": self.user_id}
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    res = await client.put(url, headers=headers, json=payload)
                    if res.status_code in (200, 201):
                        return True
                    logger.warning(
                        "applied_mass_edit_update_set_non_2xx",
                        status_code=res.status_code,
                        body=res.text,
                        instance_id=instance_id,
                        set_id=set_id,
                    )
            except Exception:
                logger.exception(
                    "applied_mass_edit_update_set_failed",
                    instance_id=instance_id,
                    set_id=set_id,
                )
            return False

        def _as_float(value: Any) -> float | None:
            try:
                if value is None:
                    return None
                return float(value)
            except (TypeError, ValueError):
                return None

        def _as_int(value: Any) -> int | None:
            try:
                if value is None:
                    return None
                return int(value)
            except (TypeError, ValueError):
                return None

        def set_matches_filters(s: dict) -> bool:
            intensity_val = _as_float(s.get("intensity"))
            volume_val = _as_int(s.get("volume") if s.get("volume") is not None else s.get("reps"))
            weight_val = _as_float(s.get("weight"))
            effort_src = s.get("effort")
            if effort_src is None:
                effort_src = s.get("rpe")
            effort_val = _as_float(effort_src)

            if flt.intensity_gte is not None and (intensity_val is None or intensity_val < flt.intensity_gte):
                return False
            if flt.intensity_lte is not None and (intensity_val is None or intensity_val > flt.intensity_lte):
                return False
            if flt.volume_gte is not None and (volume_val is None or volume_val < flt.volume_gte):
                return False
            if flt.volume_lte is not None and (volume_val is None or volume_val > flt.volume_lte):
                return False
            if flt.weight_gte is not None and (weight_val is None or weight_val < flt.weight_gte):
                return False
            if flt.weight_lte is not None and (weight_val is None or weight_val > flt.weight_lte):
                return False
            if flt.effort_gte is not None and (effort_val is None or effort_val < flt.effort_gte):
                return False
            if flt.effort_lte is not None and (effort_val is None or effort_val > flt.effort_lte):
                return False
            return True

        def build_set_update_payload(s: dict) -> dict:
            payload: dict[str, Any] = {}

            intensity_val = _as_float(s.get("intensity"))
            if (
                actions.set_intensity is not None
                or actions.increase_intensity_by is not None
                or actions.decrease_intensity_by is not None
            ):
                new_intensity = intensity_val or 0.0
                if actions.set_intensity is not None:
                    new_intensity = actions.set_intensity
                if actions.increase_intensity_by is not None:
                    new_intensity += actions.increase_intensity_by
                if actions.decrease_intensity_by is not None:
                    new_intensity -= actions.decrease_intensity_by
                if intensity_val is None or abs(new_intensity - intensity_val) > 1e-9:
                    payload["intensity"] = new_intensity

            volume_val = _as_int(s.get("volume") if s.get("volume") is not None else s.get("reps"))
            if (
                actions.set_volume is not None
                or actions.increase_volume_by is not None
                or actions.decrease_volume_by is not None
            ):
                new_volume = volume_val or 0
                if actions.set_volume is not None:
                    new_volume = actions.set_volume
                if actions.increase_volume_by is not None:
                    new_volume += actions.increase_volume_by
                if actions.decrease_volume_by is not None:
                    new_volume -= actions.decrease_volume_by
                if actions.clamp_non_negative:
                    new_volume = max(1, int(new_volume))
                if volume_val is None or int(new_volume) != int(volume_val):
                    payload["volume"] = int(new_volume)
                    payload["reps"] = int(new_volume)

            weight_val = _as_float(s.get("weight"))
            if (
                actions.set_weight is not None
                or actions.increase_weight_by is not None
                or actions.decrease_weight_by is not None
            ):
                new_weight = weight_val or 0.0
                if actions.set_weight is not None:
                    new_weight = actions.set_weight
                if actions.increase_weight_by is not None:
                    new_weight += actions.increase_weight_by
                if actions.decrease_weight_by is not None:
                    new_weight -= actions.decrease_weight_by
                if actions.clamp_non_negative:
                    new_weight = max(0.0, new_weight)
                if weight_val is None or abs(new_weight - (weight_val or 0.0)) > 1e-9:
                    payload["weight"] = new_weight

            effort_src = s.get("effort")
            if effort_src is None:
                effort_src = s.get("rpe")
            effort_val = _as_float(effort_src)
            if (
                actions.set_effort is not None
                or actions.increase_effort_by is not None
                or actions.decrease_effort_by is not None
            ):
                new_effort = effort_val or 0.0
                if actions.set_effort is not None:
                    new_effort = actions.set_effort
                if actions.increase_effort_by is not None:
                    new_effort += actions.increase_effort_by
                if actions.decrease_effort_by is not None:
                    new_effort -= actions.decrease_effort_by
                # Clamp to [4,10] as per ExerciseSetUpdate constraints when effort is used
                new_effort = max(4.0, min(10.0, new_effort))
                if effort_val is None or abs(new_effort - (effort_val or 0.0)) > 1e-9:
                    payload["effort"] = new_effort
                    payload["rpe"] = new_effort

            return payload

        # Accumulate history of instances by exercise_definition_id as we scan workouts
        history_instances_by_ex_def: dict[int, list[dict]] = {}

        # Select workouts in this applied plan for current user
        stmt = (
            select(models.Workout)
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.applied_plan_id == applied_plan_id)
        )
        if flt.plan_order_indices:
            stmt = stmt.where(models.Workout.plan_order_index.in_(flt.plan_order_indices))
        if flt.from_order_index is not None:
            stmt = stmt.where(models.Workout.plan_order_index >= flt.from_order_index)
        if flt.to_order_index is not None:
            stmt = stmt.where(models.Workout.plan_order_index <= flt.to_order_index)
        if flt.status_in:
            stmt = stmt.where(models.Workout.status.in_(flt.status_in))
        if flt.scheduled_from is not None:
            stmt = stmt.where(models.Workout.scheduled_for >= flt.scheduled_from)
        if flt.scheduled_to is not None:
            stmt = stmt.where(models.Workout.scheduled_for <= flt.scheduled_to)
        if flt.only_future:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            stmt = stmt.where(
                (models.Workout.scheduled_for == None) | (models.Workout.scheduled_for >= now_utc)  # noqa: E711
            )
        stmt = stmt.order_by(models.Workout.plan_order_index.asc())

        result = await self.db.execute(stmt)
        workouts: list[models.Workout] = list(result.scalars().all())
        if not workouts:
            return schemas.AppliedPlanMassEditResult(
                mode=cmd.mode,
                workouts_matched=0,
                instances_matched=0,
                sets_matched=0,
                sets_modified=0,
                details=[],
            )

        workouts_matched = 0
        instances_matched = 0
        sets_matched = 0
        sets_modified = 0
        details: list[dict] = []

        for w in workouts:
            instances = await fetch_instances_for_workout(int(w.id))

            # Update history for backend fallbacks (e.g., copying sets from previous workouts)
            for inst in instances:
                if not isinstance(inst, dict):
                    continue
                hist_ex_def_id = inst.get("exercise_list_id")
                if isinstance(hist_ex_def_id, int):
                    history_instances_by_ex_def.setdefault(hist_ex_def_id, []).append(inst)

            workout_instances_matched = 0
            workout_sets_matched = 0
            workout_sets_modified = 0

            for inst in instances:
                if not isinstance(inst, dict):
                    continue
                ex_def_id = inst.get("exercise_list_id")
                if flt.exercise_definition_ids and ex_def_id not in flt.exercise_definition_ids:
                    continue
                instance_id = inst.get("id")
                if not isinstance(instance_id, int):
                    continue
                sets = inst.get("sets") or []

                instance_sets_matched = 0
                instance_sets_modified = 0

                for s in sets:
                    if not isinstance(s, dict):
                        continue
                    if not set_matches_filters(s):
                        continue
                    instance_sets_matched += 1
                    if cmd.mode == "apply":
                        set_id = s.get("id")
                        if not isinstance(set_id, int) or set_id <= 0:
                            continue
                        payload = build_set_update_payload(s)
                        if not payload:
                            continue
                        if await update_set(instance_id, set_id, payload):
                            instance_sets_modified += 1

                if instance_sets_matched:
                    workout_instances_matched += 1
                    workout_sets_matched += instance_sets_matched
                    workout_sets_modified += instance_sets_modified

                # Exercise-level replacement (after evaluating set filters)
                if actions.replace_exercise_definition_id_to is not None:
                    target_ids = flt.exercise_definition_ids or []
                    ex_def_id = inst.get("exercise_list_id")
                    matches_exercise_filter = not target_ids or ex_def_id in target_ids
                    has_set_filters = any(
                        value is not None
                        for value in (
                            flt.intensity_lte,
                            flt.intensity_gte,
                            flt.volume_lte,
                            flt.volume_gte,
                            flt.weight_lte,
                            flt.weight_gte,
                            flt.effort_lte,
                            flt.effort_gte,
                        )
                    )
                    should_replace = matches_exercise_filter and (not has_set_filters or instance_sets_matched > 0)
                    if should_replace:
                        replacement_sets = len(sets) if sets else 1
                        replaced = False
                        if cmd.mode == "apply":
                            replaced = await replace_exercise_instance(
                                inst,
                                actions.replace_exercise_definition_id_to,
                                actions.replace_exercise_name_to,
                            )
                        else:
                            replaced = True
                        if replaced:
                            workout_instances_matched += 1
                            workout_sets_matched += replacement_sets
                            if cmd.mode == "apply":
                                workout_sets_modified += replacement_sets

            # Handle high-level actions that add new exercise instances to this workout
            added_sets_for_workout = 0
            added_instances_for_workout = 0
            if actions.add_exercise_instances:
                for spec in actions.add_exercise_instances:
                    if cmd.mode == "apply":
                        created = await create_exercise_instance_for_workout(int(w.id), spec)
                        if created:
                            created_sets = created.get("sets") or []
                            added_sets_for_workout += len(created_sets)
                            added_instances_for_workout += 1
                    else:
                        # Preview mode: approximate the number of affected sets without mutating state
                        if spec.sets:
                            added_sets_for_workout += len(spec.sets)
                        else:
                            # If no sets specified, assume at least one set will be created
                            added_sets_for_workout += 1
                        added_instances_for_workout += 1

            if added_sets_for_workout:
                workout_sets_matched += added_sets_for_workout
                if cmd.mode == "apply":
                    workout_sets_modified += added_sets_for_workout
                workout_instances_matched += added_instances_for_workout

            if workout_sets_matched:
                workouts_matched += 1
                instances_matched += workout_instances_matched
                sets_matched += workout_sets_matched
                sets_modified += workout_sets_modified
                details.append(
                    {
                        "workout_id": int(w.id),
                        "plan_order_index": int(w.plan_order_index) if w.plan_order_index is not None else None,
                        "instances_matched": workout_instances_matched,
                        "sets_matched": workout_sets_matched,
                        "sets_modified": workout_sets_modified,
                    }
                )

        return schemas.AppliedPlanMassEditResult(
            mode=cmd.mode,
            workouts_matched=workouts_matched,
            instances_matched=instances_matched,
            sets_matched=sets_matched,
            sets_modified=sets_modified,
            details=details,
        )

    async def get_plan_details_with_exercises(
        self,
        applied_plan_id: int,
    ) -> List[schemas.workout.WorkoutPlanDetailItem]:
        """
        Fetch all workouts for an applied plan, including their exercise definition IDs.
        This is optimized for analysis/reporting to avoid N+1 queries.
        """
        query = (
            select(models.Workout)
            .options(selectinload(models.Workout.exercises))
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.applied_plan_id == applied_plan_id)
            .order_by(models.Workout.plan_order_index.asc())
        )
        result = await self.db.execute(query)
        workouts = result.scalars().all()

        items = []
        for w in workouts:
            exercise_ids = [ex.exercise_id for ex in w.exercises]
            items.append(
                schemas.workout.WorkoutPlanDetailItem(
                    id=w.id,
                    name=w.name,
                    scheduled_for=w.scheduled_for,
                    status=w.status,
                    plan_order_index=w.plan_order_index,
                    exercise_ids=exercise_ids,
                )
            )
        return items
