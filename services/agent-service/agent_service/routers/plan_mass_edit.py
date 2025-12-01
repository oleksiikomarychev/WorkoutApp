import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from ..celery_app import celery_app
from ..dependencies import get_current_user_id
from ..schemas.mass_edit import (
    AgentAppliedPlanMassEditRequest,
    AgentAppliedPlanScheduleShiftRequest,
    AgentPlanMassEditRequest,
)
from ..schemas.task_responses import TaskStatusResponse, TaskSubmissionResponse
from ..tasks.mass_edit_tasks import (
    execute_applied_mass_edit_task,
    execute_applied_schedule_shift_task,
    execute_mass_edit_agent_task,
    execute_mass_edit_task,
)

router = APIRouter(prefix="/agent", tags=["mass_edit"])
logger = structlog.get_logger(__name__)


def _submit_task(task_fn, payload: AgentPlanMassEditRequest, user_id: str) -> TaskSubmissionResponse:
    signature = task_fn.s(
        plan_id=payload.plan_id,
        user_id=user_id,
        mode=payload.mode,
        prompt=payload.prompt,
    )
    async_result = signature.apply_async()
    logger.info(
        "mass_edit_task_enqueued",
        task_id=async_result.id,
        task_name=task_fn.name,
        plan_id=payload.plan_id,
        user_id=user_id,
        mode=payload.mode,
    )
    return TaskSubmissionResponse(task_id=async_result.id, status=async_result.status)


def _submit_applied_task(task_fn, payload: AgentAppliedPlanMassEditRequest, user_id: str) -> TaskSubmissionResponse:
    signature = task_fn.s(
        applied_plan_id=payload.applied_plan_id,
        user_id=user_id,
        mode=payload.mode,
        prompt=payload.prompt,
    )
    async_result = signature.apply_async()
    logger.info(
        "applied_mass_edit_task_enqueued",
        task_id=async_result.id,
        task_name=task_fn.name,
        applied_plan_id=payload.applied_plan_id,
        user_id=user_id,
        mode=payload.mode,
    )
    return TaskSubmissionResponse(task_id=async_result.id, status=async_result.status)


def _submit_applied_shift_task(
    task_fn,
    payload: AgentAppliedPlanScheduleShiftRequest,
    user_id: str,
) -> TaskSubmissionResponse:
    signature = task_fn.s(
        applied_plan_id=payload.applied_plan_id,
        user_id=user_id,
        from_date=payload.from_date,
        days=payload.days,
        to_date=payload.to_date,
        new_rest_days=payload.new_rest_days,
        action_type=payload.action_type,
        only_future=payload.only_future,
        status_in=payload.status_in,
    )
    async_result = signature.apply_async()
    logger.info(
        "applied_schedule_shift_task_enqueued",
        task_id=async_result.id,
        task_name=task_fn.name,
        applied_plan_id=payload.applied_plan_id,
        user_id=user_id,
        days=payload.days,
        action_type=payload.action_type,
    )
    return TaskSubmissionResponse(task_id=async_result.id, status=async_result.status)


@router.post("/plan-mass-edit", response_model=TaskSubmissionResponse)
async def plan_mass_edit_endpoint(
    payload: AgentPlanMassEditRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Запустить mass edit (прямое применение команды) в Celery."""

    return _submit_task(execute_mass_edit_task, payload, user_id)


@router.post("/plan-mass-edit-gpt", response_model=TaskSubmissionResponse)
async def plan_mass_edit_gpt_endpoint(
    payload: AgentPlanMassEditRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Запустить сценарий с tool-агентом через Celery."""

    return _submit_task(execute_mass_edit_agent_task, payload, user_id)


@router.post("/applied-plan-mass-edit", response_model=TaskSubmissionResponse)
async def applied_plan_mass_edit_endpoint(
    payload: AgentAppliedPlanMassEditRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Запустить mass edit уже применённого (applied) плана через Celery."""

    return _submit_applied_task(execute_applied_mass_edit_task, payload, user_id)


@router.post("/applied-plan-shift-schedule", response_model=TaskSubmissionResponse)
async def applied_plan_shift_schedule_endpoint(
    payload: AgentAppliedPlanScheduleShiftRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Запустить сдвиг расписания applied-плана через Celery."""

    return _submit_applied_shift_task(execute_applied_schedule_shift_task, payload, user_id)


@router.get("/plan-mass-edit/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_mass_edit_task_status(task_id: str) -> TaskStatusResponse:
    """Вернуть статус выполнения mass edit задачи (calendar или applied)."""

    result = AsyncResult(task_id, app=celery_app)
    response = TaskStatusResponse(task_id=task_id, status=result.status)
    if result.failed():
        response.error = str(result.result)
    elif result.successful():
        response.result = result.result
    response.meta = result.info if isinstance(result.info, dict) else None
    return response
