from __future__ import annotations

import os

from celery import Celery

DEFAULT_BROKER_URL = "redis://redis:6379/3"
DEFAULT_RESULT_BACKEND = "redis://redis:6379/4"
DEFAULT_QUEUE = os.getenv("CELERY_WORKOUTS_QUEUE", "workouts.tasks")

celery_app = Celery(
    "workouts_service",
    broker=os.getenv("CELERY_BROKER_URL", DEFAULT_BROKER_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", DEFAULT_RESULT_BACKEND),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue=DEFAULT_QUEUE,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "900")),
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),
)

celery_app.autodiscover_tasks(["workouts_service.tasks"])
