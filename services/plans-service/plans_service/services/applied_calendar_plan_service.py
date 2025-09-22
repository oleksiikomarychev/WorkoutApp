from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date, timezone, tzinfo
from zoneinfo import ZoneInfo, available_timezones
from typing import Optional, List, Dict, Any
import math
import os
import logging
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import urllib.parse
from ..schemas.mesocycle import MicrocycleResponse, MesocycleResponse
from ..models.calendar import (AppliedCalendarPlan, CalendarPlan, Mesocycle, Microcycle, AppliedMesocycle, AppliedMicrocycle, AppliedWorkout, PlanWorkout, PlanExercise)
from ..schemas.calendar_plan import (AppliedCalendarPlanResponse,CalendarPlanResponse,ApplyPlanComputeSettings,UserMaxResponse, RoundingMode)
from .calendar_plan_service import CalendarPlanService
from ..rpc_client import workout_rpc
from .. import workout_calculation
from ..rpc import get_intensity, get_volume, get_effort
from sqlalchemy import select
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


class AppliedCalendarPlanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _fetch_user_maxes(self, exercise_ids: List[int]) -> List[Dict]:
        if not exercise_ids:
            return []
        base = "http://user-max-service:8003/user-max"
        headers = {"Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            async def fetch_one(ex_id):
                try:
                    url = f"{base}/by_exercise/{ex_id}"
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    else:
                        logger.error(f"Unexpected response for exercise_id {ex_id}: {data}")
                        return []
                except Exception as e:
                    logger.error(f"Failed to fetch user max for exercise_id {ex_id}: {e}")
                    return []

            tasks = [fetch_one(ex_id) for ex_id in exercise_ids]
            results = await asyncio.gather(*tasks)
            # Flatten the list of lists
            user_maxes = [max for sublist in results for max in sublist]
            return user_maxes

    async def _fetch_user_maxes_by_ids(self, user_max_ids: List[int]) -> List[Dict]:
        if not user_max_ids:
            return []
        headers = {"Content-Type": "application/json"}
        base = "http://user-max-service:8003"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{base}/user-max/by-ids"
                params = {"ids": user_max_ids}  # Pass as list to get multiple query parameters
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    return data
            except Exception as e:
                logger.error(f"Failed to fetch user maxes by IDs from {base}: {e}")
        return []

    async def _ensure_exercises_present(self, exercise_ids: set[int]) -> None:
        """Ensure exercises exist by checking via the exercises-service API."""
        if not exercise_ids:
            return
        
        base = "http://exercises-service:8002"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for ex_id in exercise_ids:
                found = False
                try:
                    url = f"{base}/exercises/definitions/{ex_id}"
                    headers = {"Content-Type": "application/json"}
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        found = True
                        break
                except Exception:
                    continue
                if not found:
                    logger.warning(f"Exercise definition id={ex_id} not found via remote services")
                    continue
        return

    async def _generate_workouts_via_rpc(self, applied_plan_id: int, workouts: List[Dict[str, Any]], compute: ApplyPlanComputeSettings) -> Optional[List[int]]:
        bases = [
            os.getenv("WORKOUTS_SERVICE_URL", "http://localhost:8004")
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for base in bases:
                # Try only the path without /api/v1
                paths = ["workouts/workout-generation/generate"]
                for path in paths:
                    url = urllib.parse.urljoin(base, path)
                    try:
                        response = await client.post(
                            url,
                            json={
                                "applied_plan_id": applied_plan_id,
                                "compute_weights": compute.compute_weights,
                                "rounding_step": compute.rounding_step,
                                "rounding_mode": compute.rounding_mode,
                                "workouts": workouts
                            }
                        )
                        response.raise_for_status()
                        return response.json().get("workout_ids")
                    except Exception as e:
                        if hasattr(e, 'response') and e.response.status_code == 422:
                            logger.error(f"Workout generation validation error: {e.response.text}")
                        else:
                            logger.warning(f"Workout generation RPC failed with URL {url}: {str(e)}")
        
        logger.error("All workout generation RPC attempts failed")
        return None

    async def apply_plan(self, plan_id: int, compute: ApplyPlanComputeSettings, user_max_ids: List[int]) -> AppliedCalendarPlanResponse:
        logger.info(f"Applying plan {plan_id} for user {user_max_ids}")
        try:
            # Async-compatible query for base plan with eager loading
            stmt = select(CalendarPlan).options(
                selectinload(CalendarPlan.mesocycles).selectinload(Mesocycle.microcycles)
            ).where(CalendarPlan.id == plan_id)
            result = await self.db.execute(stmt)
            base_plan = result.scalars().first()
            if not base_plan:
                raise ValueError(f"План с ID {plan_id} не найден")
            
            # Query mesocycles
            stmt = select(Mesocycle).where(Mesocycle.calendar_plan_id == plan_id).order_by(Mesocycle.order_index.asc(), Mesocycle.id.asc())
            result = await self.db.execute(stmt)
            mesocycles = result.scalars().all()
            
            if not mesocycles:
                raise ValueError("План должен содержать хотя бы один мезоцикл")
                
            # Query microcycles with full eager loading
            stmt = select(Microcycle).options(
                selectinload(Microcycle.plan_workouts).selectinload(PlanWorkout.exercises).selectinload(PlanExercise.sets)
            ).where(Microcycle.mesocycle_id.in_([m.id for m in mesocycles])).order_by(Microcycle.order_index.asc(), Microcycle.id.asc())
            result = await self.db.execute(stmt)
            microcycles = result.scalars().all()
            
            logger.debug(f"Loaded {len(microcycles)} microcycles")
            for mc in microcycles:
                logger.debug(f"Microcycle {mc.id} has {len(mc.plan_workouts)} plan_workouts")
            
            # Collect required exercises
            required_exercises = set()
            for mc in microcycles:
                for workout in mc.plan_workouts:
                    for exercise in workout.exercises:
                        required_exercises.add(exercise.exercise_definition_id)
            
            # Fetch user maxes and ensure exercises exist
            user_maxes = await self._fetch_user_maxes(list(required_exercises))
            max_exercises = set(um["exercise_id"] for um in user_maxes)
            missing_exercises = required_exercises - max_exercises
            if missing_exercises:
                logger.info(f"Missing user maxes for exercises: {missing_exercises}. Trying to fetch via user-max-service...")
                fetched = await self._fetch_user_maxes(list(missing_exercises))
                if fetched:
                    user_maxes.extend(fetched)
                    max_exercises = set(um["exercise_id"] for um in user_maxes)
                    missing_exercises = required_exercises - max_exercises
            if missing_exercises:
                logger.info(f"Missing user maxes for exercises: {missing_exercises}. Skipping...")
            await self._ensure_exercises_present(required_exercises)
            
            # Deactivate any currently active plan
            stmt = update(AppliedCalendarPlan).where(AppliedCalendarPlan.is_active.is_(True)).values(is_active=False)
            await self.db.execute(stmt)
            
            # Create new applied plan
            start_date = compute.start_date or datetime.now(timezone.utc)
            applied_plan = AppliedCalendarPlan(
                calendar_plan_id=plan_id,
                start_date=start_date,
            )
            total_days = 0
            for mc in microcycles:
                if mc.days_count is not None:
                    total_days += mc.days_count
                else:
                    total_days += len(mc.plan_workouts)  # Use number of workouts as fallback
            applied_plan.end_date = applied_plan.start_date + timedelta(days=total_days)
            # Convert to naive UTC datetimes for database compatibility
            applied_plan.start_date = applied_plan.start_date.replace(tzinfo=None)
            applied_plan.end_date = applied_plan.end_date.replace(tzinfo=None)
            self.db.add(applied_plan)
            await self.db.commit()
            await self.db.refresh(applied_plan)
            
            calculated_schedule = {}
            def round_to_step(value: float) -> float:
                step = compute.rounding_step
                mode = compute.rounding_mode
                if step <= 0:
                    return value
                ratio = value / step
                if mode == RoundingMode.floor:
                    return math.floor(ratio) * step
                elif mode == RoundingMode.ceil:
                    return math.ceil(ratio) * step
                else:  # nearest
                    return round(ratio) * step
            plan_order = 0
            meso_id_to_micro = {}
            for mc in microcycles:
                meso_id_to_micro.setdefault(mc.mesocycle_id, []).append(mc)
            effective_1rms: dict[int, float] = {}
            for um in user_maxes:
                base_true = await workout_calculation.WorkoutCalculator.get_true_1rm_from_user_max(um)
                effective_1rms[um["exercise_id"]] = float(base_true if base_true is not None else um["max_weight"])

            workouts_to_generate = []
            for mi, meso in enumerate(mesocycles, start=1):
                for mci, mc in enumerate(meso_id_to_micro.get(meso.id, []), start=1):
                    # Build schedule_dict from ORM relationships
                    schedule_dict = defaultdict(list)
                    for workout in mc.plan_workouts:
                        workout_data = {"exercises": []}
                        for exercise in workout.exercises:
                            sets_data = []
                            for s in exercise.sets:
                                set_dict = {
                                    "intensity": s.intensity,
                                    "effort": s.effort,
                                    "volume": s.volume
                                }
                                sets_data.append(set_dict)
                            exercise_data = {
                                "exercise_id": exercise.exercise_definition_id,
                                "sets": sets_data
                            }
                            workout_data["exercises"].append(exercise_data)
                        schedule_dict[workout.day_label].append(workout_data)
                    
                    if not schedule_dict:
                        logger.warning(f"Microcycle {mc.id} has no workouts - skipping.")
                        continue
                    
                    for di, (day_key, workouts) in enumerate(schedule_dict.items(), start=1):
                        label = f"M{mi}-MC{mci}-D{di}: {day_key}"
                        logger.debug(f"Processing day: {label} with {len(workouts)} workouts")

                        calculated_schedule[label] = []
                        for workout_index, workout in enumerate(workouts, start=1):
                            workout_exercises = []  # Reset for each workout in the day

                            for exercise in workout.get("exercises", []):
                                user_max = next((um for um in user_maxes if um["exercise_id"] == exercise["exercise_id"]), None)
                                if not user_max:
                                    logger.debug(f"No user max found for exercise {exercise['exercise_id']}")
                                    continue

                                calculated_sets = []
                                for set_data in exercise["sets"]:
                                    intensity = set_data.get("intensity")
                                    effort = set_data.get("effort")
                                    volume = set_data.get("volume")
                                    if intensity is not None and effort is not None:
                                        volume = await get_volume(intensity=intensity, effort=effort)
                                    elif volume is not None and effort is not None:
                                        intensity = await get_intensity(volume=volume, effort=effort)
                                    elif volume is not None and intensity is not None:
                                        effort = await get_effort(volume=volume, intensity=intensity)
                                    weight = None
                                    if compute.compute_weights and intensity is not None:
                                        eff = effective_1rms.get(user_max["exercise_id"])
                                        if eff is None:
                                            true_1rm = await workout_calculation.WorkoutCalculator.get_true_1rm_from_user_max(user_max)
                                            eff = float(true_1rm) if true_1rm is not None else float(user_max["max_weight"])
                                            effective_1rms[user_max["exercise_id"]] = eff
                                        raw = eff * (intensity / 100.0)
                                        weight = round_to_step(raw)

                                    calculated_sets.append({"intensity": intensity, "effort": effort, "volume": volume, "working_weight": weight, "weight": weight})

                                calculated_exercise = {"exercise_id": exercise["exercise_id"],"sets": calculated_sets}
                                calculated_schedule[label].append(calculated_exercise)
                                
                                workout_exercises.append({
                                    "exercise_id": exercise["exercise_id"],
                                    "sets": [{
                                        "exercise_id": exercise["exercise_id"],
                                        "intensity": s["intensity"],
                                        "effort": s["effort"],
                                        "volume": s["volume"],
                                        "working_weight": s["working_weight"]
                                    } for s in calculated_sets]
                                })

                            # Create a workout for this workout in the day
                            workout_name = f"{label} - Workout {workout_index}"
                            logger.debug(f"Creating workout: {workout_name} with {len(workout_exercises)} exercises")
                            for ex_index, exercise in enumerate(workout_exercises, start=1):
                                logger.debug(f"  Exercise {ex_index}: exercise_id={exercise.get('exercise_id')}, sets={len(exercise.get('sets', []))}")
                                for set_index, set_data in enumerate(exercise.get('sets', []), start=1):
                                    logger.debug(f"    Set {set_index}: intensity={set_data.get('intensity')}, effort={set_data.get('effort')}, volume={set_data.get('volume')}, working_weight={set_data.get('working_weight')}")
                            
                            workouts_to_generate.append({
                                "name": workout_name,
                                "scheduled_for": (applied_plan.start_date + timedelta(days=plan_order)).isoformat(),
                                "plan_order_index": plan_order,
                                "exercises": workout_exercises
                            })
                            plan_order += 1
                    
                    self._apply_normalization(
                        effective_1rms, mc.normalization_value, mc.normalization_unit
                    )
            if compute.generate_workouts:
                logger.info(f"Generating workouts for applied plan {applied_plan.id} with {len(workouts_to_generate)} workouts")
                workout_ids = await self._generate_workouts_via_rpc(applied_plan.id, workouts_to_generate, compute)
                logger.info(f"Generated workout IDs: {workout_ids}")
                if workout_ids:
                    from ..models.calendar import AppliedPlanWorkout
                    for i, workout_id in enumerate(workout_ids):
                        applied_workout = AppliedPlanWorkout(
                            applied_plan_id=applied_plan.id,
                            workout_id=workout_id,
                            order_index=i
                        )
                        self.db.add(applied_workout)
                    await self.db.commit()
                    logger.info(f"Saved {len(workout_ids)} workouts to applied_plan_workouts table")
            else:
                logger.info("Skipping workout saving because compute.generate_workouts is false")
            calendar_plan_response = CalendarPlanService._get_plan_response(base_plan)
            
            user_maxes = await self._fetch_user_maxes_by_ids(user_max_ids) if user_max_ids else []
            
            applied_plan.user_max_ids = [um["id"] for um in user_maxes]
            self.db.add(applied_plan)
            await self.db.commit()
            
            await self.db.refresh(applied_plan)
            
            applied_plan_response = AppliedCalendarPlanResponse(
                id=applied_plan.id,
                calendar_plan_id=applied_plan.calendar_plan_id,
                start_date=applied_plan.start_date,
                end_date=applied_plan.end_date,
                is_active=applied_plan.is_active,
                calendar_plan=calendar_plan_response,  
                user_maxes=[UserMaxResponse(id=um["id"],exercise_id=um["exercise_id"],max_weight=um["max_weight"],rep_max=um["rep_max"]) for um in user_maxes],
                next_workout=None,
            )

            logger.info(f"Successfully applied plan {plan_id}")
            return applied_plan_response
        except Exception as e:
            logger.error(f"Error applying plan {plan_id}: {str(e)}", exc_info=True)
            raise

    async def get_applied_plan_by_id(self, plan_id: int) -> Optional[AppliedCalendarPlan]:
        try:
            stmt = select(AppliedCalendarPlan).where(AppliedCalendarPlan.id == plan_id)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching applied plan: {str(e)}")
            return None

    async def get_user_applied_plans(self) -> List[AppliedCalendarPlanResponse]:
        try:
            stmt = select(AppliedCalendarPlan).order_by(AppliedCalendarPlan.start_date.desc())
            result = await self.db.execute(stmt)
            plans = result.scalars().all()

            response = []
            for p in plans:
                calendar_plan_response = CalendarPlanResponse(
                    id=p.calendar_plan.id,
                    name=p.calendar_plan.name,
                    duration_weeks=p.calendar_plan.duration_weeks,
                    is_active=p.calendar_plan.is_active,
                    mesocycles=[
                        MesocycleResponse(
                            id=m.id,
                            name=m.name,
                            order_index=m.order_index,
                            weeks_count=m.weeks_count,
                            microcycle_length_days=m.microcycle_length_days,
                            microcycles=[
                                MicrocycleResponse(
                                    id=mc.id,
                                    name=mc.name,
                                    order_index=mc.order_index,
                                    normalization_value=mc.normalization_value,
                                    normalization_unit=mc.normalization_unit,
                                    days_count=mc.days_count
                                ) for mc in m.microcycles
                            ]
                        ) for m in p.calendar_plan.mesocycles
                    ]
                )
                
                response.append(AppliedCalendarPlanResponse(
                    id=p.id,
                    calendar_plan_id=p.calendar_plan_id,
                    start_date=p.start_date,
                    end_date=p.end_date,
                    is_active=p.is_active,
                    calendar_plan=calendar_plan_response,
                    next_workout=None
                ))
            
            return response
        except Exception as e:
            logger.error(f"Error fetching user plans: {str(e)}")
            return []

    async def get_active_plan(self) -> Optional[AppliedCalendarPlan]:
        """Get the currently active plan with applied hierarchy"""
        stmt = select(AppliedCalendarPlan).where(AppliedCalendarPlan.is_active.is_(True))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    def _apply_normalization(self, effective_1rms: dict[int, float], value: Optional[float], unit: Optional[str]):
        """Apply normalization to the effective 1RMs."""
        if value is None or unit is None:
            return
        if unit == "percentage":
            # Apply a percentage increase or decrease
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm * (1 + value / 100.0)
        elif unit == "absolute":
            # Apply an absolute increase or decrease
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm + value
