from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date, timezone, tzinfo
from zoneinfo import ZoneInfo, available_timezones
from typing import Optional, List, Dict, Any
import re
import math
import os
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import urllib.parse
from ..schemas.mesocycle import MicrocycleResponse, MesocycleResponse
from ..schemas.calendar_plan import ApplyPlanComputeSettings, AppliedCalendarPlanResponse, CalendarPlanResponse, UserMaxResponse, RoundingMode
from ..models.calendar import (AppliedCalendarPlan, CalendarPlan, Mesocycle, Microcycle, AppliedMesocycle, AppliedMicrocycle, AppliedWorkout, PlanWorkout, PlanExercise)
from .calendar_plan_service import CalendarPlanService
from ..rpc_client import workout_rpc
from .. import workout_calculation
from ..rpc import get_intensity, get_volume, get_effort
from collections import defaultdict
from sqlalchemy import select


class AppliedCalendarPlanService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    def _require_user_id(self) -> str:
        if not self.user_id:
            raise ValueError("User context required")
        return self.user_id

    def _auth_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        user_id = self.user_id
        if user_id:
            headers["X-User-Id"] = user_id
        return headers

    async def _fetch_user_maxes(self, exercise_ids: List[int]) -> List[Dict]:
        if not exercise_ids:
            return []
        base = "http://user-max-service:8003/user-max"
        headers = self._auth_headers()

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
                        return []
                except Exception:
                    return []

            tasks = [fetch_one(ex_id) for ex_id in exercise_ids]
            results = await asyncio.gather(*tasks)
            # Flatten the list of lists
            user_maxes = [max for sublist in results for max in sublist]
            return user_maxes

    async def _fetch_user_maxes_by_ids(self, user_max_ids: List[int]) -> List[Dict]:
        if not user_max_ids:
            return []
        headers = self._auth_headers()
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
            except Exception:
                pass
        return []

    async def _ensure_exercises_present(self, exercise_ids: set[int]) -> None:
        """Ensure exercises exist by checking via the exercises-service API."""
        if not exercise_ids:
            return

        base = "http://exercises-service:8002"
        headers = self._auth_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for ex_id in exercise_ids:
                found = False
                try:
                    url = f"{base}/exercises/definitions/{ex_id}"
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        found = True
                        break
                except Exception:
                    continue
                if not found:
                    continue
        return

    async def _generate_workouts_via_rpc(self, applied_plan_id: int, workouts: List[Dict[str, Any]], compute: ApplyPlanComputeSettings) -> Optional[List[int]]:
        import logging
        logger = logging.getLogger(__name__)
        
        bases = [
            os.getenv("WORKOUTS_SERVICE_URL", "http://localhost:8004")
        ]
        headers = self._auth_headers()
        
        logger.info(f"[APPLY_PLAN] Generating {len(workouts)} workouts via RPC for applied_plan_id={applied_plan_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for base in bases:
                # Try only the path without /api/v1
                paths = ["workouts/workout-generation/generate"]
                for path in paths:
                    url = urllib.parse.urljoin(base, path)
                    try:
                        logger.info(f"[APPLY_PLAN] Posting to {url}")
                        response = await client.post(
                            url,
                            json={
                                "applied_plan_id": applied_plan_id,
                                "compute_weights": compute.compute_weights,
                                "rounding_step": compute.rounding_step,
                                "rounding_mode": compute.rounding_mode,
                                "workouts": workouts
                            },
                            headers=headers,
                        )
                        response.raise_for_status()
                        workout_ids = response.json().get("workout_ids")
                        logger.info(f"[APPLY_PLAN] Successfully generated workout_ids: {workout_ids}")
                        return workout_ids
                    except httpx.HTTPStatusError as e:
                        logger.error(f"[APPLY_PLAN] HTTP error from {url}: status={e.response.status_code}, body={e.response.text}")
                    except Exception as e:
                        logger.error(f"[APPLY_PLAN] Failed to generate workouts via {url}: {e}")
        
        logger.warning("[APPLY_PLAN] All workout generation attempts failed")
        return None

    async def _create_instances_for_workouts(
        self,
        workout_ids: List[int],
        workouts_to_generate: List[Dict[str, Any]],
    ) -> None:
        """Create exercise instances in exercises-service for generated workouts.

        We use the exact computed payload used to generate workouts to materialize
        instances immediately, so clients always fetch real exercise_instances.
        """
        if not workout_ids or not workouts_to_generate:
            return
        base = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")
        # Ensure base has no trailing slash issues in joins
        headers = self._auth_headers()
        async with httpx.AsyncClient(timeout=20.0) as client:
            for idx, workout_id in enumerate(workout_ids):
                if idx >= len(workouts_to_generate):
                    break
                src = workouts_to_generate[idx]
                exercises = src.get("exercises") or []
                for ex in exercises:
                    sets_payload = []
                    for s in ex.get("sets") or []:
                        sets_payload.append(
                            {
                                # exercises-service requires 'reps' in SetService.normalize_sets
                                "reps": s.get("volume"),
                                "weight": s.get("working_weight"),
                                # keep extra for traceability/UI
                                "rpe": s.get("effort"),
                                "effort": s.get("effort"),
                                "effort_type": "RPE",
                                "intensity": s.get("intensity"),
                                "volume": s.get("volume"),
                            }
                        )
                    instance_payload = {
                        "exercise_list_id": ex.get("exercise_id"),
                        "sets": sets_payload,
                        "notes": None,
                        "order": None,
                        "user_max_id": None,
                    }
                    url = f"{base}/exercises/instances/workouts/{workout_id}/instances"
                    try:
                        res = await client.post(url, json=instance_payload, headers=headers)
                        # Do not raise on error to avoid aborting entire plan; just continue
                        if res.status_code not in (200, 201):
                            print(
                                f"[APPLY_PLAN] Failed to create instance for workout {workout_id}: "
                                f"status={res.status_code} body={res.text}"
                            )
                    except Exception as e:
                        print(f"[APPLY_PLAN] Exception creating instance for workout {workout_id}: {e}")

    async def apply_plan(self, plan_id: int, compute: ApplyPlanComputeSettings, user_max_ids: List[int]) -> AppliedCalendarPlanResponse:
        try:
            user_id = self._require_user_id()
            headers = self._auth_headers()

            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets)
                )
                .where(CalendarPlan.id == plan_id)
            )
            result = await self.db.execute(stmt)
            base_plan = result.scalars().first()
            if not base_plan:
                raise ValueError(f"План с ID {plan_id} не найден")

            stmt = (
                select(Mesocycle)
                .join(Mesocycle.calendar_plan)
                .where(Mesocycle.calendar_plan_id == plan_id)
                .order_by(Mesocycle.order_index.asc(), Mesocycle.id.asc())
            )
            result = await self.db.execute(stmt)
            mesocycles = result.scalars().all()
            if not mesocycles:
                raise ValueError("План должен содержать хотя бы один мезоцикл")

            stmt = (
                select(Microcycle)
                .options(
                    selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets)
                )
                .join(Microcycle.mesocycle)
                .join(Mesocycle.calendar_plan)
                .where(Microcycle.mesocycle_id.in_([m.id for m in mesocycles]))
                .order_by(Microcycle.order_index.asc(), Microcycle.id.asc())
            )
            result = await self.db.execute(stmt)
            microcycles = result.scalars().all()

            required_exercises: set[int] = set()
            for mc in microcycles:
                for workout in mc.plan_workouts:
                    for exercise in workout.exercises:
                        required_exercises.add(exercise.exercise_definition_id)

            selected_user_maxes = await self._fetch_user_maxes_by_ids(user_max_ids) if user_max_ids else []

            def _pick_preferred(existing: dict | None, candidate: dict | None) -> dict | None:
                if candidate is None:
                    return existing
                if existing is None:
                    return candidate
                try:
                    existing_weight = float(existing.get("max_weight") or 0)
                except (TypeError, ValueError):
                    existing_weight = 0.0
                try:
                    candidate_weight = float(candidate.get("max_weight") or 0)
                except (TypeError, ValueError):
                    candidate_weight = 0.0
                return candidate if candidate_weight >= existing_weight else existing

            user_max_by_exercise: dict[int, dict] = {}
            for um in selected_user_maxes:
                ex_id = um.get("exercise_id")
                if isinstance(ex_id, int):
                    user_max_by_exercise[ex_id] = _pick_preferred(user_max_by_exercise.get(ex_id), um)

            missing_exercises = required_exercises - set(user_max_by_exercise.keys())
            if missing_exercises:
                fetched = await self._fetch_user_maxes(list(missing_exercises))
                for um in fetched or []:
                    ex_id = um.get("exercise_id")
                    if isinstance(ex_id, int):
                        user_max_by_exercise[ex_id] = _pick_preferred(user_max_by_exercise.get(ex_id), um)

            user_maxes = list(user_max_by_exercise.values())
            await self._ensure_exercises_present(required_exercises)

            stmt = (
                update(AppliedCalendarPlan)
                .where(
                    AppliedCalendarPlan.is_active.is_(True),
                    AppliedCalendarPlan.user_id == user_id,
                )
                .values(is_active=False)
            )
            await self.db.execute(stmt)

            start_date = compute.start_date or datetime.now(timezone.utc)
            applied_plan = AppliedCalendarPlan(
                calendar_plan_id=plan_id,
                start_date=start_date,
                user_id=user_id,
            )
            total_days = 0
            for mc in microcycles:
                if mc.days_count is not None:
                    total_days += mc.days_count
                else:
                    total_days += len(mc.plan_workouts)
            applied_plan.end_date = applied_plan.start_date + timedelta(days=total_days)
            applied_plan.start_date = applied_plan.start_date.replace(tzinfo=None)
            applied_plan.end_date = applied_plan.end_date.replace(tzinfo=None)
            self.db.add(applied_plan)
            await self.db.flush()

            calculated_schedule: dict[str, list[dict[str, Any]]] = {}

            def round_to_step(value: float) -> float:
                step = compute.rounding_step
                mode = compute.rounding_mode
                if step <= 0:
                    return value
                ratio = value / step
                if mode == RoundingMode.floor:
                    return math.floor(ratio) * step
                if mode == RoundingMode.ceil:
                    return math.ceil(ratio) * step
                return round(ratio) * step

            plan_order = 0
            meso_id_to_micro: dict[int, list[Microcycle]] = {}
            for mc in microcycles:
                meso_id_to_micro.setdefault(mc.mesocycle_id, []).append(mc)

            effective_1rms: dict[int, float] = {}
            for um in user_maxes:
                base_true = await workout_calculation.WorkoutCalculator.get_true_1rm_from_user_max(um, headers=headers)
                effective_1rms[um["exercise_id"]] = float(base_true if base_true is not None else um["max_weight"])

            workouts_to_generate: list[dict[str, Any]] = []
            for mi, meso in enumerate(mesocycles, start=1):
                for mci, mc in enumerate(meso_id_to_micro.get(meso.id, []), start=1):
                    schedule_dict: dict[str, list[dict[str, Any]]] = defaultdict(list)
                    for workout in sorted(mc.plan_workouts, key=lambda w: (w.order_index, w.id)):
                        workout_data = {"exercises": []}
                        for exercise in workout.exercises:
                            sets_data = []
                            for s in exercise.sets:
                                sets_data.append(
                                    {
                                        "intensity": s.intensity,
                                        "effort": s.effort,
                                        "volume": s.volume,
                                    }
                                )
                            workout_data["exercises"].append(
                                {
                                    "exercise_id": exercise.exercise_definition_id,
                                    "sets": sets_data,
                                }
                            )
                        schedule_dict[workout.day_label].append(workout_data)

                    if not schedule_dict:
                        continue

                    micro_len = mc.days_count or 0
                    if micro_len <= 0:
                        micro_len = max(len(schedule_dict) if schedule_dict else 0, len(mc.plan_workouts))
                        if micro_len == 0:
                            micro_len = 7

                    for di, (day_key, workouts) in enumerate(schedule_dict.items(), start=1):
                        label = f"M{mi}-MC{mci}-D{di}: {day_key}"
                        calculated_schedule[label] = []

                        for workout_index, workout_payload in enumerate(workouts, start=1):
                            workout_exercises: list[dict[str, Any]] = []

                            for exercise in workout_payload.get("exercises", []):
                                user_max = user_max_by_exercise.get(exercise["exercise_id"])
                                calculated_sets = []
                                for set_data in exercise["sets"]:
                                    intensity = set_data.get("intensity")
                                    effort = set_data.get("effort")
                                    volume = set_data.get("volume")
                                    try:
                                        if intensity is not None and effort is not None:
                                            volume = await get_volume(intensity=intensity, effort=effort, headers=headers)
                                        elif volume is not None and effort is not None:
                                            intensity = await get_intensity(volume=volume, effort=effort, headers=headers)
                                        elif volume is not None and intensity is not None:
                                            effort = await get_effort(volume=volume, intensity=intensity, headers=headers)
                                    except Exception:
                                        pass

                                    weight = None
                                    if compute.compute_weights and intensity is not None and user_max is not None:
                                        eff = effective_1rms.get(user_max["exercise_id"])
                                        if eff is None:
                                            true_1rm = await workout_calculation.WorkoutCalculator.get_true_1rm_from_user_max(user_max, headers=headers)
                                            eff = float(true_1rm) if true_1rm is not None else float(user_max["max_weight"])
                                            effective_1rms[user_max["exercise_id"]] = eff
                                        raw = eff * (intensity / 100.0)
                                        weight = round_to_step(raw)

                                    calculated_sets.append(
                                        {
                                            "intensity": intensity,
                                            "effort": effort,
                                            "volume": volume,
                                            "working_weight": weight,
                                            "weight": weight,
                                        }
                                    )

                                calculated_schedule[label].append(
                                    {
                                        "exercise_id": exercise["exercise_id"],
                                        "sets": calculated_sets,
                                    }
                                )

                                workout_exercises.append(
                                    {
                                        "exercise_id": exercise["exercise_id"],
                                        "sets": [
                                            {
                                                "exercise_id": exercise["exercise_id"],
                                                "intensity": s["intensity"],
                                                "effort": s["effort"],
                                                "volume": s["volume"],
                                                "working_weight": s["working_weight"],
                                            }
                                            for s in calculated_sets
                                        ],
                                    }
                                )

                            workout_name = f"{label} - Workout {workout_index}"
                            workouts_to_generate.append(
                                {
                                    "name": workout_name,
                                    "scheduled_for": (applied_plan.start_date + timedelta(days=plan_order)).isoformat(),
                                    "plan_order_index": plan_order,
                                    "exercises": workout_exercises,
                                }
                            )
                            plan_order += 1

                    self._apply_normalization(
                        effective_1rms,
                        mc.normalization_value,
                        mc.normalization_unit,
                    )

            if compute.generate_workouts:
                workout_ids = await self._generate_workouts_via_rpc(applied_plan.id, workouts_to_generate, compute)
                if workout_ids:
                    from ..models.calendar import AppliedPlanWorkout

                    for i, workout_id in enumerate(workout_ids):
                        applied_workout = AppliedPlanWorkout(
                            applied_plan_id=applied_plan.id,
                            workout_id=workout_id,
                            order_index=i,
                        )
                        self.db.add(applied_workout)
                    await self.db.flush()
                    try:
                        await self._create_instances_for_workouts(workout_ids, workouts_to_generate)
                    except Exception as e:
                        print(f"[APPLY_PLAN] Non-fatal: failed to create some instances: {e}")

            calendar_plan_response = CalendarPlanService._get_plan_response(base_plan)

            selected_user_maxes_by_id = {um.get("id"): um for um in selected_user_maxes if um.get("id") is not None}
            ordered_user_maxes = [selected_user_maxes_by_id.get(uid) for uid in user_max_ids] if user_max_ids else []
            ordered_user_maxes = [um for um in ordered_user_maxes if um]

            applied_plan.user_max_ids = [um["id"] for um in ordered_user_maxes]
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
                user_maxes=[
                    UserMaxResponse(
                        id=um["id"],
                        exercise_id=um["exercise_id"],
                        max_weight=um["max_weight"],
                        rep_max=um["rep_max"],
                    )
                    for um in ordered_user_maxes
                ],
                next_workout=None,
            )

            return applied_plan_response
        except Exception:
            raise

    async def get_applied_plan_by_id(self, plan_id: int) -> Optional[AppliedCalendarPlan]:
        try:
            user_id = self._require_user_id()
            stmt = (
                select(AppliedCalendarPlan)
                .options(
                    selectinload(AppliedCalendarPlan.calendar_plan)
                        .selectinload(CalendarPlan.mesocycles)
                        .selectinload(Mesocycle.microcycles)
                        .selectinload(Microcycle.plan_workouts)
                        .selectinload(PlanWorkout.exercises)
                        .selectinload(PlanExercise.sets),
                    selectinload(AppliedCalendarPlan.workouts)
                )
                .where(
                    AppliedCalendarPlan.id == plan_id,
                    AppliedCalendarPlan.user_id == user_id,
                )
            )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception:
            return None

    async def get_user_applied_plans(self) -> List[AppliedCalendarPlanResponse]:
        try:
            user_id = self._require_user_id()
            stmt = (
                select(AppliedCalendarPlan)
                .options(
                    selectinload(AppliedCalendarPlan.calendar_plan)
                        .selectinload(CalendarPlan.mesocycles)
                        .selectinload(Mesocycle.microcycles)
                        .selectinload(Microcycle.plan_workouts)
                        .selectinload(PlanWorkout.exercises)
                        .selectinload(PlanExercise.sets),
                    selectinload(AppliedCalendarPlan.workouts)
                )
                .where(AppliedCalendarPlan.user_id == user_id)
                .order_by(AppliedCalendarPlan.start_date.desc())
            )
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
        except Exception:
            return []

    async def get_active_plan(self) -> Optional[AppliedCalendarPlan]:
        """Get the currently active plan with applied hierarchy"""
        user_id = self._require_user_id()
        stmt = (
            select(AppliedCalendarPlan)
            .options(
                selectinload(AppliedCalendarPlan.calendar_plan)
                    .selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets),
                selectinload(AppliedCalendarPlan.workouts)
            )
            .where(
                AppliedCalendarPlan.is_active.is_(True),
                AppliedCalendarPlan.user_id == user_id,
            )
        )
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
