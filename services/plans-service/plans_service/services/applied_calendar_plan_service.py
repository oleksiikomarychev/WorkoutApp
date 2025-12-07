import asyncio
import math
import os
import urllib.parse
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog
from backend_common.http_client import ServiceClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import workout_calculation
from ..models.calendar import (
    AppliedCalendarPlan,
    CalendarPlan,
    Mesocycle,
    Microcycle,
    PlanExercise,
    PlanWorkout,
)
from ..rpc import get_effort, get_intensity, get_volume
from ..schemas.calendar_plan import (
    AppliedCalendarPlanResponse,
    ApplyPlanComputeSettings,
    CalendarPlanResponse,
    RoundingMode,
    UserMaxResponse,
)
from ..schemas.mesocycle import MesocycleResponse, MicrocycleResponse
from .calendar_plan_service import CalendarPlanService
from .template_service import TemplateService

logger = structlog.get_logger(__name__)


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

    async def _fetch_user_maxes(self, exercise_ids: list[int]) -> list[dict]:
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
                except (httpx.RequestError, ValueError):
                    return []

            tasks = [fetch_one(ex_id) for ex_id in exercise_ids]
            results = await asyncio.gather(*tasks)

            user_maxes = [max for sublist in results for max in sublist]
            return user_maxes

    async def _fetch_user_maxes_by_ids(self, user_max_ids: list[int]) -> list[dict]:
        if not user_max_ids:
            return []
        headers = self._auth_headers()
        base = "http://user-max-service:8003"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{base}/user-max/by-ids"
                params = {"ids": user_max_ids}
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    return data
            except (httpx.RequestError, ValueError):
                logger.warning("_fetch_user_maxes_by_ids_failed", user_max_ids=user_max_ids, exc_info=True)
        return []

    async def _ensure_exercises_present(self, exercise_ids: set[int]) -> None:
        if not exercise_ids:
            return

        base = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")
        headers = self._auth_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for ex_id in exercise_ids:
                try:
                    url = f"{base.rstrip('/')}/exercises/definitions/{ex_id}"
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        continue
                except httpx.RequestError:
                    continue
        return

    async def _fetch_exercise_metadata(self, exercise_ids: set[int]) -> dict[int, dict[str, Any]]:
        if not exercise_ids:
            return {}

        base = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")
        headers = self._auth_headers()
        params = {"ids": ",".join(str(eid) for eid in sorted(exercise_ids))}
        url = f"{base.rstrip('/')}/exercises/definitions"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list):
                    return {}
                meta: dict[int, dict[str, Any]] = {}
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    try:
                        ex_id = int(item.get("id"))
                    except (TypeError, ValueError):
                        continue
                    meta[ex_id] = item
                return meta
        except (httpx.RequestError, ValueError):
            logger.warning("_fetch_exercise_metadata_failed", exercise_ids=list(exercise_ids), exc_info=True)
            return {}

    def _build_exercise_scope(self, exercise_meta: dict[int, dict[str, Any]]) -> dict[str, dict[str, set[int]]]:
        from collections import defaultdict

        by_group: dict[str, set[int]] = defaultdict(set)
        by_target: dict[str, set[int]] = defaultdict(set)

        for ex_id, meta in (exercise_meta or {}).items():
            muscle_group = (meta.get("muscle_group") or "").strip().lower()
            if muscle_group:
                by_group[muscle_group].add(ex_id)
            for tm in meta.get("target_muscles") or []:
                key = (tm or "").strip().lower()
                if key:
                    by_target[key].add(ex_id)

        return {
            "by_muscle_group": {k: set(v) for k, v in by_group.items()},
            "by_target_muscle": {k: set(v) for k, v in by_target.items()},
        }

    async def _generate_workouts_via_rpc(
        self, applied_plan_id: int, workouts: list[dict[str, Any]], compute: ApplyPlanComputeSettings
    ) -> list[int] | None:
        bases = [os.getenv("WORKOUTS_SERVICE_URL", "http://localhost:8004")]
        headers = self._auth_headers()

        logger.info(
            "apply_plan_generate_workouts",
            applied_plan_id=applied_plan_id,
            workout_count=len(workouts),
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            for base in bases:
                paths = ["workouts/workout-generation/generate"]
                for path in paths:
                    url = urllib.parse.urljoin(base, path)
                    try:
                        logger.info("apply_plan_rpc_post", url=url)
                        response = await client.post(
                            url,
                            json={
                                "applied_plan_id": applied_plan_id,
                                "compute_weights": compute.compute_weights,
                                "rounding_step": compute.rounding_step,
                                "rounding_mode": compute.rounding_mode,
                                "workouts": workouts,
                            },
                            headers=headers,
                        )
                        response.raise_for_status()
                        body = response.json()
                        workout_ids = body.get("workout_ids") if isinstance(body, dict) else None
                        if isinstance(workout_ids, list) and len(workout_ids) != len(workouts):
                            logger.warning(
                                "apply_plan_rpc_existing_workouts",
                                workout_ids=workout_ids,
                                attempted=len(workouts),
                            )
                        else:
                            logger.info("apply_plan_rpc_success", workout_ids=workout_ids)
                        return workout_ids
                    except httpx.HTTPStatusError as e:
                        logger.error(
                            "apply_plan_rpc_http_error",
                            url=url,
                            status_code=e.response.status_code,
                            body=e.response.text,
                        )
                    except httpx.RequestError as e:
                        logger.error("apply_plan_rpc_failed", url=url, error=str(e))

        logger.warning("apply_plan_rpc_all_failed", applied_plan_id=applied_plan_id)
        return None

    async def _create_instances_for_workouts(
        self,
        workout_ids: list[int],
        workouts_to_generate: list[dict[str, Any]],
    ) -> None:
        if not workout_ids or not workouts_to_generate:
            return
        base = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")

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
                                "reps": s.get("volume"),
                                "weight": s.get("working_weight"),
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

                        if res.status_code not in (200, 201):
                            print(
                                f"[APPLY_PLAN] Failed to create instance for workout {workout_id}: "
                                f"status={res.status_code} body={res.text}"
                            )
                    except httpx.RequestError as e:
                        print(f"[APPLY_PLAN] Exception creating instance for workout {workout_id}: {e}")

    async def apply_plan(
        self, plan_id: int, compute: ApplyPlanComputeSettings, user_max_ids: list[int]
    ) -> AppliedCalendarPlanResponse:
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
                if ex_id is not None:
                    user_max_by_exercise[int(ex_id)] = _pick_preferred(user_max_by_exercise.get(int(ex_id)), um)

            missing_exercises = required_exercises - set(user_max_by_exercise.keys())
            if missing_exercises:
                fetched = await self._fetch_user_maxes(list(missing_exercises))
                for um in fetched or []:
                    ex_id = um.get("exercise_id")
                    if ex_id is not None:
                        user_max_by_exercise[int(ex_id)] = _pick_preferred(user_max_by_exercise.get(int(ex_id)), um)

            user_maxes = list(user_max_by_exercise.values())
            await self._ensure_exercises_present(required_exercises)
            exercise_metadata = await self._fetch_exercise_metadata(required_exercises)
            exercise_scope = self._build_exercise_scope(exercise_metadata)

            stmt = (
                update(AppliedCalendarPlan)
                .where(
                    AppliedCalendarPlan.is_active.is_(True),
                    AppliedCalendarPlan.user_id == user_id,
                )
                .values(is_active=False)
            )
            await self.db.execute(stmt)

            start_date = compute.start_date or datetime.now(UTC)
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
                                            volume = await get_volume(
                                                intensity=intensity, effort=effort, headers=headers
                                            )
                                        elif volume is not None and effort is not None:
                                            intensity = await get_intensity(
                                                volume=volume, effort=effort, headers=headers
                                            )
                                        elif volume is not None and intensity is not None:
                                            effort = await get_effort(
                                                volume=volume, intensity=intensity, headers=headers
                                            )
                                    except Exception:
                                        pass

                                    weight = None
                                    if compute.compute_weights and intensity is not None and user_max is not None:
                                        eff = effective_1rms.get(user_max["exercise_id"])
                                        if eff is None:
                                            true_1rm = (
                                                await workout_calculation.WorkoutCalculator.get_true_1rm_from_user_max(
                                                    user_max, headers=headers
                                                )
                                            )
                                            eff = (
                                                float(true_1rm)
                                                if true_1rm is not None
                                                else float(user_max["max_weight"])
                                            )
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
                        mc.normalization_rules,
                        exercise_scope,
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

    async def get_applied_plan_by_id(self, plan_id: int) -> AppliedCalendarPlan | None:
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
                    selectinload(AppliedCalendarPlan.workouts),
                )
                .where(
                    AppliedCalendarPlan.id == plan_id,
                    AppliedCalendarPlan.user_id == user_id,
                )
            )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception:
            logger.exception("get_applied_plan_by_id_failed", plan_id=plan_id)
            return None

    async def get_flattened_plan_workouts(self, applied_plan_id: int) -> list[dict[str, Any]]:
        plan = await self.get_applied_plan_by_id(applied_plan_id)
        if not plan or not plan.calendar_plan:
            return []

        mesocycles = sorted(
            plan.calendar_plan.mesocycles or [],
            key=lambda m: (m.order_index if m.order_index is not None else 0, m.id),
        )

        flattened_workouts = []
        current_global_index = 0

        for meso in mesocycles:
            meso_name = meso.name or "Unnamed Meso"

            microcycles = sorted(
                meso.microcycles or [],
                key=lambda mc: (mc.order_index if mc.order_index is not None else 0, mc.id),
            )

            for micro in microcycles:
                micro_name = micro.name or "Microcycle"

                p_workouts = sorted(
                    micro.plan_workouts or [],
                    key=lambda pw: (pw.order_index if pw.order_index is not None else 0, pw.id),
                )

                for pw in p_workouts:
                    exercises_data = []
                    for ex in pw.exercises or []:
                        sets_data = []
                        for s in ex.sets or []:
                            sets_data.append(
                                {
                                    "volume": s.volume,
                                    "intensity": s.intensity,
                                    "effort": s.effort,
                                    "working_weight": s.working_weight,
                                    "tempo": s.tempo,
                                    "rest_seconds": s.rest_seconds,
                                }
                            )
                        exercises_data.append(
                            {
                                "exercise_definition_id": ex.exercise_definition_id,
                                "sets": sets_data,
                                "notes": ex.notes,
                            }
                        )

                    flattened_workouts.append(
                        {
                            "plan_workout_id": pw.id,
                            "name": pw.name,
                            "day_label": pw.day_label,
                            "order_index": pw.order_index,
                            "meso_name": meso_name,
                            "micro_name": micro_name,
                            "micro_id": micro.id,
                            "micro_days_count": micro.days_count,
                            "meso_id": meso.id,
                            "exercises": exercises_data,
                            "global_index": current_global_index,
                        }
                    )
                    current_global_index += 1

        return flattened_workouts

    async def get_user_applied_plans(self) -> list[AppliedCalendarPlanResponse]:
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
                    selectinload(AppliedCalendarPlan.workouts),
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
                                    days_count=mc.days_count,
                                )
                                for mc in m.microcycles
                            ],
                        )
                        for m in p.calendar_plan.mesocycles
                    ],
                )

                response.append(
                    AppliedCalendarPlanResponse(
                        id=p.id,
                        calendar_plan_id=p.calendar_plan_id,
                        start_date=p.start_date,
                        end_date=p.end_date,
                        is_active=p.is_active,
                        calendar_plan=calendar_plan_response,
                        next_workout=None,
                    )
                )

            return response
        except Exception:
            logger.exception("get_user_applied_plans_failed")
            return []

    async def get_active_plan(self) -> AppliedCalendarPlan | None:
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
                selectinload(AppliedCalendarPlan.workouts),
            )
            .where(
                AppliedCalendarPlan.is_active.is_(True),
                AppliedCalendarPlan.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def advance_current_index(self, applied_plan_id: int, by: int = 1) -> int | None:
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
            except (TypeError, ValueError):
                step = 1
            max_idx = 0
            try:
                if plan.workouts:
                    max_idx = max(
                        (int(w.order_index) for w in plan.workouts if w.order_index is not None),
                        default=0,
                    )
            except (TypeError, ValueError):
                max_idx = 0
            new_val = current + (step if step > 0 else 1)

            cap = max_idx + 1
            if new_val > cap:
                new_val = cap
            plan.current_workout_index = new_val
            await self.db.commit()
            return new_val
        except Exception:
            logger.exception("advance_current_index_failed", applied_plan_id=applied_plan_id)
            return None

    async def cancel_applied_plan(
        self,
        applied_plan_id: int,
        *,
        dropout_reason: str | None = None,
    ) -> AppliedCalendarPlan | None:
        user_id = self._require_user_id()
        try:
            stmt = select(AppliedCalendarPlan).where(
                AppliedCalendarPlan.id == applied_plan_id,
                AppliedCalendarPlan.user_id == user_id,
            )
            res = await self.db.execute(stmt)
            plan = res.scalars().first()
            if not plan:
                return None

            plan.is_active = False

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
            logger.exception("cancel_applied_plan_failed", applied_plan_id=applied_plan_id)
            return None

    def _apply_normalization(
        self,
        effective_1rms: dict[int, float],
        value: float | None,
        unit: str | None,
        rules: list[dict] | None = None,
        exercise_scope: dict[str, dict[str, set[int]]] | None = None,
    ) -> None:
        def _apply_to_exercises(exercise_ids: list[int], adj_value: float, adj_unit: str) -> None:
            normalized_unit = (adj_unit or "").lower()
            if normalized_unit in {"percentage", "%"}:
                for exercise_id in exercise_ids:
                    current = effective_1rms.get(exercise_id)
                    if current is None:
                        continue
                    effective_1rms[exercise_id] = current * (1 + adj_value / 100.0)
            elif normalized_unit in {"absolute", "kg"}:
                for exercise_id in exercise_ids:
                    current = effective_1rms.get(exercise_id)
                    if current is None:
                        continue
                    effective_1rms[exercise_id] = current + adj_value

        if value is not None and unit is not None:
            _apply_to_exercises(list(effective_1rms.keys()), value, unit)

        if not rules:
            return

        muscle_group_index = (exercise_scope or {}).get("by_muscle_group") or {}
        target_muscle_index = (exercise_scope or {}).get("by_target_muscle") or {}

        for rule in rules or []:
            exercise_ids = rule.get("exercise_ids") or []
            muscle_groups = rule.get("muscle_groups") or []
            target_muscles = rule.get("target_muscles") or []
            rule_value = rule.get("value")
            rule_unit = rule.get("unit")
            if rule_value is None or rule_unit is None:
                continue

            scoped_ids: set[int] = set()

            for raw_id in exercise_ids:
                try:
                    scoped_ids.add(int(raw_id))
                except (TypeError, ValueError):
                    continue

            for mg in muscle_groups:
                key = (mg or "").strip().lower()
                if key and key in muscle_group_index:
                    scoped_ids.update(muscle_group_index[key])

            for tm in target_muscles:
                key = (tm or "").strip().lower()
                if key and key in target_muscle_index:
                    scoped_ids.update(target_muscle_index[key])

            if not scoped_ids:
                continue

            _apply_to_exercises(sorted(scoped_ids), rule_value, rule_unit)

    async def inject_mesocycle_into_applied_plan(
        self,
        applied_plan_id: int,
        *,
        mode: str,
        template_id: int | None = None,
        source_mesocycle_id: int | None = None,
        placement: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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

            workouts_to_generate: list[dict[str, Any]] = []
            eff_mode = mode or ""
            if not eff_mode:
                eff_mode = (
                    "by_Template"
                    if template_id is not None
                    else ("by_Existing" if source_mesocycle_id is not None else "")
                )
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
                    except (TypeError, ValueError):
                        anchor_index = -1
                if anchor_index < 0 and mode_str == "Insert_After_Workout":
                    return {"applied": False, "reason": "invalid_plan_order_index"}
                if anchor_index < 0 and mode_str == "Insert_After_Mesocycle":
                    try:
                        m_idx = int(placement.get("mesocycle_index"))
                    except (TypeError, ValueError):
                        m_idx = None
                    if m_idx is not None and m_idx >= 0:
                        try:
                            from ..models.calendar import CalendarPlan as _CP
                            from ..models.calendar import Mesocycle as _M
                            from ..models.calendar import Microcycle as _MC

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
                            cum = []
                            total = 0
                            if cp and cp.mesocycles:
                                for ms in sorted(cp.mesocycles, key=lambda x: (x.order_index or 0, x.id)):
                                    w_count = 0
                                    for mc in sorted(
                                        ms.microcycles or [],
                                        key=lambda x: (x.order_index or 0, x.id),
                                    ):
                                        w_count += len(getattr(mc, "plan_workouts", []) or [])
                                    total += w_count
                                    cum.append(total)
                            if cum:
                                if m_idx < len(cum):
                                    anchor_index = cum[m_idx] - 1
                                else:
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

            baseline_date: datetime | None = None
            try:
                existing_ws = await self._fetch_workouts_for_applied_plan(plan.id)

                fut = [
                    w
                    for w in existing_ws
                    if (
                        w.get("plan_order_index") is not None
                        and int(w.get("plan_order_index")) >= insert_pos
                        and w.get("scheduled_for") is not None
                    )
                ]
                prev = [
                    w
                    for w in existing_ws
                    if (
                        w.get("plan_order_index") is not None
                        and int(w.get("plan_order_index")) < insert_pos
                        and w.get("scheduled_for") is not None
                    )
                ]

                def _parse(dt: str) -> datetime | None:
                    try:
                        return datetime.fromisoformat(dt)
                    except ValueError:
                        return None

                if fut:
                    fds = sorted(
                        [_parse(w.get("scheduled_for")) for w in fut if _parse(w.get("scheduled_for")) is not None]
                    )
                    if fds:
                        baseline_date = fds[0]
                if baseline_date is None and prev:
                    pds = sorted(
                        [_parse(w.get("scheduled_for")) for w in prev if _parse(w.get("scheduled_for")) is not None]
                    )
                    if pds:
                        baseline_date = pds[-1] + timedelta(days=1)
                if baseline_date is None and plan.start_date is not None:
                    baseline_date = plan.start_date
                if baseline_date is None:
                    baseline_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            except Exception:
                baseline_date = None

            try:
                if baseline_date is None:
                    baseline_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
                for i, w in enumerate(workouts_to_generate):
                    w["plan_order_index"] = insert_pos + i

                    dt = baseline_date + timedelta(days=i)
                    w["scheduled_for"] = dt.isoformat()
            except Exception:
                logger.exception("inject_mesocycle_schedule_generation_failed", applied_plan_id=applied_plan_id)

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

                ok = False
                try:
                    if isinstance(shift_summary, dict):
                        ac = int(shift_summary.get("affected_count") or 0)

                        ok = ac >= 0
                    else:
                        ok = False
                except (TypeError, ValueError):
                    ok = False
                if not ok:
                    logger.warning(
                        "[APPLY_PLAN] Shift failed or returned invalid summary; "
                        "aborting generation | applied_plan_id=%s insert_pos=%s "
                        "count=%s summary=%s",
                        plan.id,
                        insert_pos,
                        shift_count,
                        shift_summary,
                    )
                    return {
                        "applied": False,
                        "reason": "shift_failed",
                        "shift_summary": shift_summary,
                    }

            if compute.compute_weights:
                required_exercise_ids: set[int] = set()
                for w in workouts_to_generate:
                    for ex in w.get("exercises") or []:
                        ex_id = ex.get("exercise_id")
                        if isinstance(ex_id, int):
                            required_exercise_ids.add(ex_id)

                selected_user_maxes = []
                try:
                    um_ids = getattr(plan, "user_max_ids", None)
                    if um_ids:
                        selected_user_maxes = await self._fetch_user_maxes_by_ids(list(um_ids))
                except Exception as e:
                    logger.exception("_fetch_user_maxes_by_ids_failed", exc_info=e)
                    selected_user_maxes = []

                def _pick_preferred(existing: dict | None, candidate: dict | None) -> dict | None:
                    if candidate is None:
                        return existing
                    if existing is None:
                        return candidate
                    try:
                        ew = float(existing.get("max_weight") or 0)
                    except (TypeError, ValueError):
                        ew = 0.0
                    try:
                        cw = float(candidate.get("max_weight") or 0)
                    except (TypeError, ValueError):
                        cw = 0.0
                    return candidate if cw >= ew else existing

                user_max_by_ex: dict[int, dict] = {}
                for um in selected_user_maxes or []:
                    try:
                        exid = int(um.get("exercise_id"))
                    except (TypeError, ValueError):
                        continue
                    user_max_by_ex[exid] = _pick_preferred(user_max_by_ex.get(exid), um) or um

                missing_exercises = required_exercise_ids - set(user_max_by_ex.keys())
                if missing_exercises:
                    fetched = await self._fetch_user_maxes(list(missing_exercises))
                    for um in fetched or []:
                        try:
                            exid = int(um.get("exercise_id"))
                        except (TypeError, ValueError):
                            continue
                        if exid not in user_max_by_ex:
                            user_max_by_ex[exid] = um

                effective_1rms: dict[int, float] = {}
                for exid, um in user_max_by_ex.items():
                    try:
                        true_1rm = await workout_calculation.WorkoutCalculator.get_true_1rm_from_user_max(
                            um, headers=headers
                        )
                    except Exception as e:
                        logger.exception("get_true_1rm_from_user_max_failed", exc_info=e)
                        true_1rm = None
                    try:
                        eff = float(true_1rm) if true_1rm is not None else float(um.get("max_weight") or 0)
                    except (TypeError, ValueError):
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

                for w in workouts_to_generate:
                    for ex in w.get("exercises") or []:
                        ex_id = ex.get("exercise_id")
                        eff_1rm = effective_1rms.get(ex_id)
                        for s in ex.get("sets") or []:
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
                            except Exception as e:
                                logger.exception("calculate_set_values_failed", exc_info=e)

                            weight = None
                            try:
                                if eff_1rm is not None and intensity is not None:
                                    weight = _round_to_step(float(eff_1rm) * (float(intensity) / 100.0))
                            except (TypeError, ValueError):
                                weight = None
                            s["working_weight"] = weight

            workout_ids = await self._generate_workouts_via_rpc(applied_plan_id, workouts_to_generate, compute)
            if not workout_ids:
                return {"applied": False, "reason": "workout_generation_failed"}

            for w in sorted(plan.workouts or [], key=lambda w: w.order_index, reverse=True):
                if w.order_index >= insert_pos:
                    w.order_index = w.order_index + len(workout_ids)
            await self.db.flush()

            from ..models.calendar import (
                AppliedMesocycle,
                AppliedMicrocycle,
                AppliedPlanWorkout,
                AppliedWorkout,
            )

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
            except Exception as e:
                logger.exception("fetch_applied_mesocycle_order_failed", exc_info=e)
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
            except Exception as e:
                logger.exception("_create_instances_for_workouts_failed", exc_info=e)

            try:
                cur = int(getattr(plan, "current_workout_index", 0) or 0)
                if insert_pos <= cur:
                    plan.current_workout_index = cur + len(workout_ids)
            except (TypeError, ValueError):
                pass
            await self.db.commit()

            try:
                await self.db.refresh(plan)
                total_days = 0

                try:
                    from ..models.calendar import CalendarPlan
                    from ..models.calendar import Mesocycle as _M
                    from ..models.calendar import Microcycle as _MC

                    stmt_cp = (
                        select(CalendarPlan)
                        .options(selectinload(CalendarPlan.mesocycles).selectinload(_M.microcycles))
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
                                    total_days += max(1, len(getattr(mc, "plan_workouts", []) or []))
                except Exception as e:
                    logger.exception("fetch_calendar_plan_failed", exc_info=e)
                if total_days <= 0:
                    try:
                        applied_workouts_count = len(plan.workouts or [])
                    except TypeError:
                        applied_workouts_count = 0
                    total_days = max(1, applied_workouts_count)
                if plan.start_date is not None:
                    plan.end_date = plan.start_date + timedelta(days=total_days)

                    plan.end_date = plan.end_date.replace(tzinfo=None)
                    await self.db.commit()
            except Exception as e:
                logger.exception("update_plan_end_date_failed", exc_info=e)

            return {
                "applied": True,
                "inserted": len(workout_ids),
                "start_index": insert_pos,
                "workout_ids": workout_ids,
            }
        except Exception as e:
            logger.exception("apply_plan_failed", exc_info=e)
            return {"applied": False, "reason": "exception"}

    def _build_workouts_from_template_response(self, tpl_resp) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        try:
            for mc in sorted((tpl_resp.microcycles or []), key=lambda m: (m.order_index or 0)):
                schedule = mc.schedule or {}
                items = list(schedule.items())

                def _key(x):
                    try:
                        return int(str(x[0]).strip().split()[-1])
                    except (TypeError, ValueError):
                        return 0

                for day_key, day_items in sorted(items, key=_key):
                    workout_exercises: list[dict[str, Any]] = []
                    for item in day_items or []:
                        ex_id = item.get("exercise_id") or item.get("exercise_list_id")
                        if ex_id is None:
                            continue
                        sets = []
                        for s in item.get("sets") or []:
                            sets.append(
                                {
                                    "exercise_id": int(ex_id),
                                    "intensity": s.get("intensity"),
                                    "effort": s.get("effort"),
                                    "volume": s.get("volume"),
                                    "working_weight": s.get("working_weight"),
                                }
                            )
                        workout_exercises.append(
                            {
                                "exercise_id": int(ex_id),
                                "sets": sets,
                            }
                        )
                    if workout_exercises:
                        try:
                            day_idx = int(str(day_key).strip().split()[-1])
                            w_name = f"{tpl_resp.name}: Day {day_idx}"
                        except (TypeError, ValueError):
                            w_name = f"{tpl_resp.name}: {str(day_key)}"
                        out.append(
                            {
                                "name": w_name,
                                "scheduled_for": None,
                                "plan_order_index": None,
                                "exercises": workout_exercises,
                            }
                        )
        except Exception:
            logger.exception("_build_workouts_from_template_response_failed")
            return []
        return out

    async def _fetch_workouts_for_applied_plan(self, applied_plan_id: int) -> list[dict[str, Any]]:
        base = os.getenv("WORKOUTS_SERVICE_URL", "http://localhost:8004")
        headers = self._auth_headers()
        url = urllib.parse.urljoin(base + "/", f"workouts/?applied_plan_id={applied_plan_id}")
        async with ServiceClient(timeout=15.0) as client:
            data = await client.get_json(url, headers=headers, default=[], applied_plan_id=applied_plan_id)
        return data if isinstance(data, list) else []

    async def _shift_schedule_via_rpc(
        self,
        *,
        applied_plan_id: int,
        from_order_index: int,
        delta_days: int,
        delta_index: int,
        exclude_ids: list[int],
        only_future: bool,
        baseline_date: datetime | None,
    ) -> dict[str, Any] | None:
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
        async with ServiceClient(timeout=20.0) as client:
            resp = await client.post(
                url, headers=headers, json=payload, expected_status=200, applied_plan_id=applied_plan_id
            )
        return resp.data if resp.success else None

    async def get_plan_analytics(
        self,
        applied_plan_id: int,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
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
        params["include_actual"] = "true"
        async with ServiceClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers, params=params, applied_plan_id=applied_plan_id)
        if not resp.success:
            raise ValueError(f"Failed to fetch analytics: status={resp.status_code}")
        data = resp.data

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return {"items": []}

        def _safe_float(value: Any) -> float:
            try:
                if value is None:
                    return 0.0
                return float(value)
            except (TypeError, ValueError):
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

        def _avg(values: list[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        totals = {
            "effort_avg": _avg(effort_values),
            "intensity_avg": _avg(intensity_values),
            "volume_sum": volume_sum,
            "sets_count": sets_sum,
        }
        data["totals"] = totals
        return data

    async def _build_workouts_from_existing_mesocycle(self, mesocycle_id: int) -> list[dict[str, Any]]:
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
        out: list[dict[str, Any]] = []
        for mc in sorted(src.microcycles or [], key=lambda m: (m.order_index or 0, m.id)):
            for pw in sorted(mc.plan_workouts or [], key=lambda w: (w.order_index or 0, w.id)):
                workout_exercises: list[dict[str, Any]] = []
                for ex in sorted(pw.exercises or [], key=lambda e: (e.order_index or 0, e.id)):
                    sets: list[dict[str, Any]] = []
                    for s in sorted(ex.sets or [], key=lambda z: (z.order_index or 0, z.id)):
                        sets.append(
                            {
                                "exercise_id": int(ex.exercise_definition_id)
                                if ex.exercise_definition_id is not None
                                else None,
                                "intensity": s.intensity,
                                "effort": s.effort,
                                "volume": s.volume,
                                "working_weight": s.working_weight,
                            }
                        )
                    workout_exercises.append({"exercise_id": ex.exercise_definition_id, "sets": sets})
                if workout_exercises:
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
                    out.append(
                        {
                            "name": wname,
                            "scheduled_for": None,
                            "plan_order_index": None,
                            "exercises": workout_exercises,
                        }
                    )
        return out
