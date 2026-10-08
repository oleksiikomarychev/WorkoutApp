from __future__ import annotations

from typing import Any, TypeVar

import structlog
from celery import Celery
from celery.result import AsyncResult
from fastapi import HTTPException, status

TStatusModel = TypeVar("TStatusModel")

logger = structlog.get_logger(__name__)


def enqueue_task(
    task_fn,
    *,
    logger,
    log_event: str,
    task_kwargs: dict[str, Any],
    celery_app: Celery,
    log_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    logger.info(
        "attempting_to_enqueue_task", task_name=getattr(task_fn, "name", getattr(task_fn, "__name__", "unknown"))
    )
    try:
        # 1. Check if broker is reachable
        with celery_app.broker_connection(timeout=2) as conn:
            conn.ensure_connection(max_retries=0)

        # 2. Check if there are active workers
        stats = celery_app.control.inspect(timeout=1).active_queues()
        if not stats:
            raise RuntimeError("No active Celery workers found")
    except Exception as e:
        logger.error("celery_service_unreachable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task processing service is currently unavailable. Please try again later.",
        )

    signature = task_fn.s(**task_kwargs)
    async_result = signature.apply_async()

    log_payload: dict[str, Any] = {
        "task_id": async_result.id,
        "task_name": getattr(task_fn, "name", getattr(task_fn, "__name__", None)),
    }
    if log_extra:
        log_payload.update(log_extra)

    try:
        logger.info(log_event, **log_payload)
    except Exception:
        # Logging must not break the primary flow
        logger.exception("failed_to_log_task_enqueued", log_event=log_event)

    return {
        "task_id": async_result.id,
        "status": async_result.status,
    }


def build_task_status_response[TStatusModel](
    *,
    task_id: str,
    celery_app: Celery,
    response_model: type[TStatusModel],
) -> TStatusModel:
    result = AsyncResult(task_id, app=celery_app)
    payload: dict[str, Any] = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.failed():
        payload["error"] = str(result.result)
    elif result.successful():
        payload["result"] = result.result

    info = result.info
    if isinstance(info, dict):
        payload["meta"] = info

    return response_model(**payload)
