import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from ..celery_app import celery_app
from ..dependencies import get_current_user_id
from ..schemas.task_responses import TaskStatusResponse, TaskSubmissionResponse
from ..schemas.user_data import UserDataInput
from ..tasks.plan_tasks import (
    generate_plan_task,
    generate_plan_with_rationale_task,
    generate_plan_with_summary_task,
)

router = APIRouter()

logger = structlog.get_logger(__name__)


def _submit_task(task_fn, user_data: UserDataInput, user_id: str) -> TaskSubmissionResponse:
    signature = task_fn.s(user_data=user_data.model_dump(mode="json"), user_id=user_id)
    async_result = signature.apply_async()
    logger.info(
        "training_plan_task_enqueued",
        task_id=async_result.id,
        task_name=task_fn.name,
        user_id=user_id,
    )
    return TaskSubmissionResponse(task_id=async_result.id, status=async_result.status)


@router.post("/generate-plan/", response_model=TaskSubmissionResponse)
async def generate_plan(user_data: UserDataInput, user_id: str = Depends(get_current_user_id)):
    """Enqueue base training plan generation."""
    return _submit_task(generate_plan_task, user_data, user_id)


@router.post("/generate-plan-with-rationale/", response_model=TaskSubmissionResponse)
async def generate_plan_with_rationale(
    user_data: UserDataInput,
    user_id: str = Depends(get_current_user_id),
):
    """Enqueue plan generation with rationale payload."""
    return _submit_task(generate_plan_with_rationale_task, user_data, user_id)


@router.post("/generate-plan-with-summary/", response_model=TaskSubmissionResponse)
async def generate_plan_with_summary(
    user_data: UserDataInput,
    user_id: str = Depends(get_current_user_id),
):
    """Enqueue plan generation with summary text."""
    return _submit_task(generate_plan_with_summary_task, user_data, user_id)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_training_plan_task_status(task_id: str) -> TaskStatusResponse:
    """Return Celery task status and optional result/error payload."""
    result = AsyncResult(task_id, app=celery_app)
    response = TaskStatusResponse(task_id=task_id, status=result.status)
    if result.failed():
        response.error = str(result.result)
    elif result.successful():
        response.result = result.result
    response.meta = result.info if isinstance(result.info, dict) else None
    return response
