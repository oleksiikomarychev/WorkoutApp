from __future__ import annotations

import os

from celery import Celery

DEFAULT_BROKER_URL = "redis://redis:6379/1"
DEFAULT_RESULT_BACKEND = "redis://redis:6379/2"
PLANS_TASK_QUEUE = os.getenv("CELERY_PLANS_QUEUE", "plans.tasks")


def _parse_time_limit(value: str | None) -> int | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = int(raw)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed

celery_app = Celery(
    "plans_service",
    broker=os.getenv("CELERY_BROKER_URL", DEFAULT_BROKER_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", DEFAULT_RESULT_BACKEND),
    task_always_eager=False,
    task_eager_propagates=True,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue=os.getenv("CELERY_TASK_DEFAULT_QUEUE", PLANS_TASK_QUEUE),
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_time_limit=_parse_time_limit(os.getenv("CELERY_TASK_TIME_LIMIT", "0")),
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),
    worker_pool="solo",
)

celery_app.autodiscover_tasks(["plans_service"])
