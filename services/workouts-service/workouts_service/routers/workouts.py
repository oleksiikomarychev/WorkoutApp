from datetime import datetime
from typing import List, Optional

import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas
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

PLANS_SERVICE_URL = "http://plans-service:8005"  # URL plans-service в docker-сети

logger = structlog.get_logger(__name__)


def get_workout_service(
    db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> WorkoutService:
    plans_rpc = PlansServiceRPC(base_url=PLANS_SERVICE_URL)
    exercises_rpc = get_exercise_by_id
    return WorkoutService(db, plans_rpc, exercises_rpc, user_id)


router = APIRouter(prefix="")


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


@router.get("/", response_model=List[schemas.workout.WorkoutListResponse])
async def list_workouts(
    skip: int = 0,
    limit: int = 100,
    type: Optional[str] = None,
    status: Optional[str] = None,
    applied_plan_id: Optional[int] = Query(None, alias="applied_plan_id"),
    workout_service: WorkoutService = Depends(get_workout_service),
):
    return await workout_service.list_workouts(skip, limit, type=type, status=status, applied_plan_id=applied_plan_id)


@router.get("/generated", response_model=List[schemas.workout.WorkoutListResponse])
async def list_generated_workouts(
    skip: int = 0, limit: int = 100, workout_service: WorkoutService = Depends(get_workout_service)
):
    """List all generated workouts"""
    return await workout_service.list_workouts(skip, limit, type="generated")


@router.get("/{workout_id}", response_model=schemas.workout.WorkoutResponse)
async def get_workout(workout_id: int, workout_service: WorkoutService = Depends(get_workout_service)):
    return await workout_service.get_workout(workout_id)


@router.get("/{workout_id}/next", response_model=schemas.workout.WorkoutResponse)
async def get_next_workout_in_plan(workout_id: int, workout_service: WorkoutService = Depends(get_workout_service)):
    """
    Get the next workout in the same plan after the given workout.
    """
    return await workout_service.get_next_workout_in_plan(workout_id)


@router.put("/{workout_id}", response_model=schemas.workout.WorkoutResponse)
async def update_workout(
    workout_id: int,
    payload: schemas.workout.WorkoutUpdate,
    workout_service: WorkoutService = Depends(get_workout_service),
):
    item = await workout_service.update_workout(workout_id, payload)
    # Convert ORM object to Pydantic model for proper serialization
    return schemas.workout.WorkoutResponse.model_validate(item)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(workout_id: int, workout_service: WorkoutService = Depends(get_workout_service)):
    await workout_service.delete_workout(workout_id)
    return None


@router.post("/batch", response_model=List[schemas.workout.WorkoutListResponse])
async def create_workouts_batch(
    workouts_data: List[schemas.workout.WorkoutCreate],
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
    """
    Fetches the first generated workout (with smallest id)
    """
    return await workout_service.get_first_generated_workout()


@router.get("/debug/microcycle/{microcycle_id}")
async def debug_microcycle(microcycle_id: int, workout_service: WorkoutService = Depends(get_workout_service)):
    """Debug endpoint to check if any workouts exist for a microcycle"""
    workouts = await workout_service.get_workouts_by_microcycle_ids([microcycle_id])
    return {
        "microcycle_id": microcycle_id,
        "workouts_found": len(workouts) > 0,
        "workout_count": len(workouts),
    }


@router.post("/by-microcycles", response_model=List[schemas.workout.WorkoutListResponse])
async def get_workouts_by_microcycles(
    microcycle_ids: List[int] = Body(..., embed=True),
    workout_service: WorkoutService = Depends(get_workout_service),
):
    """
    Fetches workouts associated with the given microcycle IDs.
    """
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


@router.get("/applied-plans/{applied_plan_id}/details", response_model=List[schemas.workout.WorkoutPlanDetailItem])
async def get_plan_details_with_exercises(
    applied_plan_id: int,
    workout_service: WorkoutService = Depends(get_workout_service),
):
    """
    Fetch all workouts for a plan with exercise IDs included.
    Designed for plan analysis tools.
    """
    return await workout_service.get_plan_details_with_exercises(applied_plan_id)


@router.post("/schedule/shift-in-plan")
async def shift_schedule_in_plan(
    applied_plan_id: int = Body(...),
    from_order_index: int = Body(...),
    delta_days: int = Body(...),
    delta_index: int = Body(...),
    exclude_ids: Optional[List[int]] = Body(default=None),
    only_future: bool = Body(default=True),
    baseline_date: Optional[str] = Body(default=None),
    workout_service: WorkoutService = Depends(get_workout_service),
    user_id: str = Depends(get_current_user_id),
):
    """Batch shift scheduled_for and plan_order_index for workouts in a plan."""
    try:
        parsed_baseline = None
        if baseline_date:
            try:
                parsed_baseline = datetime.fromisoformat(baseline_date)
            except Exception:
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
    exclude_ids: Optional[List[int]] = Body(default=None),
    only_future: bool = Body(default=True),
    baseline_date: Optional[str] = Body(default=None),
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
        signature = shift_schedule_in_plan_task.s(
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_order_index=from_order_index,
            delta_days=delta_days,
            delta_index=delta_index,
            exclude_ids=exclude_ids,
            only_future=only_future,
            baseline_date=baseline_date,
        )
        async_result = signature.apply_async()
        logger.info(
            "workout_schedule_shift_async_enqueued",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            task_id=async_result.id,
        )
        return schemas.TaskSubmissionResponse(task_id=async_result.id, status=async_result.status)
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
    result = AsyncResult(task_id, app=celery_app)
    response = schemas.TaskStatusResponse(task_id=task_id, status=result.status)
    if result.failed():
        response.error = str(result.result)
    elif result.successful():
        response.result = result.result
    response.meta = result.info if isinstance(result.info, dict) else None
    return response


@router.post("/applied-plans/{applied_plan_id}/mass-edit-sets", response_model=schemas.AppliedPlanMassEditResult)
async def applied_plan_mass_edit_sets(
    applied_plan_id: int,
    command: schemas.AppliedPlanMassEditCommand,
    workout_service: WorkoutService = Depends(get_workout_service),
    user_id: str = Depends(get_current_user_id),
):
    """Apply mass edit actions to exercise instances/sets for an applied plan.

    This endpoint operates on generated workouts linked to the given applied_plan_id
    and updates sets stored in exercises-service via its public API.
    """
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
        signature = applied_plan_mass_edit_sets_task.s(
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            command=command.model_dump(),
        )
        async_result = signature.apply_async()
        logger.info(
            "applied_plan_mass_edit_async_enqueued",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            task_id=async_result.id,
        )
        return schemas.TaskSubmissionResponse(task_id=async_result.id, status=async_result.status)
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
    """Shift scheduled_for dates for workouts in an applied plan starting from a given date.

    This endpoint is primarily used by the mobile client and the assistant to
    implement operations like "shift all not-yet-completed workouts starting
    from this week by +1 day" for the current applied plan.
    """

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
    """Enqueue applied-plan schedule shift as a Celery task and return task id/status."""

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
        signature = applied_plan_schedule_shift_task.s(
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_date=command.from_date.isoformat(),
            days=command.days,
            only_future=command.only_future,
            status_in=command.status_in,
        )
        async_result = signature.apply_async()
        logger.info(
            "applied_plan_schedule_shift_async_enqueued",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            task_id=async_result.id,
        )
        return schemas.TaskSubmissionResponse(task_id=async_result.id, status=async_result.status)
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
