from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    EXERCISES_REDIS_HOST: str = "redis"
    EXERCISES_REDIS_PORT: int = 6379
    EXERCISES_REDIS_DB: int = 0
    EXERCISES_REDIS_PASSWORD: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
