from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PLANS_DATABASE_URL: str = ""
    GEMINI_API_KEY: str = ""
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    SERVICE_PORT: int = 8005
    GRPC_PORT: int = 50053

    # Redis Configuration
    PLANS_REDIS_HOST: str = "redis"
    PLANS_REDIS_PORT: int = 6379
    PLANS_REDIS_DB: int = 0
    PLANS_REDIS_PASSWORD: str | None = None

    # Celery Configuration
    CELERY_TASK_TIMEOUT_SECONDS: int = 900

    # Downstream Microservices URLs
    EXERCISES_SERVICE_URL: str = "http://exercises-service:8002"
    USER_MAX_SERVICE_URL: str = "http://user-max-service:8003"
    WORKOUTS_SERVICE_URL: str = "http://workouts-service:8004"
    RPE_SERVICE_URL: str = "http://rpe-service:8001"

    # Database Pool Settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 3600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
