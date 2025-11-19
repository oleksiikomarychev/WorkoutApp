from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from ..models import Workout, WorkoutExercise, WorkoutSet, workout_type_enum
from ..schemas.workout import WorkoutCreate, WorkoutUpdate, WorkoutResponse, WorkoutListResponse
from .. import schemas
from ..exceptions import WorkoutNotFoundException
from typing import List, Optional, Any
from .. import models
from ..schemas.workout_generation import WorkoutGenerationRequest, WorkoutGenerationItem
from fastapi import HTTPException
import os
import httpx
from ..workout_calculation import WorkoutCalculator
import math
from datetime import datetime, timedelta
import logging
import pytz
from datetime import datetime, timedelta, timezone
from .rpc_client import PlansServiceRPC, RpeServiceRPC
import json

logger = logging.getLogger(__name__)

class WorkoutService:
    def __init__(self, db: AsyncSession, plans_rpc: PlansServiceRPC, exercises_rpc: Any = None, user_id: str = None, rpe_rpc: RpeServiceRPC | None = None, request_headers: dict[str, str] | None = None):
        self.db = db
        self.plans_rpc = plans_rpc
        self.exercises_rpc = exercises_rpc
        self.user_id = user_id
        self.rpe_rpc = rpe_rpc
        self.request_headers = request_headers or {}

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
        for field in ['scheduled_for', 'completed_at', 'started_at']:
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
        result = await self.db.execute(
            select(models.Workout)
            .options(
                selectinload(models.Workout.exercises)
                .selectinload(models.WorkoutExercise.sets)
            )
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

        return schemas.workout.WorkoutResponse.model_validate(workout_dict)

    async def list_workouts(
        self,
        skip: int = 0,
        limit: int = 100,
        type: Optional[str] = None,
        applied_plan_id: Optional[int] = None
    ) -> list[WorkoutListResponse]:
        query = select(models.Workout).where(models.Workout.user_id == self.user_id)
        if type:
            if type not in ['manual', 'generated']:
                raise HTTPException(status_code=400, detail=f"Invalid workout type: {type}")
            query = query.where(models.Workout.workout_type == type)
        if applied_plan_id is not None:
            query = query.where(models.Workout.applied_plan_id == applied_plan_id)
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
                "workout_type": workout.workout_type
            }
            workout_dicts.append(workout_dict)
        
        return [WorkoutListResponse.model_validate(w) for w in workout_dicts]

    async def update_workout(self, workout_id: int, payload: WorkoutUpdate) -> WorkoutResponse:
        # Fetch the ORM model directly (not the Pydantic response)
        result = await self.db.execute(
            select(models.Workout)
            .options(
                selectinload(models.Workout.exercises)
                .selectinload(models.WorkoutExercise.sets)
            )
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
        
        # Re-fetch with exercises after commit to ensure relationships are loaded
        result = await self.db.execute(
            select(models.Workout)
            .options(
                selectinload(models.Workout.exercises)
                .selectinload(models.WorkoutExercise.sets)
            )
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
            for field in ['scheduled_for', 'completed_at', 'started_at']:
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
                "workout_type": workout.workout_type
            }
            created_workouts.append(workout_dict)
            
        await self.db.commit()
        return created_workouts

    async def _create_workout(self, workout_item: WorkoutGenerationItem, request: WorkoutGenerationRequest, microcycle_id: int = None) -> models.Workout:
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
            workout_type='generated'
        )

    async def _create_workout_exercise(self, workout: models.Workout, exercise: dict) -> models.WorkoutExercise:
        """Create workout exercise from exercise data"""
        exercise_id = exercise.get('exercise_id') if isinstance(exercise, dict) else exercise.exercise_id
        return models.WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercise_id
        )

    async def _create_workout_set(self, workout_exercise: models.WorkoutExercise, set_data: dict) -> models.WorkoutSet:
        """Create workout set from set data"""
        intensity = set_data.get('intensity') if isinstance(set_data, dict) else set_data.intensity
        effort = set_data.get('effort') if isinstance(set_data, dict) else set_data.effort
        volume = set_data.get('volume') if isinstance(set_data, dict) else set_data.volume
        working_weight = set_data.get('working_weight') if isinstance(set_data, dict) else set_data.working_weight
        
        return models.WorkoutSet(
            exercise_id=workout_exercise.id,
            intensity=intensity,
            effort=effort,
            volume=volume,
            working_weight=working_weight
        )

    async def generate_workouts(self, request: WorkoutGenerationRequest) -> tuple[list[int], int, int]:
        workout_ids: list[int] = []
        
        logger.info(f"[WORKOUT_SERVICE] Generating {len(request.workouts)} workouts for applied_plan_id={request.applied_plan_id}, user_id={self.user_id}")
        
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
                
                logger.debug(f"[WORKOUT_SERVICE] Creating workout {idx+1}/{len(request.workouts)}: {workout_item.name}")
                    
                workout = models.Workout(
                    name=workout_item.name,
                    scheduled_for=scheduled_for,
                    plan_order_index=workout_item.plan_order_index,
                    applied_plan_id=request.applied_plan_id,
                    workout_type='generated',
                    user_id=self.user_id
                )
                self.db.add(workout)
                await self.db.flush()
                logger.debug(f"[WORKOUT_SERVICE] Created workout id={workout.id}")
                
                # Create exercises and sets
                for ex_idx, exercise in enumerate(workout_item.exercises):
                    workout_exercise = models.WorkoutExercise(
                        workout_id=workout.id,
                        exercise_id=exercise.exercise_id,
                        user_id=self.user_id
                    )
                    self.db.add(workout_exercise)
                    await self.db.flush()
                    logger.debug(f"[WORKOUT_SERVICE] Created workout_exercise id={workout_exercise.id} for exercise_id={exercise.exercise_id}")
                    
                    for set_idx, set_data in enumerate(exercise.sets):
                        intensity = set_data.intensity
                        effort = set_data.effort
                        volume = set_data.volume
                        working_weight = set_data.working_weight

                        # Determine if we need to call RPE compute:
                        need_core_fill = sum(v is not None for v in (intensity, effort, volume)) >= 2 and (
                            intensity is None or effort is None or volume is None
                        )
                        need_weight = bool(getattr(request, 'compute_weights', False)) and (working_weight is None)

                        if self.rpe_rpc and (need_core_fill or need_weight):
                            try:
                                um = user_max_by_ex.get(int(exercise.exercise_id))
                                user_max_id = int(um.get("id")) if um and um.get("id") is not None else None
                                compute_res = await self.rpe_rpc.compute(
                                    intensity=intensity,
                                    effort=effort,
                                    volume=volume,
                                    user_max_id=user_max_id,
                                    rounding_step=getattr(request, 'rounding_step', 2.5),
                                    rounding_mode=getattr(request, 'rounding_mode', 'nearest'),
                                    headers=self.request_headers,
                                    user_id=self.user_id,
                                )
                                intensity = compute_res.get('intensity', intensity)
                                effort = compute_res.get('effort', effort)
                                volume = compute_res.get('volume', volume)
                                if need_weight:
                                    ww = compute_res.get('weight')
                                    if ww is not None:
                                        working_weight = ww
                            except Exception as e:
                                logger.warning(f"[WORKOUT_SERVICE] RPE compute failed, proceeding with provided values: {e}")

                        workout_set = models.WorkoutSet(
                            exercise_id=workout_exercise.id,
                            intensity=intensity,
                            effort=effort,
                            volume=volume,
                            working_weight=working_weight
                        )
                        self.db.add(workout_set)
                        await self.db.flush()
                
                workout_ids.append(workout.id)
            
            logger.info(f"[WORKOUT_SERVICE] Committing transaction with {len(workout_ids)} workouts")
            await self.db.commit()
            logger.info(f"[WORKOUT_SERVICE] Successfully committed workout_ids: {workout_ids}")
            return workout_ids, len(workout_ids), 0
        except IntegrityError as e:
            logger.error(f"[WORKOUT_SERVICE] IntegrityError during workout generation (likely duplicate): {e}")
            await self.db.rollback()
            # If we hit a duplicate constraint, fetch existing workouts and return them
            if request.applied_plan_id:
                logger.info(f"[WORKOUT_SERVICE] Fetching existing workouts for applied_plan_id={request.applied_plan_id}")
                existing_result = await self.db.execute(
                    select(models.Workout)
                    .where(
                        models.Workout.user_id == self.user_id,
                        models.Workout.applied_plan_id == request.applied_plan_id
                    )
                    .order_by(models.Workout.plan_order_index)
                )
                existing_workouts = existing_result.scalars().all()
                if existing_workouts:
                    existing_ids = [w.id for w in existing_workouts]
                    logger.info(f"[WORKOUT_SERVICE] Returning existing workout_ids: {existing_ids}")
                    return existing_ids, 0, len(existing_ids)
            raise
        except Exception as e:
            logger.error(f"[WORKOUT_SERVICE] Error during workout generation: {e}")
            await self.db.rollback()
            logger.error(f"[WORKOUT_SERVICE] Transaction rolled back")
            raise

    async def get_next_generated_workout(self) -> models.Workout:
        """
        Fetches the next generated workout (scheduled for the nearest future)
        """
        current_time = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(models.Workout)
            .options(
                selectinload(models.Workout.exercises)
                .selectinload(models.WorkoutExercise.sets)
            )
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.workout_type == 'generated')
            .where(models.Workout.status != 'completed')  # Only include not completed
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
            "exercises": []  # We don't need exercises for this response
        }
        return schemas.workout.WorkoutResponse.model_validate(workout_dict)

    async def get_next_workout_in_plan(self, current_workout_id: int) -> models.Workout:
        """
        Get the next workout in the same plan after the current workout
        """
        logger.info(f"Searching next workout for current_workout_id={current_workout_id}")
        
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
        
        logger.info(f"Current workout: id={current_workout.id}, applied_plan_id={current_workout.applied_plan_id}, order_index={current_workout.plan_order_index}")
        
        result = await self.db.execute(
            select(models.Workout)
            .options(
                selectinload(models.Workout.exercises)
                .selectinload(models.WorkoutExercise.sets)
            )
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.applied_plan_id == current_workout.applied_plan_id)
            .where(models.Workout.plan_order_index > current_workout.plan_order_index)
            .where(or_(models.Workout.status != 'completed', models.Workout.status == None))
            .order_by(models.Workout.plan_order_index.asc())
            .limit(1)
        )
        next_workout = result.scalars().first()
        
        if not next_workout:
            logger.warning(f"No next workout found for applied_plan_id={current_workout.applied_plan_id} after order_index={current_workout.plan_order_index}")
            raise HTTPException(status_code=404, detail="No next workout found in this plan")
        
        logger.info(f"Found next workout: id={next_workout.id}, order_index={next_workout.plan_order_index}")
        
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
                            "working_weight": s.working_weight
                        } for s in ex.sets
                    ]
                } for ex in next_workout.exercises
            ]
        }
        return schemas.workout.WorkoutResponse.model_validate(workout_dict)

    async def get_first_generated_workout(self) -> models.Workout:
        """
        Fetches the first generated workout (with smallest id)
        """
        result = await self.db.execute(
            select(models.Workout)
            .options(
                selectinload(models.Workout.exercises)
                .selectinload(models.WorkoutExercise.sets)
            )
            .where(models.Workout.user_id == self.user_id)
            .where(models.Workout.workout_type == 'generated')
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
            "exercises": []  # We don't need exercises for this response
        }
        return schemas.workout.WorkoutResponse.model_validate(workout_dict)

    async def get_workouts_by_microcycle_ids(self, microcycle_ids: list[int]) -> list[models.Workout]:
        """
        Fetches workouts associated with the given microcycle IDs.
        """
        logger.debug(f"Fetching workouts for microcycle IDs: {microcycle_ids}")
        if not microcycle_ids:
            return []

        stmt = select(models.Workout).where(
            models.Workout.user_id == self.user_id
        ).where(models.Workout.microcycle_id.in_(microcycle_ids))
        result = await self.db.execute(stmt)
        workouts = result.scalars().all()
        logger.debug(f"Found {len(workouts)} workouts for microcycle IDs {microcycle_ids}")
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
                f"[SHIFT_SCHEDULE] user_id={self.user_id} applied_plan_id={applied_plan_id} from_index={from_order_index} "
                f"delta_days={delta_days} delta_index={delta_index} exclude={len(exclude_ids)} only_future={only_future} baseline={baseline_date}"
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
            logger.info(f"[SHIFT_SCHEDULE] affected_count={affected}")
            return {"affected_count": affected, "shifted_ids": shifted_ids}
        except Exception as e:
            logger.error(f"[SHIFT_SCHEDULE] error: {e}")
            await self.db.rollback()
            raise
