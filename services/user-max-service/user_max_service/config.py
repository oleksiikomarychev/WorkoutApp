"""Configuration settings for user-max-service."""

import os
from typing import Any

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore[assignment]

    def SettingsConfigDict(**kwargs: Any) -> dict[str, Any]:
        return kwargs


class Settings(BaseSettings):
    """Configuration settings for user-max-service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    USER_MAX_DATABASE_URL: str = os.getenv(
        "USER_MAX_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/user_max_db",
    )
    EXERCISES_SERVICE_URL: str = os.getenv(
        "EXERCISES_SERVICE_URL",
        os.getenv("GATEWAY_URL", "http://exercises-service:8002"),
    )
    GATEWAY_URL: str = os.getenv("GATEWAY_URL", "http://gateway:8000")
    INTERNAL_GATEWAY_SECRET: str = os.getenv("INTERNAL_GATEWAY_SECRET", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    EX_META_TTL_SECONDS: float = float(os.getenv("EX_META_TTL_SECONDS", "1800"))
    SERVICE_PORT: int = int(os.getenv("USER_MAX_SERVICE_PORT", "8003"))


settings = Settings()
