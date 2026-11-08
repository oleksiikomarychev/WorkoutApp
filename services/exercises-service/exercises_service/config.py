import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for exercises-service."""

    EXERCISES_REDIS_HOST: str = "localhost"
    EXERCISES_REDIS_PORT: int = 6379
    EXERCISES_REDIS_DB: int = 0
    EXERCISES_REDIS_PASSWORD: str | None = None

    EXERCISES_MEDIA_DIR: str = "data/exercise_media"
    EXERCISES_DATABASE_URL: str = os.getenv(
        "EXERCISES_DATABASE_URL",
        os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/exercises_db"),
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
