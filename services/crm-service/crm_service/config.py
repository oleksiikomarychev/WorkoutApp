from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for crm-service."""

    CRM_DATABASE_URL: str = os.getenv(
        "CRM_DATABASE_URL",
        os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:"),
    )
    WORKOUTS_SERVICE_URL: str = os.getenv("WORKOUTS_SERVICE_URL", "http://workouts-service:8004")
    PLANS_SERVICE_URL: str = os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005")
    EXERCISES_SERVICE_URL: str = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")
    AGENT_SERVICE_URL: str = os.getenv("AGENT_SERVICE_URL", "http://agent-service:8006")
    ACCOUNTS_SERVICE_URL: str = os.getenv("ACCOUNTS_SERVICE_URL", "http://accounts-service:8007")

    MESSAGING_GATEWAY_URL: str = os.getenv(
        "MESSAGING_GATEWAY_URL", "http://gateway:8000/api/v1/messaging"
    )
    INTERNAL_GATEWAY_SECRET: str = os.getenv("INTERNAL_GATEWAY_SECRET", "")

    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PLATFORM_FEE_PERCENT: float = float(os.getenv("STRIPE_PLATFORM_FEE_PERCENT", "5.0"))
    STRIPE_CHECKOUT_SUCCESS_URL: str = os.getenv("STRIPE_CHECKOUT_SUCCESS_URL", "")
    STRIPE_CHECKOUT_CANCEL_URL: str = os.getenv("STRIPE_CHECKOUT_CANCEL_URL", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Backwards compatibility properties for lowercase access
    @property
    def workouts_service_url(self) -> str:
        return self.WORKOUTS_SERVICE_URL

    @property
    def plans_service_url(self) -> str:
        return self.PLANS_SERVICE_URL

    @property
    def exercises_service_url(self) -> str:
        return self.EXERCISES_SERVICE_URL

    @property
    def agent_service_url(self) -> str:
        return self.AGENT_SERVICE_URL

    @property
    def accounts_service_url(self) -> str:
        return self.ACCOUNTS_SERVICE_URL


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance."""
    return Settings()


settings = get_settings()
