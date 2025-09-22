from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload, selectinload
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
from .rpc_client import PlansServiceRPC
import json

logger = logging.getLogger(__name__)

class WorkoutService:
    def __init__(self, db: AsyncSession, plans_rpc: PlansServiceRPC, exercises_rpc: Any = None):
        self.db = db
        self.plans_rpc = plans_rpc
        self.exercises_rpc = exercises_rpc

    def _convert_to_naive_utc(self, dt: datetime) -> datetime:
        """Convert aware datetime to naive UTC datetime"""
        if dt.tzinfo is not None:
            dt = dt.astimezone(pytz.utc)
            return dt.replace(tzinfo=None)
        return dt

    async def create_workout(self, payload: WorkoutCreate, user_id: int, plan_workout_id: int = None) -> WorkoutResponse:
        # Convert timezone-aware datetimes to naive UTC
        item_data = payload.model_dump()
        for field in ['scheduled_for', 'completed_at', 'started_at']:
            if field in item_data and item_data[field] is not None:
                item_data[field] = self._convert_to_naive_utc(item_data[field])
                
        item = models.Workout(**item_data, plan_workout_id=plan_workout_id, user_id=user_id)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return WorkoutResponse.model_validate(item)

    async def get_workout(self, workout_id: int) -> schemas.workout.WorkoutResponse:
        result = await self.db.execute(
            select(models.Workout)
            .options(
                joinedload(models.Workout.exercises).joinedload(models.WorkoutExercise.sets)
            )
            .filter(models.Workout.id == workout_id)
        )
        workout = result.unique().scalars().first()
        if not workout:
            raise WorkoutNotFoundException(workout_id)
            
        return schemas.workout.WorkoutResponse.model_validate(workout)

    async def list_workouts(
        self,
        skip: int = 0,
        limit: int = 100,
        type: Optional[str] = None,
        applied_plan_id: Optional[int] = None
    ) -> list[WorkoutListResponse]:
        query = select(models.Workout)
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
        item = await self.get_workout(workout_id)
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(item, k, v)
            
        await self.db.commit()
        await self.db.refresh(item)
        
        # Convert to response model after update
        return WorkoutResponse.model_validate(item)

    async def delete_workout(self, workout_id: int) -> None:
        # Fetch the ORM model directly for deletion
        result = await self.db.execute(select(models.Workout).filter(models.Workout.id == workout_id))
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

    async def generate_workouts(self, request: WorkoutGenerationRequest) -> List[int]:
        workout_ids = []
        
        for workout_item in request.workouts:
            # Create workout
            scheduled_for = workout_item.scheduled_for
            if isinstance(scheduled_for, str):
                scheduled_for = datetime.fromisoformat(scheduled_for)
                
            workout = models.Workout(
                name=workout_item.name,
                scheduled_for=scheduled_for,
                plan_order_index=workout_item.plan_order_index,
                applied_plan_id=request.applied_plan_id,
                workout_type='generated'
            )
            self.db.add(workout)
            await self.db.flush()
            
            # Create exercises and sets
            for exercise in workout_item.exercises:
                workout_exercise = models.WorkoutExercise(
                    workout_id=workout.id,
                    exercise_id=exercise.exercise_id
                )
                self.db.add(workout_exercise)
                await self.db.flush()
                
                for set_data in exercise.sets:
                    workout_set = models.WorkoutSet(
                        exercise_id=workout_exercise.id,
                        intensity=set_data.intensity,
                        effort=set_data.effort,
                        volume=set_data.volume,
                        working_weight=set_data.working_weight
                    )
                    self.db.add(workout_set)
                    await self.db.flush()
            
            workout_ids.append(workout.id)
            
        await self.db.commit()
        return workout_ids

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

        stmt = select(models.Workout).where(models.Workout.microcycle_id.in_(microcycle_ids))
        result = await self.db.execute(stmt)
        workouts = result.scalars().all()
        logger.debug(f"Found {len(workouts)} workouts for microcycle IDs {microcycle_ids}")
        return workouts
