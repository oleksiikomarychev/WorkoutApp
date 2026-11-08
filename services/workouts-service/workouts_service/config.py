from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for workouts-service."""

    WORKOUTS_REDIS_HOST: str = os.getenv("WORKOUTS_REDIS_HOST", "redis")
    WORKOUTS_REDIS_PORT: int = int(os.getenv("WORKOUTS_REDIS_PORT", "6379"))
    WORKOUTS_REDIS_DB: int = int(os.getenv("WORKOUTS_REDIS_DB", "0"))
    WORKOUTS_REDIS_PASSWORD: str | None = os.getenv("WORKOUTS_REDIS_PASSWORD")

    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/3")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/4")
    CELERY_WORKOUTS_QUEUE: str = os.getenv("CELERY_WORKOUTS_QUEUE", "workouts.tasks")
    CELERY_TASK_TIMEOUT_SECONDS: int = int(os.getenv("CELERY_TASK_TIMEOUT_SECONDS", "900"))
    CELERY_TASK_TIME_LIMIT: int = int(os.getenv("CELERY_TASK_TIME_LIMIT", "900"))
    CELERY_RESULT_EXPIRES: int = int(os.getenv("CELERY_RESULT_EXPIRES", "3600"))

    WORKOUTS_DATABASE_URL: str | None = os.getenv("WORKOUTS_DATABASE_URL")
    SUPPLEMENTS_DATABASE_URL: str | None = os.getenv("SUPPLEMENTS_DATABASE_URL")
    DB_POOL_RECYCLE_SECONDS: int = int(os.getenv("DB_POOL_RECYCLE_SECONDS", "300"))

    INTERNAL_GATEWAY_SECRET: str = os.getenv("INTERNAL_GATEWAY_SECRET", "")
    GATEWAY_URL: str = os.getenv("GATEWAY_URL", "http://gateway:8000")
    EXERCISES_SERVICE_URL: str = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")
    PLANS_SERVICE_URL: str = os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005")
    USER_MAX_SERVICE_URL: str = os.getenv("USER_MAX_SERVICE_URL", "http://user-max-service:8003")
    RPE_SERVICE_URL: str = os.getenv("RPE_SERVICE_URL", "http://rpe-service:8001")
    SOCIAL_GATEWAY_URL: str = os.getenv("SOCIAL_GATEWAY_URL", "http://gateway:8000/api/v1/social")
    RPE_TABLE_URL: str = os.getenv("RPE_TABLE_URL", "http://rpe-service:8001/rpe/table")

    SERVICE_PORT: int = int(os.getenv("WORKOUTS_SERVICE_PORT", "8004"))
    GRPC_PORT: int = int(os.getenv("WORKOUTS_GRPC_PORT", "50054"))

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()


settings = get_settings()
