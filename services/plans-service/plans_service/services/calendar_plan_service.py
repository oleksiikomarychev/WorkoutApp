import json
from typing import Any

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import CircularDependencyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..metrics import (
    CALENDAR_PLAN_VARIANTS_CREATED_TOTAL,
    CALENDAR_PLANS_CREATED_TOTAL,
    PLAN_MASS_EDITS_APPLIED_TOTAL,
    PLAN_WORKOUTS_GENERATED_TOTAL,
    PLANS_CACHE_ERRORS_TOTAL,
    PLANS_CACHE_HITS_TOTAL,
    PLANS_CACHE_MISSES_TOTAL,
)
from ..models.calendar import (
    AppliedCalendarPlan,
    AppliedMesocycle,
    AppliedMicrocycle,
    CalendarPlan,
    Mesocycle,
    Microcycle,
    PlanExercise,
    PlanSet,
    PlanWorkout,
)
from ..redis_client import (
    FAVORITE_PLANS_TTL_SECONDS,
    PLAN_DETAIL_TTL_SECONDS,
    PLAN_LIST_TTL_SECONDS,
    calendar_plan_key,
    favorite_plans_key,
    get_redis,
    invalidate_plans_cache,
    plans_list_key,
)
from ..schemas.calendar_plan import (
    CalendarPlanCreate,
    CalendarPlanResponse,
    CalendarPlanSummaryResponse,
    CalendarPlanUpdate,
    CalendarPlanVariantCreate,
    PlanMassEditCommand,
)

logger = structlog.get_logger(__name__)


class CalendarPlanService:
    async def create_plan(db: AsyncSession, plan_data: CalendarPlanCreate, user_id: str) -> CalendarPlanResponse:
        try:
            plan = CalendarPlan(
                name=plan_data.name,
                duration_weeks=plan_data.duration_weeks,
                is_active=True,
                user_id=user_id,
                primary_goal=plan_data.primary_goal,
                intended_experience_level=plan_data.intended_experience_level,
                intended_frequency_per_week=plan_data.intended_frequency_per_week,
                session_duration_target_min=plan_data.session_duration_target_min,
                primary_focus_lifts=plan_data.primary_focus_lifts,
                required_equipment=plan_data.required_equipment,
            )
            db.add(plan)
            await db.flush()
            plan.root_plan_id = plan.id
            plan_id = plan.id

            exercise_cache: dict[int, dict] = {}

            for meso_idx, mesocycle_data in enumerate(plan_data.mesocycles):
                mesocycle = Mesocycle(
                    name=mesocycle_data.name,
                    order_index=meso_idx,
                    duration_weeks=mesocycle_data.duration_weeks,
                    calendar_plan_id=plan.id,
                )
                db.add(mesocycle)
                await db.flush()

                for micro_idx, microcycle_data in enumerate(mesocycle_data.microcycles):
                    microcycle = Microcycle(
                        name=microcycle_data.name,
                        order_index=micro_idx,
                        days_count=microcycle_data.days_count,
                        normalization_value=microcycle_data.normalization_value,
                        normalization_unit=microcycle_data.normalization_unit,
                        normalization_rules=[rule.model_dump() for rule in (microcycle_data.normalization_rules or [])]
                        or None,
                        mesocycle_id=mesocycle.id,
                    )
                    db.add(microcycle)
                    await db.flush()

                    for workout_idx, workout_data in enumerate(microcycle_data.plan_workouts):
                        plan_workout = PlanWorkout(
                            day_label=workout_data.day_label,
                            order_index=workout_idx,
                            microcycle_id=microcycle.id,
                        )
                        db.add(plan_workout)
                        await db.flush()

                        for ex_idx, exercise_data in enumerate(workout_data.exercises):
                            ex_def_id = exercise_data.exercise_definition_id
                            if ex_def_id in exercise_cache:
                                exercise_details = exercise_cache[ex_def_id]
                            else:
                                exercise_details = await CalendarPlanService._get_exercise_details(ex_def_id)
                                exercise_cache[ex_def_id] = exercise_details

                            plan_exercise = PlanExercise(
                                exercise_definition_id=ex_def_id,
                                exercise_name=exercise_details["name"],
                                order_index=ex_idx,
                                plan_workout_id=plan_workout.id,
                            )
                            db.add(plan_exercise)
                            await db.flush()

                            for set_idx, set_data in enumerate(exercise_data.sets):
                                plan_set = PlanSet(
                                    order_index=set_idx,
                                    intensity=set_data.intensity,
                                    effort=set_data.effort,
                                    volume=set_data.volume,
                                    plan_exercise_id=plan_exercise.id,
                                )
                                db.add(plan_set)

            await db.commit()

            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets)
                )
                .where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
            )
            result = await db.execute(stmt)
            reloaded_plan = result.scalars().first()

            if not reloaded_plan:
                raise HTTPException(status_code=500, detail="Failed to load created plan")

            CALENDAR_PLANS_CREATED_TOTAL.inc()
            await invalidate_plans_cache(user_id, plan_ids=[reloaded_plan.id])
            return CalendarPlanService._get_plan_response(reloaded_plan)
        except Exception as e:
            await db.rollback()
            logger.exception("calendar_plan_create_failed", user_id=user_id)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    async def create_variant(
        db: AsyncSession,
        plan_id: int,
        user_id: str,
        variant_data: CalendarPlanVariantCreate,
    ) -> CalendarPlanResponse:
        stmt = (
            select(CalendarPlan)
            .options(
                selectinload(CalendarPlan.mesocycles)
                .selectinload(Mesocycle.microcycles)
                .selectinload(Microcycle.plan_workouts)
                .selectinload(PlanWorkout.exercises)
                .selectinload(PlanExercise.sets)
            )
            .where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
        )
        result = await db.execute(stmt)
        source = result.scalars().first()
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or permission denied")

        if source.root_plan_id != source.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Variants can be created only from the original plan",
            )

        variant_name = variant_data.name or f"{source.name} (вариант)"
        variant = CalendarPlan(
            name=variant_name,
            duration_weeks=source.duration_weeks,
            is_active=True,
            user_id=user_id,
            root_plan_id=source.id,
        )
        db.add(variant)
        await db.flush()

        for meso_idx, src_meso in enumerate(source.mesocycles or []):
            meso = Mesocycle(
                name=src_meso.name,
                order_index=src_meso.order_index,
                duration_weeks=src_meso.duration_weeks,
                calendar_plan_id=variant.id,
            )
            db.add(meso)
            await db.flush()

            for micro_idx, src_micro in enumerate(src_meso.microcycles or []):
                micro = Microcycle(
                    name=src_micro.name,
                    order_index=src_micro.order_index,
                    days_count=src_micro.days_count,
                    normalization_value=src_micro.normalization_value,
                    normalization_unit=src_micro.normalization_unit,
                    normalization_rules=getattr(src_micro, "normalization_rules", None),
                    mesocycle_id=meso.id,
                )
                db.add(micro)
                await db.flush()

                for w_idx, src_pw in enumerate(src_micro.plan_workouts or []):
                    pw = PlanWorkout(
                        day_label=src_pw.day_label,
                        order_index=src_pw.order_index,
                        microcycle_id=micro.id,
                    )
                    db.add(pw)
                    await db.flush()

                    for ex_idx, src_ex in enumerate(src_pw.exercises or []):
                        pe = PlanExercise(
                            exercise_definition_id=src_ex.exercise_definition_id,
                            exercise_name=src_ex.exercise_name,
                            order_index=src_ex.order_index,
                            plan_workout_id=pw.id,
                        )
                        db.add(pe)
                        await db.flush()

                        for set_idx, src_set in enumerate(src_ex.sets or []):
                            ps = PlanSet(
                                order_index=src_set.order_index,
                                intensity=src_set.intensity,
                                effort=src_set.effort,
                                volume=src_set.volume,
                                plan_exercise_id=pe.id,
                            )
                            db.add(ps)

        await db.commit()

        stmt2 = (
            select(CalendarPlan)
            .options(
                selectinload(CalendarPlan.mesocycles)
                .selectinload(Mesocycle.microcycles)
                .selectinload(Microcycle.plan_workouts)
                .selectinload(PlanWorkout.exercises)
                .selectinload(PlanExercise.sets)
            )
            .where(CalendarPlan.id == variant.id)
        )
        result2 = await db.execute(stmt2)
        created_variant = result2.scalars().first()
        CALENDAR_PLAN_VARIANTS_CREATED_TOTAL.inc()
        await invalidate_plans_cache(user_id, plan_ids=[variant.id, plan_id, source.id])
        return CalendarPlanService._get_plan_response(created_variant)

    async def list_variants(db: AsyncSession, plan_id: int, user_id: str) -> list[CalendarPlanSummaryResponse]:
        stmt = select(CalendarPlan).where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
        res = await db.execute(stmt)
        base = res.scalars().first()
        if not base:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or permission denied")
        root_id = base.root_plan_id

        stmt2 = select(CalendarPlan).where(CalendarPlan.root_plan_id == root_id).order_by(CalendarPlan.id.asc())
        res2 = await db.execute(stmt2)
        items = res2.scalars().all()
        summaries: list[CalendarPlanSummaryResponse] = []
        for p in items:
            summaries.append(
                CalendarPlanSummaryResponse(
                    id=p.id,
                    name=p.name,
                    duration_weeks=p.duration_weeks,
                    is_active=p.is_active,
                    is_favorite=False,
                    root_plan_id=p.root_plan_id,
                    is_original=(p.id == p.root_plan_id),
                    primary_goal=getattr(p, "primary_goal", None),
                    intended_experience_level=getattr(p, "intended_experience_level", None),
                    intended_frequency_per_week=getattr(p, "intended_frequency_per_week", None),
                    session_duration_target_min=getattr(p, "session_duration_target_min", None),
                )
            )
        return summaries

    async def get_plan(db: AsyncSession, plan_id: int, user_id: str) -> CalendarPlanResponse | None:
        cache_key = calendar_plan_key(user_id, plan_id)
        redis = await get_redis()
        if redis:
            try:
                cached_value = await redis.get(cache_key)
                if cached_value:
                    PLANS_CACHE_HITS_TOTAL.inc()
                    return CalendarPlanResponse.model_validate_json(cached_value)
                PLANS_CACHE_MISSES_TOTAL.inc()
            except Exception as exc:
                PLANS_CACHE_ERRORS_TOTAL.inc()
                logger.warning(
                    "plans_cache_get_failed",
                    key=cache_key,
                    error=str(exc),
                )

        try:
            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets)
                )
                .where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
            )
            result = await db.execute(stmt)
            plan = result.scalars().first()

            if not plan:
                return None

            response = CalendarPlanService._get_plan_response(plan)
            if redis:
                try:
                    await redis.set(cache_key, response.model_dump_json(), ex=PLAN_DETAIL_TTL_SECONDS)
                except Exception as exc:
                    PLANS_CACHE_ERRORS_TOTAL.inc()
                    logger.warning(
                        "plans_cache_set_failed",
                        key=cache_key,
                        error=str(exc),
                    )
            return response
        except Exception as e:
            logger.exception("calendar_plan_get_failed", plan_id=plan_id, user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get plan: {str(e)}",
            )

    async def get_all_plans(db: AsyncSession, user_id: str, roots_only: bool = True) -> list[CalendarPlanResponse]:
        cache_key = plans_list_key(user_id, roots_only)
        redis = await get_redis()
        if redis:
            try:
                cached_value = await redis.get(cache_key)
                if cached_value:
                    PLANS_CACHE_HITS_TOTAL.inc()
                    raw_items = json.loads(cached_value)
                    return [CalendarPlanResponse.model_validate(item) for item in raw_items]
                PLANS_CACHE_MISSES_TOTAL.inc()
            except Exception as exc:
                PLANS_CACHE_ERRORS_TOTAL.inc()
                logger.warning(
                    "plans_cache_get_failed",
                    key=cache_key,
                    error=str(exc),
                )

        try:
            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets)
                )
                .where(CalendarPlan.user_id == user_id)
            )
            if roots_only:
                stmt = stmt.where(CalendarPlan.id == CalendarPlan.root_plan_id)
            result = await db.execute(stmt)
            plans = result.scalars().unique().all()

            responses: list[CalendarPlanResponse] = []
            for plan in plans:
                try:
                    responses.append(CalendarPlanService._get_plan_response(plan))
                except Exception:
                    logger.exception("calendar_plan_response_build_failed", plan_id=plan.id)

            if redis:
                try:
                    payload = json.dumps([plan.model_dump(mode="json") for plan in responses])
                    await redis.set(cache_key, payload, ex=PLAN_LIST_TTL_SECONDS)
                except Exception as exc:
                    PLANS_CACHE_ERRORS_TOTAL.inc()
                    logger.warning(
                        "plans_cache_set_failed",
                        key=cache_key,
                        error=str(exc),
                    )
            return responses
        except Exception as e:
            logger.exception("calendar_plan_list_failed", user_id=user_id, roots_only=roots_only)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch plans: {str(e)}",
            )

    async def get_favorite_plans(db: AsyncSession, user_id: str) -> list[CalendarPlanResponse]:
        cache_key = favorite_plans_key(user_id)
        redis = await get_redis()
        if redis:
            try:
                cached_value = await redis.get(cache_key)
                if cached_value:
                    PLANS_CACHE_HITS_TOTAL.inc()
                    raw_items = json.loads(cached_value)
                    return [CalendarPlanResponse.model_validate(item) for item in raw_items]
                PLANS_CACHE_MISSES_TOTAL.inc()
            except Exception as exc:
                PLANS_CACHE_ERRORS_TOTAL.inc()
                logger.warning(
                    "plans_cache_get_failed",
                    key=cache_key,
                    error=str(exc),
                )

        try:
            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets)
                )
                .where(CalendarPlan.user_id == user_id, CalendarPlan.is_active.is_(True))
            )
            result = await db.execute(stmt)
            plans = result.scalars().unique().all()

            responses = [CalendarPlanService._get_plan_response(plan) for plan in plans]

            if redis:
                try:
                    payload = json.dumps([plan.model_dump(mode="json") for plan in responses])
                    await redis.set(cache_key, payload, ex=FAVORITE_PLANS_TTL_SECONDS)
                except Exception as exc:
                    PLANS_CACHE_ERRORS_TOTAL.inc()
                    logger.warning(
                        "plans_cache_set_failed",
                        key=cache_key,
                        error=str(exc),
                    )

            return responses
        except Exception as e:
            logger.exception("calendar_plan_favorites_failed", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch favorite plans: {str(e)}",
            )

    async def generate_workouts(db: AsyncSession, plan_id: int, user_id: str) -> list[dict[str, Any]]:
        try:
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
            result = await db.execute(stmt)
            plan = result.scalars().first()

            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Plan not found or permission denied",
                )

            if plan.root_plan_id == plan.id and plan.variants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the original plan while variants exist. Delete variants first.",
                )

            workouts: list[dict[str, Any]] = []
            for mesocycle in plan.mesocycles or []:
                for microcycle in mesocycle.microcycles or []:
                    for plan_workout in microcycle.plan_workouts or []:
                        workout_payload: dict[str, Any] = {
                            "mesocycle": {
                                "id": mesocycle.id,
                                "name": mesocycle.name,
                                "order_index": mesocycle.order_index,
                            },
                            "microcycle": {
                                "id": microcycle.id,
                                "name": microcycle.name,
                                "order_index": microcycle.order_index,
                                "days_count": microcycle.days_count,
                            },
                            "workout": {
                                "id": plan_workout.id,
                                "day_label": plan_workout.day_label,
                                "order_index": plan_workout.order_index,
                                "exercises": [],
                            },
                        }

                        for exercise in plan_workout.exercises or []:
                            exercise_payload: dict[str, Any] = {
                                "id": exercise.id,
                                "exercise_definition_id": exercise.exercise_definition_id,
                                "exercise_name": exercise.exercise_name,
                                "order_index": exercise.order_index,
                                "sets": [],
                            }

                            for plan_set in exercise.sets or []:
                                exercise_payload["sets"].append(
                                    {
                                        "id": plan_set.id,
                                        "order_index": plan_set.order_index,
                                        "intensity": plan_set.intensity,
                                        "effort": plan_set.effort,
                                        "volume": plan_set.volume,
                                    }
                                )

                            workout_payload["workout"]["exercises"].append(exercise_payload)

                        workouts.append(workout_payload)

            if workouts:
                PLAN_WORKOUTS_GENERATED_TOTAL.inc(len(workouts))
            return workouts
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("calendar_plan_generate_workouts_failed", plan_id=plan_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate workouts: {str(e)}",
            )

    @staticmethod
    def _matches_numeric_filters(
        value: float | None,
        lt: float | None = None,
        lte: float | None = None,
        gt: float | None = None,
        gte: float | None = None,
    ) -> bool:
        if lt is not None and not (value is not None and value < lt):
            return False
        if lte is not None and not (value is not None and value <= lte):
            return False
        if gt is not None and not (value is not None and value > gt):
            return False
        if gte is not None and not (value is not None and value >= gte):
            return False
        return True

    async def apply_mass_edit(
        db: AsyncSession,
        plan_id: int,
        user_id: str,
        cmd: PlanMassEditCommand,
    ) -> CalendarPlanResponse:
        try:
            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets)
                )
                .where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
            )
            result = await db.execute(stmt)
            plan = result.scalars().first()

            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Plan not found or permission denied",
                )

            is_apply_mode = cmd.mode == "apply"
            changed = False

            for meso_idx, mesocycle in enumerate(plan.mesocycles or []):
                if cmd.filter.mesocycle_indices is not None and meso_idx not in cmd.filter.mesocycle_indices:
                    continue

                for micro_idx, microcycle in enumerate(mesocycle.microcycles or []):
                    if cmd.filter.microcycle_indices is not None and micro_idx not in cmd.filter.microcycle_indices:
                        continue

                    for workout in microcycle.plan_workouts or []:
                        if (
                            cmd.filter.workout_day_labels is not None
                            and workout.day_label not in cmd.filter.workout_day_labels
                        ):
                            continue

                        for exercise in workout.exercises or []:
                            name = exercise.exercise_name or ""
                            if cmd.filter.exercise_name_exact is not None and name != cmd.filter.exercise_name_exact:
                                continue
                            if (
                                cmd.filter.exercise_name_contains is not None
                                and cmd.filter.exercise_name_contains.lower() not in name.lower()
                            ):
                                continue

                            target_sets = []
                            for plan_set in exercise.sets or []:
                                intensity = plan_set.intensity
                                volume = plan_set.volume

                                if not CalendarPlanService._matches_numeric_filters(
                                    intensity,
                                    lt=cmd.filter.intensity_lt,
                                    lte=cmd.filter.intensity_lte,
                                    gt=cmd.filter.intensity_gt,
                                    gte=cmd.filter.intensity_gte,
                                ):
                                    continue

                                if not CalendarPlanService._matches_numeric_filters(
                                    volume,
                                    lt=cmd.filter.volume_lt,
                                    gt=cmd.filter.volume_gt,
                                ):
                                    continue

                                target_sets.append(plan_set)

                            if not target_sets and any(
                                [
                                    cmd.filter.intensity_lt,
                                    cmd.filter.intensity_lte,
                                    cmd.filter.intensity_gt,
                                    cmd.filter.intensity_gte,
                                    cmd.filter.volume_lt,
                                    cmd.filter.volume_gt,
                                ]
                            ):
                                continue

                            if not is_apply_mode:
                                continue

                            if cmd.actions.replace_exercise_definition_id_to is not None:
                                exercise.exercise_definition_id = cmd.actions.replace_exercise_definition_id_to
                                changed = True

                            if cmd.actions.replace_exercise_name_to is not None:
                                exercise.exercise_name = cmd.actions.replace_exercise_name_to
                                changed = True

                            target_iter = target_sets if target_sets else (exercise.sets or [])
                            for plan_set in target_iter:
                                if cmd.actions.set_intensity is not None:
                                    plan_set.intensity = cmd.actions.set_intensity
                                    changed = True
                                if cmd.actions.increase_intensity_by is not None:
                                    base = plan_set.intensity or 0
                                    plan_set.intensity = base + cmd.actions.increase_intensity_by
                                    changed = True
                                if cmd.actions.decrease_intensity_by is not None:
                                    base = plan_set.intensity or 0
                                    plan_set.intensity = base - cmd.actions.decrease_intensity_by
                                    changed = True

                                if cmd.actions.set_volume is not None:
                                    plan_set.volume = cmd.actions.set_volume
                                    changed = True
                                if cmd.actions.increase_volume_by is not None:
                                    base = plan_set.volume or 0
                                    plan_set.volume = base + cmd.actions.increase_volume_by
                                    changed = True
                                if cmd.actions.decrease_volume_by is not None:
                                    base = plan_set.volume or 0
                                    plan_set.volume = base - cmd.actions.decrease_volume_by
                                    changed = True

            if is_apply_mode and changed:
                await db.commit()
                await db.refresh(plan)
                PLAN_MASS_EDITS_APPLIED_TOTAL.inc()
                await invalidate_plans_cache(user_id, plan_ids=[plan_id])

            return CalendarPlanService._get_plan_response(plan)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("calendar_plan_mass_edit_failed", plan_id=plan_id, user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to apply mass edit: {str(e)}",
            )

    async def update_plan(
        db: AsyncSession, plan_id: int, plan_data: CalendarPlanUpdate, user_id: str
    ) -> CalendarPlanResponse:
        stmt = select(CalendarPlan).where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
        result = await db.execute(stmt)
        plan = result.scalars().first()
        if not plan:
            raise ValueError("Plan not found or permission denied")
        for field, value in plan_data.model_dump(exclude_none=True).items():
            setattr(plan, field, value)

        await db.commit()
        await db.refresh(plan)
        await invalidate_plans_cache(user_id, plan_ids=[plan_id])
        return CalendarPlanService._get_plan_response(plan)

    async def delete_plan(db: AsyncSession, plan_id: int, user_id: str) -> None:
        try:
            stmt = (
                select(CalendarPlan)
                .options(
                    selectinload(CalendarPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.plan_workouts)
                    .selectinload(PlanWorkout.exercises)
                    .selectinload(PlanExercise.sets),
                    selectinload(CalendarPlan.applied_instances).selectinload(AppliedCalendarPlan.workouts),
                    selectinload(CalendarPlan.applied_instances)
                    .selectinload(AppliedCalendarPlan.mesocycles)
                    .selectinload(AppliedMesocycle.microcycles)
                    .selectinload(AppliedMicrocycle.workouts),
                    selectinload(CalendarPlan.variants),
                )
                .where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
            )
            result = await db.execute(stmt)
            plan = result.scalars().first()

            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Plan not found or permission denied",
                )

            if plan.root_plan_id == plan.id and plan.variants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the original plan while variants exist. Delete variants first.",
                )

            for mesocycle in plan.mesocycles:
                for micro_cycle in mesocycle.microcycles:
                    for workout in micro_cycle.plan_workouts:
                        for exercise in workout.exercises:
                            for plan_set in exercise.sets:
                                await db.delete(plan_set)
                            await db.delete(exercise)
                        await db.delete(workout)
                    await db.delete(micro_cycle)
                await db.delete(mesocycle)

            for applied_plan in plan.applied_instances:
                for workout in applied_plan.workouts:
                    await db.delete(workout)
                for applied_meso in applied_plan.mesocycles:
                    for applied_micro in applied_meso.microcycles:
                        for applied_workout in applied_micro.workouts:
                            await db.delete(applied_workout)
                        await db.delete(applied_micro)
                    await db.delete(applied_meso)
                await db.delete(applied_plan)

            await db.delete(plan)
            await db.commit()
            await invalidate_plans_cache(user_id, plan_ids=[plan_id])
        except HTTPException as e:
            await db.rollback()
            raise e
        except Exception as e:
            await db.rollback()
            logger.exception("calendar_plan_delete_failed", plan_id=plan_id, user_id=user_id)
            if isinstance(e, CircularDependencyError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cannot delete calendar plan due to circular dependency in related objects. "
                        "Delete dependent variants or applied instances first."
                    ),
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete plan: {str(e)}",
            )

    @staticmethod
    async def _get_exercise_details(exercise_definition_id: int) -> dict:
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://exercises-service:8002/exercises/definitions/{exercise_definition_id}",
                    timeout=5.0,
                )
            if response.status_code == 200:
                exercise = response.json()
                return {"id": exercise["id"], "name": exercise["name"]}
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Exercise with id {exercise_definition_id} not found",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error fetching exercise details",
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Exercises service unavailable",
            )

    async def get_flattened_workouts(db: AsyncSession, plan_id: int, user_id: str) -> list[dict[str, Any]]:
        plan = await CalendarPlanService.get_plan(db, plan_id, user_id)
        if not plan:
            return []

        flattened_workouts = []
        current_global_index = 0

        mesocycles = sorted(
            plan.mesocycles or [], key=lambda m: (m.order_index if m.order_index is not None else 0, m.id)
        )

        for meso in mesocycles:
            meso_name = meso.name or "Unnamed Meso"
            microcycles = sorted(
                meso.microcycles or [], key=lambda mc: (mc.order_index if mc.order_index is not None else 0, mc.id)
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
                                }
                            )
                        exercises_data.append(
                            {
                                "exercise_definition_id": ex.exercise_definition_id,
                                "sets": sets_data,
                                "notes": None,
                            }
                        )

                    flattened_workouts.append(
                        {
                            "plan_workout_id": pw.id,
                            "name": f"{pw.day_label}",
                            "day_label": pw.day_label,
                            "order_index": pw.order_index,
                            "meso_name": meso_name,
                            "micro_name": micro_name,
                            "micro_id": micro.id,
                            "micro_days_count": getattr(micro, "days_count", 0),
                            "meso_id": meso.id,
                            "exercises": exercises_data,
                            "global_index": current_global_index,
                        }
                    )
                    current_global_index += 1

        return flattened_workouts

    @staticmethod
    def _get_plan_response(plan: CalendarPlan) -> CalendarPlanResponse:
        try:
            mesocycles_list = []
            for mesocycle in plan.mesocycles:
                microcycles = []
                for microcycle in mesocycle.microcycles:
                    microcycles.append(
                        {
                            "id": microcycle.id,
                            "mesocycle_id": mesocycle.id,
                            "name": microcycle.name,
                            "notes": microcycle.notes,
                            "order_index": microcycle.order_index,
                            "normalization_value": microcycle.normalization_value,
                            "normalization_unit": microcycle.normalization_unit,
                            "normalization_rules": microcycle.normalization_rules,
                            "days_count": microcycle.days_count,
                            "plan_workouts": [
                                {
                                    "id": pw.id,
                                    "microcycle_id": microcycle.id,
                                    "day_label": pw.day_label,
                                    "order_index": pw.order_index,
                                    "exercises": [
                                        {
                                            "id": pe.id,
                                            "exercise_definition_id": pe.exercise_definition_id,
                                            "exercise_name": pe.exercise_name,
                                            "order_index": pe.order_index,
                                            "plan_workout_id": pe.plan_workout_id,
                                            "sets": [
                                                {
                                                    "id": ps.id,
                                                    "order_index": ps.order_index,
                                                    "intensity": ps.intensity,
                                                    "effort": ps.effort,
                                                    "volume": ps.volume,
                                                    "plan_exercise_id": ps.plan_exercise_id,
                                                }
                                                for ps in pe.sets
                                            ],
                                        }
                                        for pe in pw.exercises
                                    ],
                                }
                                for pw in microcycle.plan_workouts
                            ],
                        }
                    )
                mesocycles_list.append(
                    {
                        "id": mesocycle.id,
                        "name": mesocycle.name,
                        "order_index": mesocycle.order_index,
                        "microcycles": microcycles,
                    }
                )
            response_data = {
                "id": getattr(plan, "id", 0),
                "name": getattr(plan, "name", ""),
                "duration_weeks": getattr(plan, "duration_weeks", 0),
                "is_active": getattr(plan, "is_active", True),
                "root_plan_id": getattr(plan, "root_plan_id", getattr(plan, "id", 0)),
                "is_original": getattr(plan, "id", None) == getattr(plan, "root_plan_id", None),
                "primary_goal": getattr(plan, "primary_goal", None),
                "intended_experience_level": getattr(plan, "intended_experience_level", None),
                "intended_frequency_per_week": getattr(plan, "intended_frequency_per_week", None),
                "session_duration_target_min": getattr(plan, "session_duration_target_min", None),
                "primary_focus_lifts": getattr(plan, "primary_focus_lifts", None),
                "required_equipment": getattr(plan, "required_equipment", None),
                "mesocycles": mesocycles_list,
            }

            return CalendarPlanResponse.model_validate(response_data)
        except Exception:
            mesocycles_list = []
            for meso in plan.mesocycles:
                microcycles_list = []
                for micro in meso.microcycles:
                    microcycles_list.append(
                        {
                            "id": micro.id,
                            "name": getattr(micro, "name", ""),
                            "order_index": getattr(micro, "order_index", 0),
                            "normalization_value": getattr(micro, "normalization_value", None),
                            "normalization_unit": getattr(micro, "normalization_unit", None),
                            "normalization_rules": getattr(micro, "normalization_rules", None),
                            "days_count": getattr(micro, "days_count", 0),
                        }
                    )
                mesocycles_list.append(
                    {
                        "id": meso.id,
                        "name": getattr(meso, "name", ""),
                        "order_index": getattr(meso, "order_index", 0),
                        "weeks_count": getattr(meso, "weeks_count", 0),
                        "microcycle_length_days": getattr(meso, "microcycle_length_days", 0),
                        "microcycles": microcycles_list,
                    }
                )

            return CalendarPlanResponse(
                id=getattr(plan, "id", 0),
                name=getattr(plan, "name", ""),
                duration_weeks=getattr(plan, "duration_weeks", 0),
                is_active=getattr(plan, "is_active", True),
                root_plan_id=getattr(plan, "root_plan_id", getattr(plan, "id", 0)),
                is_original=getattr(plan, "id", None) == getattr(plan, "root_plan_id", None),
                primary_goal=getattr(plan, "primary_goal", None),
                intended_experience_level=getattr(plan, "intended_experience_level", None),
                intended_frequency_per_week=getattr(plan, "intended_frequency_per_week", None),
                session_duration_target_min=getattr(plan, "session_duration_target_min", None),
                primary_focus_lifts=getattr(plan, "primary_focus_lifts", None),
                required_equipment=getattr(plan, "required_equipment", None),
                mesocycles=mesocycles_list,
            )
