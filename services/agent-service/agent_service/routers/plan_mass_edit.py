"""Router for plan mass edit endpoints in agent-service."""

from __future__ import annotations

from typing import Any, Callable

import structlog
from backend_common.celery_utils import build_task_status_response, enqueue_task
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


def _submit_task(
    task_fn: Callable[..., Any],
    payload: AgentPlanMassEditRequest,
    user_id: str,
) -> TaskSubmissionResponse:
    payload_dict = enqueue_task(
        task_fn,
        logger=logger,
        log_event="mass_edit_task_enqueued",
        task_kwargs={
            "plan_id": payload.plan_id,
            "user_id": user_id,
            "mode": payload.mode,
            "prompt": payload.prompt,
        },
        log_extra={
            "plan_id": payload.plan_id,
            "user_id": user_id,
            "mode": payload.mode,
        },
    )
    return TaskSubmissionResponse(**payload_dict)


def _submit_applied_task(
    task_fn: Callable[..., Any],
    payload: AgentAppliedPlanMassEditRequest,
    user_id: str,
) -> TaskSubmissionResponse:
    payload_dict = enqueue_task(
        task_fn,
        logger=logger,
        log_event="applied_mass_edit_task_enqueued",
        task_kwargs={
            "applied_plan_id": payload.applied_plan_id,
            "user_id": user_id,
            "mode": payload.mode,
            "prompt": payload.prompt,
        },
        log_extra={
            "applied_plan_id": payload.applied_plan_id,
            "user_id": user_id,
            "mode": payload.mode,
        },
    )
    return TaskSubmissionResponse(**payload_dict)


def _submit_applied_shift_task(
    task_fn: Callable[..., Any],
    payload: AgentAppliedPlanScheduleShiftRequest,
    user_id: str,
) -> TaskSubmissionResponse:
    payload_dict = enqueue_task(
        task_fn,
        logger=logger,
        log_event="applied_schedule_shift_task_enqueued",
        task_kwargs={
            "applied_plan_id": payload.applied_plan_id,
            "user_id": user_id,
            "from_date": payload.from_date,
            "days": payload.days,
            "to_date": payload.to_date,
            "new_rest_days": payload.new_rest_days,
            "action_type": payload.action_type,
            "only_future": payload.only_future,
            "status_in": payload.status_in,
        },
        log_extra={
            "applied_plan_id": payload.applied_plan_id,
            "user_id": user_id,
            "days": payload.days,
            "action_type": payload.action_type,
        },
    )
    return TaskSubmissionResponse(**payload_dict)


@router.post("/plan-mass-edit", response_model=TaskSubmissionResponse)
async def plan_mass_edit_endpoint(
    payload: AgentPlanMassEditRequest,
    user_id: str = Depends(get_current_user_id),
) -> TaskSubmissionResponse:
    """Submit direct mass edit task for a template plan."""
    return _submit_task(execute_mass_edit_task, payload, user_id)


@router.post("/plan-mass-edit-gpt", response_model=TaskSubmissionResponse)
async def plan_mass_edit_gpt_endpoint(
    payload: AgentPlanMassEditRequest,
    user_id: str = Depends(get_current_user_id),
) -> TaskSubmissionResponse:
    """Submit agentic mass edit task for a template plan."""
    return _submit_task(execute_mass_edit_agent_task, payload, user_id)


@router.post("/applied-plan-mass-edit", response_model=TaskSubmissionResponse)
async def applied_plan_mass_edit_endpoint(
    payload: AgentAppliedPlanMassEditRequest,
    user_id: str = Depends(get_current_user_id),
) -> TaskSubmissionResponse:
    """Submit mass edit task for an active/applied plan."""
    return _submit_applied_task(execute_applied_mass_edit_task, payload, user_id)


@router.post("/applied-plan-shift-schedule", response_model=TaskSubmissionResponse)
async def applied_plan_shift_schedule_endpoint(
    payload: AgentAppliedPlanScheduleShiftRequest,
    user_id: str = Depends(get_current_user_id),
) -> TaskSubmissionResponse:
    """Submit schedule shift task for an applied plan."""
    return _submit_applied_shift_task(execute_applied_schedule_shift_task, payload, user_id)


@router.get("/plan-mass-edit/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_mass_edit_task_status(task_id: str) -> TaskStatusResponse:
    """Retrieve status of mass edit Celery task."""
    return build_task_status_response(
        task_id=task_id,
        celery_app=celery_app,
        response_model=TaskStatusResponse,
    )
