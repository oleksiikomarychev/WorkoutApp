"""Configuration for Webhook Dispatcher Service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for webhook-dispatcher service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Redis configuration
    redis_url: str = Field(
        default="redis://localhost:6379",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )

    # Database URLs for reading webhook subscriptions
    social_database_url: str = Field(
        default="postgresql://user:pass@localhost:5432/social",
        validation_alias=AliasChoices("SOCIAL_DATABASE_URL", "social_database_url"),
    )
    messaging_database_url: str = Field(
        default="postgresql://user:pass@localhost:5432/messaging",
        validation_alias=AliasChoices("MESSAGING_DATABASE_URL", "messaging_database_url"),
    )

    # Consumer configuration
    consumer_group_name: str = Field(
        default="webhook-dispatcher",
        validation_alias=AliasChoices("CONSUMER_GROUP_NAME", "consumer_group_name"),
    )
    consumer_name: str = Field(
        default="dispatcher-1",
        validation_alias=AliasChoices("CONSUMER_NAME", "consumer_name"),
    )
    batch_size: int = Field(
        default=10,
        validation_alias=AliasChoices("BATCH_SIZE", "batch_size"),
    )
    block_time_ms: int = Field(
        default=5000,
        validation_alias=AliasChoices("BLOCK_TIME_MS", "block_time_ms"),
    )

    # Delivery configuration
    delivery_timeout: int = Field(
        default=10,
        validation_alias=AliasChoices("WEBHOOK_TIMEOUT", "delivery_timeout", "DELIVERY_TIMEOUT"),
    )
    max_retries: int = Field(
        default=5,
        validation_alias=AliasChoices("WEBHOOK_MAX_RETRIES", "max_retries", "MAX_RETRIES"),
    )
    retry_delays: list[int] = Field(
        default_factory=lambda: [60, 300, 900, 3600, 10800],
    )

    # Logging and environment
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL", "log_level"),
    )
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "app_env"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
