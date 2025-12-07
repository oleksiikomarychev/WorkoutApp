from __future__ import annotations

import asyncio
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger

from ..celery_app import PLANS_TASK_QUEUE
from ..dependencies import AsyncSessionLocal
from ..schemas.calendar_plan import ApplyPlanComputeSettings
from ..services.applied_calendar_plan_service import AppliedCalendarPlanService
from ..services.macro_apply import MacroApplier
from ..services.macro_engine import MacroEngine

logger = get_task_logger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


async def _apply_plan_async(
    plan_id: int,
    user_id: str,
    compute_data: dict[str, Any],
    user_max_ids: list[int],
) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        service = AppliedCalendarPlanService(session, user_id)
        compute = ApplyPlanComputeSettings.model_validate(compute_data)
        try:
            result = await service.apply_plan(plan_id, compute, user_max_ids)
        except ValueError as exc:
            return {
                "ok": False,
                "error_type": "ValueError",
                "error_message": str(exc),
            }
        return {
            "ok": True,
            "data": result.model_dump(mode="json"),
        }


async def _apply_macros_async(
    applied_plan_id: int,
    user_id: str,
    index_offset: int,
) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        engine = MacroEngine(session, user_id)
        preview = await engine.run_for_applied_plan(
            applied_plan_id,
            anchor="current",
            index_offset=index_offset,
        )

        svc = AppliedCalendarPlanService(session, user_id)
        plan_changes_results: list[dict[str, Any]] = []
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


@shared_task(
    bind=True,
    name="plans.apply_plan",
    queue=PLANS_TASK_QUEUE,
    max_retries=2,
)
def apply_plan_task(
    self,
    *,
    plan_id: int,
    user_id: str,
    compute: dict[str, Any],
    user_max_ids: list[int],
) -> dict[str, Any]:
    try:
        return _run_async(
            _apply_plan_async(
                plan_id=plan_id,
                user_id=user_id,
                compute_data=compute,
                user_max_ids=user_max_ids,
            )
        )
    except Exception as exc:
        logger.exception("apply_plan_task_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    name="plans.apply_macros",
    queue=PLANS_TASK_QUEUE,
    max_retries=2,
)
def apply_plan_macros_task(
    self,
    *,
    applied_plan_id: int,
    user_id: str,
    index_offset: int,
) -> dict[str, Any]:
    try:
        return _run_async(
            _apply_macros_async(
                applied_plan_id=applied_plan_id,
                user_id=user_id,
                index_offset=index_offset,
            )
        )
    except Exception as exc:
        logger.exception("apply_plan_macros_task_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=60)
