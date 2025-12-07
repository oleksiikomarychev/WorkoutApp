from __future__ import annotations

from typing import Any, TypeVar

import structlog
from celery import Celery
from celery.result import AsyncResult

TStatusModel = TypeVar("TStatusModel")

logger = structlog.get_logger(__name__)


def enqueue_task(
    task_fn,
    *,
    logger,
    log_event: str,
    task_kwargs: dict[str, Any],
    log_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
