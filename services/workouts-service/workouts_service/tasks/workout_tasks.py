from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger

from .. import schemas
from ..celery_app import DEFAULT_QUEUE
from ..database import AsyncSessionLocal
from ..services.rpc_client import PlansServiceRPC
from ..services.workout_service import WorkoutService

logger = get_task_logger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


def _parse_baseline_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


async def _shift_schedule_in_plan_async(
    *,
    user_id: str,
    applied_plan_id: int,
    from_order_index: int,
    delta_days: int,
    delta_index: int,
    exclude_ids: Optional[List[int]] = None,
    only_future: bool = True,
    baseline_date: Optional[str] = None,
) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        plans_rpc = PlansServiceRPC()
        service = WorkoutService(db, plans_rpc, user_id=user_id)
        parsed_baseline = _parse_baseline_date(baseline_date)
        summary = await service.shift_schedule_in_plan(
            applied_plan_id=applied_plan_id,
            from_order_index=from_order_index,
            delta_days=delta_days,
            delta_index=delta_index,
            exclude_ids=exclude_ids or [],
            only_future=only_future,
            baseline_date=parsed_baseline,
        )
        return {"ok": True, **summary}


@shared_task(
    bind=True,
    name="workouts.shift_schedule_in_plan",
    queue=DEFAULT_QUEUE,
    max_retries=1,
)
def shift_schedule_in_plan_task(
    self,
    *,
    user_id: str,
    applied_plan_id: int,
    from_order_index: int,
    delta_days: int,
    delta_index: int,
    exclude_ids: Optional[List[int]] = None,
    only_future: bool = True,
    baseline_date: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        logger.info(
            "shift_schedule_in_plan_task_enqueued",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_order_index=from_order_index,
            delta_days=delta_days,
            delta_index=delta_index,
            exclude_count=len(exclude_ids or []),
            only_future=only_future,
            baseline_date=baseline_date,
        )
        return _run_async(
            _shift_schedule_in_plan_async(
                user_id=user_id,
                applied_plan_id=applied_plan_id,
                from_order_index=from_order_index,
                delta_days=delta_days,
                delta_index=delta_index,
                exclude_ids=exclude_ids,
                only_future=only_future,
                baseline_date=baseline_date,
            )
        )
    except Exception as exc:  # pragma: no cover - rely on Celery retries/logs
        logger.exception(
            "shift_schedule_in_plan_task_failed",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            exc_info=exc,
        )
        raise self.retry(exc=exc, countdown=60)


async def _applied_plan_mass_edit_async(
    *,
    user_id: str,
    applied_plan_id: int,
    command: Dict[str, Any],
) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        plans_rpc = PlansServiceRPC()
        service = WorkoutService(db, plans_rpc, user_id=user_id)
        cmd_obj = schemas.AppliedPlanMassEditCommand.model_validate(command)
        result = await service.apply_applied_plan_mass_edit(applied_plan_id, cmd_obj)
        return {"ok": True, "result": result.model_dump()}


@shared_task(
    bind=True,
    name="workouts.applied_plan_mass_edit_sets",
    queue=DEFAULT_QUEUE,
    max_retries=1,
)
def applied_plan_mass_edit_sets_task(
    self,
    *,
    user_id: str,
    applied_plan_id: int,
    command: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        logger.info(
            "applied_plan_mass_edit_task_enqueued",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            mode=command.get("mode"),
        )
        return _run_async(
            _applied_plan_mass_edit_async(
                user_id=user_id,
                applied_plan_id=applied_plan_id,
                command=command,
            )
        )
    except Exception as exc:  # pragma: no cover - rely on Celery retries/logs
        logger.exception(
            "applied_plan_mass_edit_task_failed",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            exc_info=exc,
        )
        raise self.retry(exc=exc, countdown=60)


async def _applied_plan_schedule_shift_async(
    *,
    user_id: str,
    applied_plan_id: int,
    from_date: str,
    days: int,
    only_future: bool = True,
    status_in: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Async helper to shift applied-plan schedule from a given date.

    This calls WorkoutService.shift_applied_plan_schedule_from_date using the
    same logic as the HTTP endpoint, but in a Celery-friendly context.
    """

    async with AsyncSessionLocal() as db:
        plans_rpc = PlansServiceRPC()
        service = WorkoutService(db, plans_rpc, user_id=user_id)

        # Build command object compatible with AppliedPlanScheduleShiftCommand
        command: Dict[str, Any] = {
            "from_date": from_date,
            "days": days,
            "only_future": only_future,
            "status_in": status_in,
        }
        cmd_obj = schemas.AppliedPlanScheduleShiftCommand.model_validate(command)
        summary = await service.shift_applied_plan_schedule_from_date(applied_plan_id, cmd_obj)
        return {"ok": True, "summary": summary}


@shared_task(
    bind=True,
    name="workouts.applied_plan_schedule_shift",
    queue=DEFAULT_QUEUE,
    max_retries=1,
)
def applied_plan_schedule_shift_task(
    self,
    *,
    user_id: str,
    applied_plan_id: int,
    from_date: str,
    days: int,
    only_future: bool = True,
    status_in: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        logger.info(
            "applied_plan_schedule_shift_task_enqueued",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_date=from_date,
            days=days,
            only_future=only_future,
            status_in=status_in,
        )
        return _run_async(
            _applied_plan_schedule_shift_async(
                user_id=user_id,
                applied_plan_id=applied_plan_id,
                from_date=from_date,
                days=days,
                only_future=only_future,
                status_in=status_in,
            )
        )
    except Exception as exc:  # pragma: no cover - rely on Celery retries/logs
        logger.exception(
            "applied_plan_schedule_shift_task_failed",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            exc_info=exc,
        )
        raise self.retry(exc=exc, countdown=60)
