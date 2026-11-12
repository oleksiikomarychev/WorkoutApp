from unittest.mock import AsyncMock, patch

import pytest
from celery.exceptions import Retry
from fastapi import HTTPException
from plans_service.routers.applied_calendar_plans import apply_plan, apply_plan_async
from plans_service.schemas.calendar_plan import ApplyPlanComputeSettings
from plans_service.tasks import apply_plan_tasks


@pytest.fixture
def compute():
    return ApplyPlanComputeSettings(compute_weights=False, rounding_step=2.5)


@pytest.mark.asyncio
async def test_sync_apply_preserves_active_plan_conflict(compute):
    with patch("plans_service.routers.applied_calendar_plans.AppliedCalendarPlanService") as service_class:
        service_class.return_value.apply_plan = AsyncMock(
            side_effect=HTTPException(status_code=409, detail="An active plan already exists")
        )
        with pytest.raises(HTTPException) as error:
            await apply_plan(1, compute, "7", False, AsyncMock(), "user-1")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_async_apply_rejects_before_enqueuing(compute):
    with patch("plans_service.routers.applied_calendar_plans.AppliedCalendarPlanService") as service_class:
        service_class.return_value.get_active_plan = AsyncMock(return_value=object())
        with patch("plans_service.routers.applied_calendar_plans._submit_task") as submit:
            with pytest.raises(HTTPException) as error:
                await apply_plan_async(1, compute, "7", False, AsyncMock(), "user-1")
            submit.assert_not_called()
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_async_apply_forwards_explicit_replacement(compute):
    with patch("plans_service.routers.applied_calendar_plans._submit_task", return_value="queued") as submit:
        result = await apply_plan_async(1, compute, "7", True, AsyncMock(), "user-1")
    assert result == "queued"
    assert submit.call_args.kwargs["replace_active"] is True


def test_cleanup_outage_reaches_retry_without_logger_error():
    outage = RuntimeError("synthetic cleanup outage")
    task = apply_plan_tasks.cleanup_failed_application_task
    with patch.object(apply_plan_tasks, "_run_async", side_effect=outage):
        with patch.object(task, "retry", side_effect=Retry("scheduled")) as retry:
            with pytest.raises(Retry):
                task.run(user_id="synthetic-user", applied_plan_id=7)
    retry.assert_called_once_with(exc=outage, countdown=60)
