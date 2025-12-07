import os
from datetime import datetime

import structlog
from backend_common.celery_utils import build_task_status_response, enqueue_task
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..celery_app import celery_app
from ..database import get_db
from ..dependencies import get_current_user_id
from ..services.rpc_client import PlansServiceRPC, get_exercise_by_id
from ..services.workout_service import WorkoutService
from ..tasks.workout_tasks import (
    applied_plan_mass_edit_sets_task,
    applied_plan_schedule_shift_task,
    shift_schedule_in_plan_task,
)

PLANS_SERVICE_URL = "http://plans-service:8005"

logger = structlog.get_logger(__name__)


def get_workout_service(
    db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> WorkoutService:
    plans_rpc = PlansServiceRPC(base_url=PLANS_SERVICE_URL)
    exercises_rpc = get_exercise_by_id
    return WorkoutService(db, plans_rpc, exercises_rpc, user_id)


router = APIRouter(prefix="")


DEBUG = (os.getenv("DEBUG") or "").strip().lower() in {"1", "true", "yes"}


@router.post("/", response_model=schemas.workout.WorkoutResponse, status_code=status.HTTP_201_CREATED)
async def create_workout(
    payload: schemas.workout.WorkoutCreate,
    workout_service: WorkoutService = Depends(get_workout_service),
    user_id: str = Depends(get_current_user_id),
):
    try:
        logger.info(
            "workout_create_requested",
            user_id=user_id,
            name=getattr(payload, "name", None),
            applied_plan_id=getattr(payload, "applied_plan_id", None),
            microcycle_id=getattr(payload, "microcycle_id", None),
        )
        logger.debug(
            "workout_create_payload",
            user_id=user_id,
            payload=payload.model_dump(),
        )
        item = await workout_service.create_workout(payload)
        logger.info(
            "workout_create_success",
            user_id=user_id,
            workout_id=getattr(item, "id", None),
        )
        return schemas.workout.WorkoutResponse.model_validate(item)
    except Exception as e:
        logger.exception(
            "workout_create_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workout: {str(e)}",
        )


@router.get("/", response_model=list[schemas.workout.WorkoutListResponse])
async def list_workouts(
    skip: int = 0,
    limit: int = 100,
    type: str | None = None,
    status: str | None = None,
    applied_plan_id: int | None = Query(None, alias="applied_plan_id"),
    workout_service: WorkoutService = Depends(get_workout_service),
):
    return await workout_service.list_workouts(skip, limit, type=type, status=status, applied_plan_id=applied_plan_id)


@router.get("/generated", response_model=list[schemas.workout.WorkoutListResponse])
async def list_generated_workouts(
    skip: int = 0, limit: int = 100, workout_service: WorkoutService = Depends(get_workout_service)
):
    return await workout_service.list_workouts(skip, limit, type="generated")


@router.get("/{workout_id}", response_model=schemas.workout.WorkoutResponse)
async def get_workout(workout_id: int, workout_service: WorkoutService = Depends(get_workout_service)):
    return await workout_service.get_workout(workout_id)


@router.get("/{workout_id}/next", response_model=schemas.workout.WorkoutResponse)
async def get_next_workout_in_plan(workout_id: int, workout_service: WorkoutService = Depends(get_workout_service)):
    return await workout_service.get_next_workout_in_plan(workout_id)


@router.put("/{workout_id}", response_model=schemas.workout.WorkoutResponse)
async def update_workout(
    workout_id: int,
    payload: schemas.workout.WorkoutUpdate,
    workout_service: WorkoutService = Depends(get_workout_service),
):
    item = await workout_service.update_workout(workout_id, payload)

    return schemas.workout.WorkoutResponse.model_validate(item)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(workout_id: int, workout_service: WorkoutService = Depends(get_workout_service)):
    await workout_service.delete_workout(workout_id)
    return None


@router.post("/batch", response_model=list[schemas.workout.WorkoutListResponse])
async def create_workouts_batch(
    workouts_data: list[schemas.workout.WorkoutCreate],
    workout_service: WorkoutService = Depends(get_workout_service),
    user_id: str = Depends(get_current_user_id),
):
    try:
        logger.info(
            "workout_batch_create_requested",
            user_id=user_id,
            count=len(workouts_data),
        )
        created_workouts = await workout_service.create_workouts_batch(workouts_data)
        logger.info(
            "workout_batch_create_success",
            user_id=user_id,
            count=len(created_workouts),
        )
        return [schemas.workout.WorkoutListResponse.model_validate(w) for w in created_workouts]
    except Exception as e:
        logger.exception(
            "workout_batch_create_error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to create workouts: {str(e)}")


@router.get("/generated/next", response_model=schemas.workout.WorkoutResponse)
async def get_next_generated_workout(request: Request, workout_service: WorkoutService = Depends(get_workout_service)):
    try:
        logger.debug(
            "next_generated_workout_request",
            headers=dict(request.headers),
            query_params=dict(request.query_params),
        )
        return await workout_service.get_next_generated_workout()
    except Exception as e:
        logger.exception(
            "next_generated_workout_error",
            error=str(e),
        )
        raise


@router.get("/generated/first", response_model=schemas.workout.WorkoutResponse)
async def get_first_generated_workout(
    workout_service: WorkoutService = Depends(get_workout_service),
):
    return await workout_service.get_first_generated_workout()


@router.get("/debug/microcycle/{microcycle_id}")
async def debug_microcycle(microcycle_id: int, workout_service: WorkoutService = Depends(get_workout_service)):
    workouts = await workout_service.get_workouts_by_microcycle_ids([microcycle_id])
    return {
        "microcycle_id": microcycle_id,
        "workout_count": len(workouts),
        "workouts_found": len(workouts) > 0,
    }


@router.post("/debug/cleanup-user")
async def debug_cleanup_user(
    user_id: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    if not DEBUG:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug cleanup endpoint disabled")

    deleted_sessions = 0
    deleted_workouts = 0

    result_sessions = await db.execute(select(models.WorkoutSession).where(models.WorkoutSession.user_id == user_id))
    sessions = list(result_sessions.scalars().all())
    for s in sessions:
        await db.delete(s)
        deleted_sessions += 1

    result_workouts = await db.execute(select(models.Workout).where(models.Workout.user_id == user_id))
    workouts = list(result_workouts.scalars().all())
    for w in workouts:
        await db.delete(w)
        deleted_workouts += 1

    await db.commit()

    return {
        "user_id": user_id,
        "deleted_sessions": deleted_sessions,
        "deleted_workouts": deleted_workouts,
    }


@router.post("/by-microcycles", response_model=list[schemas.workout.WorkoutListResponse])
async def get_workouts_by_microcycles(
    microcycle_ids: list[int] = Body(..., embed=True),
    workout_service: WorkoutService = Depends(get_workout_service),
):
    try:
        logger.debug(
            "workouts_by_microcycles_requested",
            microcycle_ids=microcycle_ids,
        )
        workouts = await workout_service.get_workouts_by_microcycle_ids(microcycle_ids)
        logger.debug(
            "workouts_by_microcycles_found",
            microcycle_ids=microcycle_ids,
            count=len(workouts),
        )
        return [schemas.workout.WorkoutListResponse.model_validate(w) for w in workouts]
    except Exception as e:
        logger.exception(
            "workouts_by_microcycles_error",
            microcycle_ids=microcycle_ids,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/applied-plans/{applied_plan_id}/details", response_model=list[schemas.workout.WorkoutPlanDetailItem])
async def get_plan_details_with_exercises(
    applied_plan_id: int,
    workout_service: WorkoutService = Depends(get_workout_service),
):
    return await workout_service.get_plan_details_with_exercises(applied_plan_id)


@router.post("/schedule/shift-in-plan")
async def shift_schedule_in_plan(
    applied_plan_id: int = Body(...),
    from_order_index: int = Body(...),
    delta_days: int = Body(...),
    delta_index: int = Body(...),
    exclude_ids: list[int] | None = Body(default=None),
    only_future: bool = Body(default=True),
    baseline_date: str | None = Body(default=None),
    workout_service: WorkoutService = Depends(get_workout_service),
    user_id: str = Depends(get_current_user_id),
):
    try:
        parsed_baseline = None
        if baseline_date:
            try:
                parsed_baseline = datetime.fromisoformat(baseline_date)
            except ValueError:
                parsed_baseline = None
        summary = await workout_service.shift_schedule_in_plan(
            applied_plan_id=applied_plan_id,
            from_order_index=from_order_index,
            delta_days=delta_days,
            delta_index=delta_index,
            exclude_ids=exclude_ids or [],
            only_future=only_future,
            baseline_date=parsed_baseline,
        )
        logger.info(
            "workout_schedule_shifted_in_plan",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_order_index=from_order_index,
            delta_days=delta_days,
            delta_index=delta_index,
            exclude_ids=exclude_ids or [],
            only_future=only_future,
        )
        return summary
    except Exception as e:
        logger.exception(
            "workout_schedule_shift_error",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to shift schedule: {str(e)}",
        )


@router.post("/schedule/shift-in-plan-async", response_model=schemas.TaskSubmissionResponse)
async def shift_schedule_in_plan_async(
    applied_plan_id: int = Body(...),
    from_order_index: int = Body(...),
    delta_days: int = Body(...),
    delta_index: int = Body(...),
    exclude_ids: list[int] | None = Body(default=None),
    only_future: bool = Body(default=True),
    baseline_date: str | None = Body(default=None),
    user_id: str = Depends(get_current_user_id),
):
    try:
        logger.info(
            "workout_schedule_shift_async_requested",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_order_index=from_order_index,
            delta_days=delta_days,
            delta_index=delta_index,
            exclude_ids=exclude_ids or [],
            only_future=only_future,
            baseline_date=baseline_date,
        )
        payload = enqueue_task(
            shift_schedule_in_plan_task,
            logger=logger,
            log_event="workout_schedule_shift_async_enqueued",
            task_kwargs={
                "user_id": user_id,
                "applied_plan_id": applied_plan_id,
                "from_order_index": from_order_index,
                "delta_days": delta_days,
                "delta_index": delta_index,
                "exclude_ids": exclude_ids,
                "only_future": only_future,
                "baseline_date": baseline_date,
            },
            log_extra={
                "user_id": user_id,
                "applied_plan_id": applied_plan_id,
            },
        )
        return schemas.TaskSubmissionResponse(**payload)
    except Exception as e:
        logger.exception(
            "workout_schedule_shift_async_error",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue shift schedule task: {str(e)}",
        )


@router.get("/schedule/tasks/{task_id}", response_model=schemas.TaskStatusResponse)
async def get_schedule_task_status(task_id: str):
    return build_task_status_response(
        task_id=task_id,
        celery_app=celery_app,
        response_model=schemas.TaskStatusResponse,
    )


@router.post("/applied-plans/{applied_plan_id}/mass-edit-sets", response_model=schemas.AppliedPlanMassEditResult)
async def applied_plan_mass_edit_sets(
    applied_plan_id: int,
    command: schemas.AppliedPlanMassEditCommand,
    workout_service: WorkoutService = Depends(get_workout_service),
    user_id: str = Depends(get_current_user_id),
):
    try:
        logger.info(
            "applied_plan_mass_edit_requested",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            mode=command.mode,
        )
        result = await workout_service.apply_applied_plan_mass_edit(applied_plan_id, command)
        logger.info(
            "applied_plan_mass_edit_completed",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            mode=result.mode,
            workouts_matched=result.workouts_matched,
            instances_matched=result.instances_matched,
            sets_matched=result.sets_matched,
            sets_modified=result.sets_modified,
        )
        return result
    except Exception as e:
        logger.exception(
            "applied_plan_mass_edit_error",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply mass edit: {str(e)}",
        )


@router.post("/applied-plans/{applied_plan_id}/mass-edit-sets-async", response_model=schemas.TaskSubmissionResponse)
async def applied_plan_mass_edit_sets_async(
    applied_plan_id: int,
    command: schemas.AppliedPlanMassEditCommand,
    user_id: str = Depends(get_current_user_id),
):
    try:
        logger.info(
            "applied_plan_mass_edit_async_requested",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            mode=command.mode,
        )
        payload = enqueue_task(
            applied_plan_mass_edit_sets_task,
            logger=logger,
            log_event="applied_plan_mass_edit_async_enqueued",
            task_kwargs={
                "user_id": user_id,
                "applied_plan_id": applied_plan_id,
                "command": command.model_dump(),
            },
            log_extra={
                "user_id": user_id,
                "applied_plan_id": applied_plan_id,
                "mode": command.mode,
            },
        )
        return schemas.TaskSubmissionResponse(**payload)
    except Exception as e:
        logger.exception(
            "applied_plan_mass_edit_async_error",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue applied plan mass edit task: {str(e)}",
        )


@router.post("/applied-plans/{applied_plan_id}/shift-schedule")
async def shift_applied_plan_schedule(
    applied_plan_id: int,
    command: schemas.AppliedPlanScheduleShiftCommand,
    workout_service: WorkoutService = Depends(get_workout_service),
    user_id: str = Depends(get_current_user_id),
):
    try:
        logger.info(
            "applied_plan_schedule_shift_requested",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_date=command.from_date.isoformat(),
            days=command.days,
            only_future=command.only_future,
            status_in=command.status_in,
        )
        result = await workout_service.shift_applied_plan_schedule_from_date(applied_plan_id, command)
        logger.info(
            "applied_plan_schedule_shift_completed",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            days=command.days,
            workouts_shifted=result.get("workouts_shifted", 0),
        )
        return result
    except Exception as e:
        logger.exception(
            "applied_plan_schedule_shift_error",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to shift applied plan schedule: {str(e)}",
        )


@router.post("/applied-plans/{applied_plan_id}/shift-schedule-async", response_model=schemas.TaskSubmissionResponse)
async def shift_applied_plan_schedule_async(
    applied_plan_id: int,
    command: schemas.AppliedPlanScheduleShiftCommand,
    user_id: str = Depends(get_current_user_id),
):
    try:
        logger.info(
            "applied_plan_schedule_shift_async_requested",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_date=command.from_date.isoformat(),
            days=command.days,
            only_future=command.only_future,
            status_in=command.status_in,
        )
        payload = enqueue_task(
            applied_plan_schedule_shift_task,
            logger=logger,
            log_event="applied_plan_schedule_shift_async_enqueued",
            task_kwargs={
                "user_id": user_id,
                "applied_plan_id": applied_plan_id,
                "from_date": command.from_date.isoformat(),
                "days": command.days,
                "only_future": command.only_future,
                "status_in": command.status_in,
            },
            log_extra={
                "user_id": user_id,
                "applied_plan_id": applied_plan_id,
                "days": command.days,
            },
        )
        return schemas.TaskSubmissionResponse(**payload)
    except Exception as e:
        logger.exception(
            "applied_plan_schedule_shift_async_error",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue applied plan schedule shift task: {str(e)}",
        )
