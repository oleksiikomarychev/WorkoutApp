from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for rpe-service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    USER_MAX_SERVICE_URL: str = "http://user-max-service:8003"
    INTERNAL_GATEWAY_SECRET: str = ""
    RPE_TABLE_PATH: str | None = None
    RPE_TABLE_JSON: str | None = None
    SERVICE_PORT: int = 8001
    GRPC_PORT: int = 50051


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance."""
    return Settings()


settings = get_settings()
