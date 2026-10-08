import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    EXERCISES_REDIS_HOST: str = os.getenv("EXERCISES_REDIS_HOST")
    EXERCISES_REDIS_PORT: int = int(os.getenv("EXERCISES_REDIS_PORT"))
    EXERCISES_REDIS_DB: int = int(os.getenv("EXERCISES_REDIS_DB"))
    EXERCISES_REDIS_PASSWORD: str | None = os.getenv("EXERCISES_REDIS_PASSWORD")

    EXERCISES_MEDIA_DIR: str = os.getenv("EXERCISES_MEDIA_DIR")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
