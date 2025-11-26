from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger

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
