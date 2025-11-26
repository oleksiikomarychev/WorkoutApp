from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PLANS_DATABASE_URL: str = ""
    GEMINI_API_KEY: str = ""
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    PLANS_REDIS_HOST: str = "redis"
    PLANS_REDIS_PORT: int = 6379
    PLANS_REDIS_DB: int = 0
    PLANS_REDIS_PASSWORD: str | None = None
    CELERY_TASK_TIMEOUT_SECONDS: int = 900

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
