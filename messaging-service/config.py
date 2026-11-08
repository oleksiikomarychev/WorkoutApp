"""Configuration for Messaging Service."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql://user:pass@postgres-messaging:5432/messaging"

    @property
    def effective_database_url(self) -> str:
        """Get database URL from environment or default."""
        return os.getenv("DATABASE_URL") or os.getenv("MESSAGING_DATABASE_URL") or self.database_url

    # Redis
    redis_url: str = "redis://redis:6379"

    # Webhook
    webhook_hmac_secret: str = "change-me-in-production"

    # WebSocket
    ws_heartbeat_timeout: int = 60  # seconds
    ws_max_message_size: int = 65536  # 64KB

    # Presence and Typing
    typing_ttl: int = 5  # seconds
    presence_ttl: int = 90  # seconds

    # Service
    service_name: str = "messaging-service"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
