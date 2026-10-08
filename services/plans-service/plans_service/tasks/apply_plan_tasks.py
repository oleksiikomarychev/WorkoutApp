from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger

from ..celery_app import PLANS_TASK_QUEUE
from ..dependencies import DATABASE_URL
from ..schemas.calendar_plan import ApplyPlanComputeSettings
from ..services.applied_calendar_plan_service import AppliedCalendarPlanService
from ..services.macro_apply import MacroApplier
from ..services.macro_engine import MacroEngine

logger = get_task_logger(__name__)


def _run_async(coro_or_func):
    
    if asyncio.iscoroutinefunction(coro_or_func):
        coro = coro_or_func()
    else:
        coro = coro_or_func
    
    def run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_new_loop)
        return future.result()


def _apply_plan_sync(
    plan_id: int,
    user_id: str,
    compute_data: dict[str, Any],
    user_max_ids: list[int],
    *,
    progress: Any | None = None,
) -> dict[str, Any]:
    async def _run_async_session():
        from backend_common.database import create_async_engine_and_session
        task_engine, TaskAsyncSessionLocal = create_async_engine_and_session(
            DATABASE_URL,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=False,
            pool_recycle=3600,
        )
        
        async with TaskAsyncSessionLocal() as session:
            service = AppliedCalendarPlanService(session, user_id)
            compute = ApplyPlanComputeSettings.model_validate(compute_data)
            try:
                result = await service.apply_plan(plan_id, compute, user_max_ids, progress=progress)
                if hasattr(result, 'model_dump'):
                    return result.model_dump()
                return result
            except ValueError as exc:
                return {
                    "ok": False,
                    "error_type": "ValueError",
                    "error_message": str(exc),
                }
            finally:
                await task_engine.dispose()
    
    return _run_async(_run_async_session)


async def _apply_macros_async(
    applied_plan_id: int,
    user_id: str,
    index_offset: int,
) -> dict[str, Any]:
    from backend_common.database import create_async_engine_and_session
    task_engine, TaskAsyncSessionLocal = create_async_engine_and_session(
        DATABASE_URL, 
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=False,
        pool_recycle=3600,
    )
    
    try:
        async with TaskAsyncSessionLocal() as session:
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
    finally:
        await task_engine.dispose()


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
        def _progress(meta: dict[str, Any]) -> None:
            try:
                self.update_state(state="PROGRESS", meta=meta)
            except Exception:
                # Progress reporting must not break the task
                return

        return _apply_plan_sync(
            plan_id=plan_id,
            user_id=user_id,
            compute_data=compute,
            user_max_ids=user_max_ids,
            progress=_progress,
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
