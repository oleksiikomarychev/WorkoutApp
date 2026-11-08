import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for accounts-service."""

    ACCOUNTS_DATABASE_URL: str = os.getenv(
        "ACCOUNTS_DATABASE_URL",
        os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:"),
    )
    ACCOUNTS_GRPC_PORT: int = int(os.getenv("ACCOUNTS_GRPC_PORT", "50055"))
    STRIPE_SECRET_KEY: str | None = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_CONNECT_RETURN_URL: str | None = os.getenv("STRIPE_CONNECT_RETURN_URL")
    STRIPE_CONNECT_REFRESH_URL: str | None = os.getenv("STRIPE_CONNECT_REFRESH_URL")
    PLANS_SERVICE_URL: str | None = os.getenv("PLANS_SERVICE_URL")
    INTERNAL_GATEWAY_SECRET: str = os.getenv("INTERNAL_GATEWAY_SECRET", "")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance."""
    return Settings()


settings = get_settings()
