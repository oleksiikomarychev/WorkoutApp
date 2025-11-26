from typing import Any, Dict, List, Optional

import structlog
from celery.result import AsyncResult
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
    signature = task_fn.s(user_id=user_id, **kwargs)
    async_result = signature.apply_async()
    logger.info(
        "plans_task_enqueued",
        task_id=async_result.id,
        task_name=task_fn.name,
        user_id=user_id,
    )
    return TaskSubmissionResponse(task_id=async_result.id, status=async_result.status)


@router.get("/active", response_model=Optional[AppliedCalendarPlanResponse])
async def get_active_plan(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Получение активного плана пользователя"""
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
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    group_by: Optional[str] = Query(None, regex="^(order|date)$"),
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


@router.post("/{applied_plan_id}/apply-macros", response_model=Dict[str, Any])
async def apply_plan_macros(
    applied_plan_id: int,
    index_offset: int = Query(0, description="Offset to apply to current_workout_index when evaluating macros"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Вычислить макросы и применить предложенные изменения к будущим тренировкам (батч).

    На текущем этапе изменения применяются к инстансам упражнений в exercises-service путём
    обновления целого инстанса (списка сетов), что безопаснее для согласованности.
    """
    try:
        engine = MacroEngine(db, user_id)
        preview = await engine.run_for_applied_plan(applied_plan_id, anchor="current", index_offset=index_offset)

        # Apply plan-level changes into the applied plan
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

        # Apply patches to exercise instances
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
    """Поставить применение макросов в очередь Celery.

    Существующий синхронный эндпойнт /apply-macros остаётся без изменений; этот вариант лишь
    ставит задачу и возвращает идентификатор Celery-задачи.
    """
    return _submit_task(
        apply_plan_macros_task,
        user_id=user_id,
        applied_plan_id=applied_plan_id,
        index_offset=index_offset,
    )


@router.get("/{plan_id}", response_model=AppliedCalendarPlanResponse)
async def get_applied_plan_details(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)
):
    """Получение полной информации о примененном плане"""
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


@router.get("/user", response_model=List[AppliedCalendarPlanSummaryResponse])
async def get_user_applied_plans(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Получение всех примененных планов пользователя"""
    try:
        service = AppliedCalendarPlanService(db, user_id)
        return await service.get_user_applied_plans()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user applied plans: {str(e)}",
        )


@router.post("/{applied_plan_id}/advance-index", response_model=Dict[str, Any])
async def advance_applied_plan_index(
    applied_plan_id: int,
    by: int = Query(1, description="How many positions to advance the current_workout_index by"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Advance current_workout_index for the applied plan."""
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
    dropout_reason: Optional[str] = None


@router.post("/{applied_plan_id}/cancel", response_model=AppliedCalendarPlanResponse)
async def cancel_applied_plan(
    applied_plan_id: int,
    payload: CancelAppliedPlanRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Отменить (отказаться от) применённый план пользователя.

    Помечает план как неактивный, выставляет статус cancelled (если он ещё не задан),
    фиксирует время отмены и, при необходимости, причину отказа.
    """
    try:
        svc = AppliedCalendarPlanService(db, user_id)
        plan = await svc.cancel_applied_plan(
            applied_plan_id,
            dropout_reason=payload.dropout_reason,
        )
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found")
        # Преобразуем ORM-объект в response-схему, используя уже существующий метод get_applied_plan_by_id
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


@router.get("", response_model=List[AppliedCalendarPlanResponse])
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


@router.get("/active/workouts", response_model=List[Dict[str, Any]])
async def get_active_plan_workouts(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Get ordered workouts for user's active plan"""
    try:
        service = AppliedCalendarPlanService(db, user_id)
        active_plan = await service.get_active_plan()
        if not active_plan:
            raise HTTPException(status_code=404, detail="No active plan found")

        # Get workouts in order
        workouts = []
        for workout_rel in sorted(active_plan.workouts, key=lambda w: w.order_index):
            # In real implementation, fetch workout details from workout-service
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
    """Применение плана пользователем с настройками вычислений"""
    try:
        # Convert comma-separated string to list of integers, skipping empty parts
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
    """Асинхронное применение плана через Celery.

    Существующий /apply/{plan_id} по-прежнему выполняет операцию синхронно; этот эндпойнт
    только ставит задачу и возвращает task_id.
    """
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


@router.post("/{applied_plan_id}/run-macros", response_model=Dict[str, Any])
async def run_plan_macros(
    applied_plan_id: int,
    index_offset: int = Query(1, description="Offset to apply to current_workout_index when evaluating macros"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Запустить макросы для примененного плана и вернуть краткое резюме.

    Фаза 1: dry‑run – движок только считает активные макросы и возвращает summary
    без модификаций тренировок. В следующих шагах добавим реальные действия.
    """
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
    """Получить статус Celery-задачи plans-service."""

    result = AsyncResult(task_id, app=celery_app)
    response = TaskStatusResponse(task_id=task_id, status=result.status)
    if result.failed():
        response.error = str(result.result)
    elif result.successful():
        response.result = result.result
    response.meta = result.info if isinstance(result.info, dict) else None
    return response
