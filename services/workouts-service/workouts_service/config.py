from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    WORKOUTS_REDIS_HOST: str = "redis"
    WORKOUTS_REDIS_PORT: int = 6379
    WORKOUTS_REDIS_DB: int = 0
    WORKOUTS_REDIS_PASSWORD: str | None = None
    CELERY_BROKER_URL: str = "redis://redis:6379/3"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/4"
    CELERY_WORKOUTS_QUEUE: str = "workouts.tasks"
    CELERY_TASK_TIMEOUT_SECONDS: int = 900

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
