import structlog
from backend_common.celery_utils import build_task_status_response, enqueue_task
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
    payload = enqueue_task(
        task_fn,
        logger=logger,
        log_event="training_plan_task_enqueued",
        task_kwargs={
            "user_data": user_data.model_dump(mode="json"),
            "user_id": user_id,
        },
        log_extra={
            "user_id": user_id,
        },
    )
    return TaskSubmissionResponse(**payload)


@router.post("/generate-plan/", response_model=TaskSubmissionResponse)
async def generate_plan(user_data: UserDataInput, user_id: str = Depends(get_current_user_id)):
    return _submit_task(generate_plan_task, user_data, user_id)


@router.post("/generate-plan-with-rationale/", response_model=TaskSubmissionResponse)
async def generate_plan_with_rationale(
    user_data: UserDataInput,
    user_id: str = Depends(get_current_user_id),
):
    return _submit_task(generate_plan_with_rationale_task, user_data, user_id)


@router.post("/generate-plan-with-summary/", response_model=TaskSubmissionResponse)
async def generate_plan_with_summary(
    user_data: UserDataInput,
    user_id: str = Depends(get_current_user_id),
):
    return _submit_task(generate_plan_with_summary_task, user_data, user_id)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_training_plan_task_status(task_id: str) -> TaskStatusResponse:
    return build_task_status_response(
        task_id=task_id,
        celery_app=celery_app,
        response_model=TaskStatusResponse,
    )
