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
from .template_service import TemplateService


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
                        body = response.json()
                        workout_ids = body.get("workout_ids") if isinstance(body, dict) else None
                        if isinstance(workout_ids, list) and len(workout_ids) != len(workouts):
                            logger.warning(
                                "[APPLY_PLAN] Returned existing workouts (no new created) due to unique index conflict: %s",
                                workout_ids,
                            )
                        else:
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
                status="active",
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

            # Planned sessions = number of workouts we attempted to generate
            try:
                applied_plan.planned_sessions_total = len(workouts_to_generate)
            except Exception:
                applied_plan.planned_sessions_total = None

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
                status=applied_plan.status,
                planned_sessions_total=applied_plan.planned_sessions_total,
                actual_sessions_completed=applied_plan.actual_sessions_completed,
                adherence_pct=applied_plan.adherence_pct,
                notes=applied_plan.notes,
                dropout_reason=applied_plan.dropout_reason,
                dropped_at=applied_plan.dropped_at,
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

    async def advance_current_index(self, applied_plan_id: int, by: int = 1) -> Optional[int]:
        """Advance current_workout_index for the applied plan by N (default 1).
        Caps at last workout index + 1. Returns new index or None if plan not found.
        """
        try:
            user_id = self._require_user_id()
            stmt = (
                select(AppliedCalendarPlan)
                .options(selectinload(AppliedCalendarPlan.workouts))
                .where(
                    AppliedCalendarPlan.id == applied_plan_id,
                    AppliedCalendarPlan.user_id == user_id,
                )
            )
            res = await self.db.execute(stmt)
            plan = res.scalars().first()
            if not plan:
                return None
            current = int(getattr(plan, "current_workout_index", 0) or 0)
            try:
                step = int(by)
            except Exception:
                step = 1
            max_idx = 0
            try:
                if plan.workouts:
                    max_idx = max((int(w.order_index) for w in plan.workouts if w.order_index is not None), default=0)
            except Exception:
                max_idx = 0
            new_val = current + (step if step > 0 else 1)
            # allow pointer to move just past the last workout
            cap = max_idx + 1
            if new_val > cap:
                new_val = cap
            plan.current_workout_index = new_val
            await self.db.commit()
            return new_val
        except Exception:
            return None

    async def cancel_applied_plan(
        self,
        applied_plan_id: int,
        *,
        dropout_reason: Optional[str] = None,
    ) -> Optional[AppliedCalendarPlan]:
        """Mark an applied plan as cancelled/dropped for the current user.

        Sets is_active = False, status = 'cancelled' (if not already set),
        dropped_at = now and optionally updates dropout_reason.
        """
        user_id = self._require_user_id()
        try:
            stmt = (
                select(AppliedCalendarPlan)
                .where(
                    AppliedCalendarPlan.id == applied_plan_id,
                    AppliedCalendarPlan.user_id == user_id,
                )
            )
            res = await self.db.execute(stmt)
            plan = res.scalars().first()
            if not plan:
                return None

            plan.is_active = False
            # сохраняем существующий статус, если он уже задан явно
            if not plan.status:
                plan.status = "cancelled"
            if dropout_reason:
                plan.dropout_reason = dropout_reason[:64]
            plan.dropped_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(plan)
            return plan
        except Exception:
            await self.db.rollback()
            return None

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

    async def inject_mesocycle_into_applied_plan(
        self,
        applied_plan_id: int,
        *,
        mode: str,
        template_id: Optional[int] = None,
        source_mesocycle_id: Optional[int] = None,
        placement: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            stmt = (
                select(AppliedCalendarPlan)
                .options(selectinload(AppliedCalendarPlan.workouts))
                .where(
                    AppliedCalendarPlan.id == applied_plan_id,
                    AppliedCalendarPlan.user_id == self.user_id,
                )
            )
            res = await self.db.execute(stmt)
            plan = res.scalars().first()
            if not plan:
                return {"applied": False, "reason": "applied_plan_not_found"}

            headers = self._auth_headers()

            workouts_to_generate: List[Dict[str, Any]] = []
            eff_mode = mode or ""
            if not eff_mode:
                eff_mode = "by_Template" if template_id is not None else ("by_Existing" if source_mesocycle_id is not None else "")
            if eff_mode == "by_Template" and template_id is not None:
                tpl_svc = TemplateService(self.db, self.user_id)
                tpl = await tpl_svc.get_template(int(template_id))
                workouts_to_generate = self._build_workouts_from_template_response(tpl)
            elif eff_mode == "by_Existing" and source_mesocycle_id is not None:
                workouts_to_generate = await self._build_workouts_from_existing_mesocycle(int(source_mesocycle_id))
            else:
                return {"applied": False, "reason": "invalid_params"}

            if not workouts_to_generate:
                return {"applied": False, "reason": "empty_schedule"}

            anchor_index = -1
            if isinstance(placement, dict):
                mode_str = str(placement.get("mode") or "").strip()
                poi = placement.get("plan_order_index")
                if poi is not None:
                    try:
                        anchor_index = int(poi)
                    except Exception:
                        anchor_index = -1
                if anchor_index < 0 and mode_str == "Insert_After_Workout":
                    return {"applied": False, "reason": "invalid_plan_order_index"}
                if anchor_index < 0 and mode_str == "Insert_After_Mesocycle":
                    try:
                        m_idx = int(placement.get("mesocycle_index"))
                    except Exception:
                        m_idx = None
                    if m_idx is not None and m_idx >= 0:
                        try:
                            # Compute cumulative workout counts per mesocycle from base CalendarPlan
                            from ..models.calendar import CalendarPlan as _CP, Mesocycle as _M, Microcycle as _MC, PlanWorkout as _PW
                            stmt_cp = (
                                select(_CP)
                                .options(
                                    selectinload(_CP.mesocycles)
                                        .selectinload(_M.microcycles)
                                        .selectinload(_MC.plan_workouts)
                                )
                                .where(_CP.id == plan.calendar_plan_id)
                            )
                            res_cp = await self.db.execute(stmt_cp)
                            cp = res_cp.scalars().first()
                            cum = []  # cumulative workout counts end index for each meso (exclusive)
                            total = 0
                            if cp and cp.mesocycles:
                                for ms in sorted(cp.mesocycles, key=lambda x: (x.order_index or 0, x.id)):
                                    w_count = 0
                                    for mc in sorted(ms.microcycles or [], key=lambda x: (x.order_index or 0, x.id)):
                                        w_count += len(getattr(mc, 'plan_workouts', []) or [])
                                    total += w_count
                                    cum.append(total)
                            if cum:
                                # After mesocycle m_idx means before the first workout of m_idx+1 -> insert_pos = cum[m_idx]
                                if m_idx < len(cum):
                                    anchor_index = cum[m_idx] - 1  # after last workout of this meso
                                else:
                                    # out of range -> append to end
                                    anchor_index = -1
                        except Exception:
                            anchor_index = -1
            ordered = sorted(plan.workouts or [], key=lambda w: w.order_index)
            insert_pos = anchor_index + 1 if anchor_index >= 0 else (ordered[-1].order_index + 1 if ordered else 0)

            compute = ApplyPlanComputeSettings(
                compute_weights=True,
                rounding_step=2.5,
                rounding_mode=RoundingMode.nearest,
                generate_workouts=True,
                start_date=None,
            )
            # Determine baseline_date for scheduling inserted workouts and shifting subsequent ones
            baseline_date: Optional[datetime] = None
            try:
                # fetch existing workouts from workouts-service to inspect scheduled_for
                existing_ws = await self._fetch_workouts_for_applied_plan(plan.id)
                # Partition by order index relative to insert_pos
                fut = [w for w in existing_ws if (w.get("plan_order_index") is not None and int(w.get("plan_order_index")) >= insert_pos and w.get("scheduled_for") is not None)]
                prev = [w for w in existing_ws if (w.get("plan_order_index") is not None and int(w.get("plan_order_index")) < insert_pos and w.get("scheduled_for") is not None)]
                def _parse(dt: str) -> Optional[datetime]:
                    try:
                        return datetime.fromisoformat(dt)
                    except Exception:
                        return None
                if fut:
                    # minimal future date at/after insert_pos
                    fds = sorted([_parse(w.get("scheduled_for")) for w in fut if _parse(w.get("scheduled_for")) is not None])
                    if fds:
                        baseline_date = fds[0]
                if baseline_date is None and prev:
                    pds = sorted([_parse(w.get("scheduled_for")) for w in prev if _parse(w.get("scheduled_for")) is not None])
                    if pds:
                        baseline_date = pds[-1] + timedelta(days=1)
                if baseline_date is None and plan.start_date is not None:
                    baseline_date = plan.start_date
                if baseline_date is None:
                    baseline_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            except Exception:
                baseline_date = None

            # Populate plan_order_index and scheduled_for for inserted workouts
            try:
                if baseline_date is None:
                    # fall back to today at 9am to make them visible in UI
                    baseline_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
                for i, w in enumerate(workouts_to_generate):
                    w["plan_order_index"] = insert_pos + i
                    # preserve time of baseline across all inserted
                    dt = (baseline_date + timedelta(days=i))
                    w["scheduled_for"] = dt.isoformat()
            except Exception:
                pass

            # Shift existing workouts remotely before creating new ones to avoid conflicts
            shift_count = len(workouts_to_generate)
            shift_summary = None
            if shift_count:
                try:
                    shift_summary = await self._shift_schedule_via_rpc(
                        applied_plan_id=plan.id,
                        from_order_index=insert_pos,
                        delta_days=shift_count,
                        delta_index=shift_count,
                        exclude_ids=[],
                        only_future=True,
                        baseline_date=baseline_date,
                    )
                except Exception:
                    shift_summary = None
                # Block on shift failure: do not proceed to generation if shift did not succeed
                ok = False
                try:
                    if isinstance(shift_summary, dict):
                        ac = int(shift_summary.get("affected_count") or 0)
                        # we allow zero if реально нет будущих записей, но если в плане есть хвост, это ошибка
                        ok = ac >= 0
                    else:
                        ok = False
                except Exception:
                    ok = False
                if not ok:
                    logger.warning(
                        f"[APPLY_PLAN] Shift failed or returned invalid summary; aborting generation | applied_plan_id={plan.id} insert_pos={insert_pos} count={shift_count} summary={shift_summary}"
                    )
                    return {"applied": False, "reason": "shift_failed", "shift_summary": shift_summary}

            # Compute working weights for generated workouts if enabled
            if compute.compute_weights:
                # Collect required exercise IDs
                required_exercise_ids: set[int] = set()
                for w in workouts_to_generate:
                    for ex in (w.get("exercises") or []):
                        ex_id = ex.get("exercise_id")
                        if isinstance(ex_id, int):
                            required_exercise_ids.add(ex_id)

                # 1) Primary source: user_max_ids selected at plan apply
                selected_user_maxes = []
                try:
                    um_ids = getattr(plan, "user_max_ids", None)
                    if um_ids:
                        selected_user_maxes = await self._fetch_user_maxes_by_ids(list(um_ids))
                except Exception:
                    selected_user_maxes = []

                def _pick_preferred(existing: dict | None, candidate: dict | None) -> dict | None:
                    if candidate is None:
                        return existing
                    if existing is None:
                        return candidate
                    try:
                        ew = float(existing.get("max_weight") or 0)
                    except Exception:
                        ew = 0.0
                    try:
                        cw = float(candidate.get("max_weight") or 0)
                    except Exception:
                        cw = 0.0
                    return candidate if cw >= ew else existing

                user_max_by_ex: dict[int, dict] = {}
                for um in selected_user_maxes or []:
                    try:
                        exid = int(um.get("exercise_id"))
                    except Exception:
                        continue
                    user_max_by_ex[exid] = _pick_preferred(user_max_by_ex.get(exid), um) or um

                # 2) Fill gaps by fetching by exercise_id
                missing_exercises = required_exercise_ids - set(user_max_by_ex.keys())
                if missing_exercises:
                    fetched = await self._fetch_user_maxes(list(missing_exercises))
                    for um in fetched or []:
                        try:
                            exid = int(um.get("exercise_id"))
                        except Exception:
                            continue
                        if exid not in user_max_by_ex:
                            user_max_by_ex[exid] = um

                # Build effective 1RMs strictly from the chosen set
                effective_1rms: dict[int, float] = {}
                for exid, um in user_max_by_ex.items():
                    try:
                        true_1rm = await workout_calculation.WorkoutCalculator.get_true_1rm_from_user_max(um, headers=headers)
                    except Exception:
                        true_1rm = None
                    try:
                        eff = float(true_1rm) if true_1rm is not None else float(um.get("max_weight") or 0)
                    except Exception:
                        eff = 0.0
                    effective_1rms[exid] = eff

                def _round_to_step(value: float) -> float:
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

                # Fill missing triplets and compute working_weight
                for w in workouts_to_generate:
                    for ex in (w.get("exercises") or []):
                        ex_id = ex.get("exercise_id")
                        eff_1rm = effective_1rms.get(ex_id)
                        for s in (ex.get("sets") or []):
                            intensity = s.get("intensity")
                            effort = s.get("effort")
                            volume = s.get("volume")
                            try:
                                if intensity is not None and effort is not None and volume is None:
                                    volume = await get_volume(intensity=intensity, effort=effort, headers=headers)
                                    s["volume"] = volume
                                elif volume is not None and effort is not None and intensity is None:
                                    intensity = await get_intensity(volume=volume, effort=effort, headers=headers)
                                    s["intensity"] = intensity
                                elif volume is not None and intensity is not None and effort is None:
                                    effort = await get_effort(volume=volume, intensity=intensity, headers=headers)
                                    s["effort"] = effort
                            except Exception:
                                pass

                            weight = None
                            try:
                                if eff_1rm is not None and intensity is not None:
                                    weight = _round_to_step(float(eff_1rm) * (float(intensity) / 100.0))
                            except Exception:
                                weight = None
                            s["working_weight"] = weight

            workout_ids = await self._generate_workouts_via_rpc(applied_plan_id, workouts_to_generate, compute)
            if not workout_ids:
                return {"applied": False, "reason": "workout_generation_failed"}

            # Shift linear list to make room in applied plan representation
            for w in sorted(plan.workouts or [], key=lambda w: w.order_index, reverse=True):
                if w.order_index >= insert_pos:
                    w.order_index = w.order_index + len(workout_ids)
            await self.db.flush()

            # Create hierarchy: one AppliedMesocycle and one AppliedMicrocycle to contain inserted workouts
            from ..models.calendar import AppliedPlanWorkout, AppliedMesocycle, AppliedMicrocycle, AppliedWorkout

            # Compute new meso order_index: append as last
            meso_order = 0
            try:
                stmt_m = (
                    select(AppliedMesocycle)
                    .where(AppliedMesocycle.applied_plan_id == plan.id)
                    .order_by(AppliedMesocycle.order_index.desc(), AppliedMesocycle.id.desc())
                )
                r_m = await self.db.execute(stmt_m)
                last_m = r_m.scalars().first()
                meso_order = int(getattr(last_m, "order_index", -1) or -1) + 1 if last_m else 0
            except Exception:
                meso_order = 0
            a_meso = AppliedMesocycle(
                applied_plan_id=plan.id,
                mesocycle_id=None,
                order_index=meso_order,
            )
            self.db.add(a_meso)
            await self.db.flush()

            a_micro = AppliedMicrocycle(
                applied_mesocycle_id=a_meso.id,
                microcycle_id=None,
                order_index=0,
            )
            self.db.add(a_micro)
            await self.db.flush()

            for i, wid in enumerate(workout_ids):
                apw = AppliedPlanWorkout(
                    applied_plan_id=plan.id,
                    workout_id=wid,
                    order_index=insert_pos + i,
                )
                self.db.add(apw)
                aw = AppliedWorkout(
                    applied_microcycle_id=a_micro.id,
                    workout_id=wid,
                    order_index=i,
                )
                self.db.add(aw)
            await self.db.flush()
            try:
                await self._create_instances_for_workouts(workout_ids, workouts_to_generate)
            except Exception:
                pass

            # Adjust current_workout_index if insertion is before current pointer
            try:
                cur = int(getattr(plan, "current_workout_index", 0) or 0)
                if insert_pos <= cur:
                    plan.current_workout_index = cur + len(workout_ids)
            except Exception:
                pass
            await self.db.commit()
            # Recalculate end_date to reflect extended plan length
            try:
                # Reload plan to ensure we have current state
                await self.db.refresh(plan)
                total_days = 0
                # Prefer using the base calendar plan structure if available to estimate days per microcycle
                try:
                    from ..models.calendar import CalendarPlan, Mesocycle as _M, Microcycle as _MC
                    stmt_cp = (
                        select(CalendarPlan)
                        .options(
                            selectinload(CalendarPlan.mesocycles)
                                .selectinload(_M.microcycles)
                        )
                        .where(CalendarPlan.id == plan.calendar_plan_id)
                    )
                    res_cp = await self.db.execute(stmt_cp)
                    cp = res_cp.scalars().first()
                    if cp and cp.mesocycles:
                        for m in cp.mesocycles:
                            for mc in m.microcycles or []:
                                if mc.days_count is not None:
                                    total_days += int(mc.days_count)
                                else:
                                    # Fallback: assume 1 day per planned workout entry if unspecified
                                    total_days += max(1, len(getattr(mc, 'plan_workouts', []) or []))
                except Exception:
                    pass
                if total_days <= 0:
                    # Fallback approximation: one workout per day over all applied workouts
                    try:
                        applied_workouts_count = len(plan.workouts or [])
                    except Exception:
                        applied_workouts_count = 0
                    total_days = max(1, applied_workouts_count)
                if plan.start_date is not None:
                    plan.end_date = plan.start_date + timedelta(days=total_days)
                    # Ensure naive datetime to match existing convention
                    plan.end_date = plan.end_date.replace(tzinfo=None)
                    await self.db.commit()
            except Exception:
                # Non-fatal if we fail to recalc end_date
                pass
            return {"applied": True, "inserted": len(workout_ids), "start_index": insert_pos, "workout_ids": workout_ids}
        except Exception:
            return {"applied": False, "reason": "exception"}

    def _build_workouts_from_template_response(self, tpl_resp) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            for mc in sorted((tpl_resp.microcycles or []), key=lambda m: (m.order_index or 0)):
                schedule = mc.schedule or {}
                items = list(schedule.items())
                def _key(x):
                    try:
                        return int(str(x[0]).strip().split()[-1])
                    except Exception:
                        return 0
                for day_key, day_items in sorted(items, key=_key):
                    workout_exercises: List[Dict[str, Any]] = []
                    for item in day_items or []:
                        ex_id = item.get("exercise_id") or item.get("exercise_list_id")
                        if ex_id is None:
                            continue
                        sets = []
                        for s in item.get("sets") or []:
                            sets.append({
                                "exercise_id": int(ex_id),
                                "intensity": s.get("intensity"),
                                "effort": s.get("effort"),
                                "volume": s.get("volume"),
                                "working_weight": s.get("working_weight"),
                            })
                        workout_exercises.append({
                            "exercise_id": int(ex_id),
                            "sets": sets,
                        })
                    if workout_exercises:
                        try:
                            day_idx = int(str(day_key).strip().split()[-1])
                            w_name = f"{tpl_resp.name}: Day {day_idx}"
                        except Exception:
                            w_name = f"{tpl_resp.name}: {str(day_key)}"
                        out.append({
                            "name": w_name,
                            "scheduled_for": None,
                            "plan_order_index": None,
                            "exercises": workout_exercises,
                        })
        except Exception:
            return []
        return out

    async def _fetch_workouts_for_applied_plan(self, applied_plan_id: int) -> List[Dict[str, Any]]:
        """Fetch workouts list from workouts-service for the given applied plan.
        Returns list of dicts with at least id, plan_order_index, scheduled_for.
        """
        base = os.getenv("WORKOUTS_SERVICE_URL", "http://localhost:8004")
        headers = self._auth_headers()
        url = urllib.parse.urljoin(base + "/", f"workouts/?applied_plan_id={applied_plan_id}")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list):
                        return data
        except Exception:
            pass
        return []

    async def _shift_schedule_via_rpc(
        self,
        *,
        applied_plan_id: int,
        from_order_index: int,
        delta_days: int,
        delta_index: int,
        exclude_ids: List[int],
        only_future: bool,
        baseline_date: Optional[datetime],
    ) -> Optional[Dict[str, Any]]:
        base = os.getenv("WORKOUTS_SERVICE_URL", "http://localhost:8004")
        headers = self._auth_headers()
        path = "workouts/schedule/shift-in-plan"
        url = urllib.parse.urljoin(base + "/", path)
        payload = {
            "applied_plan_id": applied_plan_id,
            "from_order_index": from_order_index,
            "delta_days": delta_days,
            "delta_index": delta_index,
            "exclude_ids": exclude_ids,
            "only_future": only_future,
            "baseline_date": baseline_date.isoformat() if baseline_date is not None else None,
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
        return None

    async def get_plan_analytics(
        self,
        applied_plan_id: int,
        *,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        group_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        base = os.getenv("WORKOUTS_SERVICE_URL", "http://localhost:8004")
        headers = self._auth_headers()
        path = "workouts/analytics/in-plan"
        url = urllib.parse.urljoin(base + "/", path)
        params = {"applied_plan_id": applied_plan_id}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if group_by:
            params["group_by"] = group_by
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.get(url, params=params, headers=headers)
                res.raise_for_status()
                data = res.json()
        except Exception as exc:
            raise ValueError(f"Failed to fetch analytics: {exc}") from exc

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return {"items": []}

        def _safe_float(value: Any) -> float:
            try:
                if value is None:
                    return 0.0
                return float(value)
            except Exception:
                return 0.0

        effort_values = []
        intensity_values = []
        volume_sum = 0.0
        sets_sum = 0.0
        for item in items:
            metrics = item.get("metrics") if isinstance(item, dict) else None
            if not isinstance(metrics, dict):
                continue
            ev = metrics.get("effort_avg")
            if ev is not None:
                effort_values.append(_safe_float(ev))
            iv = metrics.get("intensity_avg")
            if iv is not None:
                intensity_values.append(_safe_float(iv))
            volume_sum += _safe_float(metrics.get("volume_sum"))
            sets_sum += _safe_float(metrics.get("sets_count"))

        def _avg(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        totals = {
            "effort_avg": _avg(effort_values),
            "intensity_avg": _avg(intensity_values),
            "volume_sum": volume_sum,
            "sets_count": sets_sum,
        }
        data["totals"] = totals
        return data

    async def _build_workouts_from_existing_mesocycle(self, mesocycle_id: int) -> List[Dict[str, Any]]:
        stmt = (
            select(Mesocycle)
            .options(
                selectinload(Mesocycle.microcycles)
                .selectinload(Microcycle.plan_workouts)
                .selectinload(PlanWorkout.exercises)
                .selectinload(PlanExercise.sets)
            )
            .where(Mesocycle.id == mesocycle_id)
        )
        res = await self.db.execute(stmt)
        src = res.scalars().first()
        if not src:
            return []
        out: List[Dict[str, Any]] = []
        for mc in sorted(src.microcycles or [], key=lambda m: (m.order_index or 0, m.id)):
            for pw in sorted(mc.plan_workouts or [], key=lambda w: (w.order_index or 0, w.id)):
                workout_exercises: List[Dict[str, Any]] = []
                for ex in sorted(pw.exercises or [], key=lambda e: (e.order_index or 0, e.id)):
                    sets: List[Dict[str, Any]] = []
                    for s in sorted(ex.sets or [], key=lambda z: (z.order_index or 0, z.id)):
                        sets.append({
                            "exercise_id": int(ex.exercise_definition_id) if ex.exercise_definition_id is not None else None,
                            "intensity": s.intensity,
                            "effort": s.effort,
                            "volume": s.volume,
                            "working_weight": s.working_weight,
                        })
                    workout_exercises.append({"exercise_id": ex.exercise_definition_id, "sets": sets})
                if workout_exercises:
                    # Build a friendly workout name using day label or fallback to order index (1-based)
                    try:
                        dl = str(getattr(pw, "day_label", "")).strip() or None
                    except Exception:
                        dl = None
                    if not dl:
                        try:
                            idx = int(getattr(pw, "order_index", 0) or 0) + 1
                            dl = f"Day {idx}"
                        except Exception:
                            dl = "Day"
                    wname = f"{src.name}: {dl}"
                    out.append({
                        "name": wname,
                        "scheduled_for": None,
                        "plan_order_index": None,
                        "exercises": workout_exercises,
                    })
        return out
