from typing import Any

import structlog
from backend_common.celery_utils import build_task_status_response, enqueue_task
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..dependencies import get_current_user_id, get_db
from ..schemas.calendar_plan import (
    AppliedCalendarPlanResponse,
    AppliedCalendarPlanSummaryResponse,
    ApplyPlanComputeSettings,
)
from ..schemas.task_responses import TaskStatusResponse, TaskSubmissionResponse
from ..services.applied_calendar_plan_service import AppliedCalendarPlanService
from ..services.macro_apply import MacroApplier
from ..services.macro_engine import MacroEngine
from ..tasks.apply_plan_tasks import apply_plan_macros_task, apply_plan_task

router = APIRouter(prefix="/applied-plans")

logger = structlog.get_logger(__name__)


def _submit_task(task_fn, *, user_id: str, **kwargs: Any) -> TaskSubmissionResponse:
    task_kwargs: dict[str, Any] = {"user_id": user_id}
    task_kwargs.update(kwargs)

    payload = enqueue_task(
        task_fn,
        logger=logger,
        log_event="plans_task_enqueued",
        task_kwargs=task_kwargs,
        log_extra={
            "user_id": user_id,
        },
    )
    return TaskSubmissionResponse(**payload)


@router.get("/active", response_model=AppliedCalendarPlanResponse | None)
async def get_active_plan(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    try:
        service = AppliedCalendarPlanService(db, user_id)
        plan = await service.get_active_plan()
        logger.info("fetched_active_plan", user_id=user_id, plan_id=plan.id if plan else None)
        return plan
    except Exception as e:
        logger.error("failed_to_fetch_active_plan", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch active plan: {str(e)}",
        )


@router.get("/{applied_plan_id}/analytics")
async def get_applied_plan_analytics(
    applied_plan_id: int,
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    group_by: str | None = Query(None, regex="^(order|date)$"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        service = AppliedCalendarPlanService(db, user_id)
        data = await service.get_plan_analytics(
            applied_plan_id,
            from_date=from_date,
            to_date=to_date,
            group_by=group_by,
        )
        return data
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch plan analytics: {exc}",
        )


@router.post("/{applied_plan_id}/apply-macros", response_model=dict[str, Any])
async def apply_plan_macros(
    applied_plan_id: int,
    index_offset: int = Query(0, description="Offset to apply to current_workout_index when evaluating macros"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = MacroEngine(db, user_id)
        preview = await engine.run_for_applied_plan(applied_plan_id, anchor="current", index_offset=index_offset)

        svc = AppliedCalendarPlanService(db, user_id)
        plan_changes_results: list[dict] = []
        for item in preview.get("preview") or []:
            for ch in item.get("plan_changes") or []:
                if ch.get("type") == "Inject_Mesocycle":
                    params = ch.get("params") or {}
                    mode = str((params.get("mode") or "").strip())
                    tpl_id = params.get("template_id")
                    src_id = params.get("source_mesocycle_id") or params.get("mesocycle_id")
                    placement = params.get("placement")
                    try:
                        res = await svc.inject_mesocycle_into_applied_plan(
                            applied_plan_id,
                            mode=mode,
                            template_id=tpl_id if tpl_id is not None else None,
                            source_mesocycle_id=src_id if src_id is not None else None,
                            placement=placement if isinstance(placement, dict) else None,
                        )
                    except Exception:
                        res = {"applied": False, "reason": "exception"}
                    plan_changes_results.append(res)

        applier = MacroApplier(user_id=user_id)
        patch_result = await applier.apply(preview)
        return {
            "preview": preview,
            "plan_changes": plan_changes_results,
            "apply_result": patch_result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply macros: {str(e)}",
        )


@router.post("/{applied_plan_id}/apply-macros-async", response_model=TaskSubmissionResponse)
async def apply_plan_macros_async(
    applied_plan_id: int,
    index_offset: int = Query(0, description="Offset to apply to current_workout_index when evaluating macros"),
    user_id: str = Depends(get_current_user_id),
):
    return _submit_task(
        apply_plan_macros_task,
        user_id=user_id,
        applied_plan_id=applied_plan_id,
        index_offset=index_offset,
    )


@router.get("/{applied_plan_id}/flattened-workouts", response_model=list[dict[str, Any]])
async def get_flattened_workouts(
    applied_plan_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        service = AppliedCalendarPlanService(db, user_id)
        workouts = await service.get_flattened_plan_workouts(applied_plan_id)
        return workouts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch flattened workouts: {str(e)}",
        )


@router.get("/{plan_id}", response_model=AppliedCalendarPlanResponse)
async def get_applied_plan_details(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)
):
    try:
        service = AppliedCalendarPlanService(db, user_id)
        plan = await service.get_applied_plan_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Applied plan not found")
        return plan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch applied plan details: {str(e)}",
        )


@router.get("/user", response_model=list[AppliedCalendarPlanSummaryResponse])
async def get_user_applied_plans(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        service = AppliedCalendarPlanService(db, user_id)
        return await service.get_user_applied_plans()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user applied plans: {str(e)}",
        )


@router.post("/{applied_plan_id}/advance-index", response_model=dict[str, Any])
async def advance_applied_plan_index(
    applied_plan_id: int,
    by: int = Query(1, description="How many positions to advance the current_workout_index by"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        svc = AppliedCalendarPlanService(db, user_id)
        new_index = await svc.advance_current_index(applied_plan_id, by=by)
        if new_index is None:
            raise HTTPException(status_code=404, detail="Applied plan not found")
        return {"applied_plan_id": applied_plan_id, "current_workout_index": new_index}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to advance index: {str(e)}",
        )


class CancelAppliedPlanRequest(BaseModel):
    dropout_reason: str | None = None


@router.post("/{applied_plan_id}/cancel", response_model=AppliedCalendarPlanResponse)
async def cancel_applied_plan(
    applied_plan_id: int,
    payload: CancelAppliedPlanRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        svc = AppliedCalendarPlanService(db, user_id)
        plan = await svc.cancel_applied_plan(
            applied_plan_id,
            dropout_reason=payload.dropout_reason,
        )
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found")

        full = await svc.get_applied_plan_by_id(applied_plan_id)
        if not full:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Applied plan not found")
        return full
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel applied plan: {str(e)}",
        )


@router.get("", response_model=list[AppliedCalendarPlanResponse])
async def get_applied_plans(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        service = AppliedCalendarPlanService(db, user_id)
        return await service.get_user_applied_plans()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch applied plans: {str(e)}",
        )


@router.get("/active/workouts", response_model=list[dict[str, Any]])
async def get_active_plan_workouts(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    try:
        service = AppliedCalendarPlanService(db, user_id)
        active_plan = await service.get_active_plan()
        if not active_plan:
            raise HTTPException(status_code=404, detail="No active plan found")

        workouts = []
        for workout_rel in sorted(active_plan.workouts, key=lambda w: w.order_index):
            workouts.append(
                {
                    "id": workout_rel.workout_id,
                    "order_index": workout_rel.order_index,
                    "is_current": workout_rel.order_index == active_plan.current_workout_index,
                }
            )

        return workouts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch active plan workouts: {str(e)}",
        )


@router.post("/apply/{plan_id}", response_model=AppliedCalendarPlanResponse)
async def apply_plan(
    plan_id: int,
    compute: ApplyPlanComputeSettings,
    user_max_ids: str = Query(..., description="Comma-separated list of user_max IDs"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        user_max_ids_list = [int(id.strip()) for id in user_max_ids.split(",") if id.strip()]
        if not user_max_ids_list:
            raise HTTPException(status_code=400, detail="At least one user_max_id is required")
        logger.info(
            "applied_plan_apply_requested",
            user_id=user_id,
            plan_id=plan_id,
            user_max_ids=user_max_ids_list,
        )
        service = AppliedCalendarPlanService(db, user_id)
        result = await service.apply_plan(plan_id, compute, user_max_ids_list)
        logger.info(
            "applied_plan_apply_success",
            user_id=user_id,
            plan_id=plan_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply plan: {str(e)}",
        )


@router.post("/apply-async/{plan_id}", response_model=TaskSubmissionResponse)
async def apply_plan_async(
    plan_id: int,
    compute: ApplyPlanComputeSettings,
    user_max_ids: str = Query(..., description="Comma-separated list of user_max IDs"),
    user_id: str = Depends(get_current_user_id),
):
    user_max_ids_list = [int(id.strip()) for id in user_max_ids.split(",") if id.strip()]
    if not user_max_ids_list:
        raise HTTPException(status_code=400, detail="At least one user_max_id is required")
    logger.info(
        "applied_plan_apply_async_requested",
        user_id=user_id,
        plan_id=plan_id,
        user_max_ids=user_max_ids_list,
    )
    return _submit_task(
        apply_plan_task,
        user_id=user_id,
        plan_id=plan_id,
        compute=compute.model_dump(mode="json"),
        user_max_ids=user_max_ids_list,
    )


@router.post("/{applied_plan_id}/run-macros", response_model=dict[str, Any])
async def run_plan_macros(
    applied_plan_id: int,
    index_offset: int = Query(1, description="Offset to apply to current_workout_index when evaluating macros"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = MacroEngine(db, user_id)
        result = await engine.run_for_applied_plan(applied_plan_id, anchor="current", index_offset=index_offset)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run macros: {str(e)}",
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_plans_task_status(task_id: str) -> TaskStatusResponse:
    return build_task_status_response(
        task_id=task_id,
        celery_app=celery_app,
        response_model=TaskStatusResponse,
    )
