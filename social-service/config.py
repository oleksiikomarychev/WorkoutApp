"""Configuration for Social Service."""
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for social service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Database
    database_url: str = Field(
        default="postgresql://user:pass@postgres-social:5432/social",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    # Redis
    redis_url: str = Field(
        default="redis://redis:6379",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )

    # Webhook
    webhook_hmac_secret: str = Field(
        default="change-me-in-production",
        validation_alias=AliasChoices("WEBHOOK_HMAC_SECRET", "webhook_hmac_secret"),
    )

    # Internal gateway secret for cross-service authenticated endpoints (e.g. purge)
    internal_gateway_secret: str = Field(
        default="",
        validation_alias=AliasChoices("INTERNAL_GATEWAY_SECRET", "internal_gateway_secret"),
    )

    # Service
    service_name: str = Field(
        default="social-service",
        validation_alias=AliasChoices("SERVICE_NAME", "service_name"),
    )

    @field_validator("service_name", mode="before")
    @classmethod
    def default_service_name(cls, v: str | None) -> str:
        """Fallback to default if empty or blank."""
        if not v or not str(v).strip():
            return "social-service"
        return str(v).strip()

    @property
    def effective_database_url(self) -> str:
        """Get database URL normalized for SQLAlchemy."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


settings = Settings()
