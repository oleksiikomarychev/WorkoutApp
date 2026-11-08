"""Configuration settings for agent-service."""

from __future__ import annotations

import os
from typing import Any

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore[assignment]

    def SettingsConfigDict(**kwargs: Any) -> dict[str, Any]:
        return kwargs


class Settings(BaseSettings):
    """Configuration settings for agent-service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    AGENT_DATABASE_URL: str = os.getenv(
        "AGENT_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/workout_agent",
    )
    INTERNAL_GATEWAY_SECRET: str = os.getenv("INTERNAL_GATEWAY_SECRET", "")
    FIREBASE_PROJECT_ID: str | None = os.getenv("FIREBASE_PROJECT_ID")
    HF_TOKEN: str | None = os.getenv("HF_TOKEN")
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash-lite")
    STAGED_LLM_PROVIDER: str = os.getenv("STAGED_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "gemini"))
    GENAI_STAGED_MODEL: str = os.getenv("GENAI_STAGED_MODEL", os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"))

    GENAI_MAX_ATTEMPTS: int = int(os.getenv("GENAI_MAX_ATTEMPTS", "3"))
    GENAI_BASE_DELAY: float = float(os.getenv("GENAI_BASE_DELAY", "1.5"))
    GENAI_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("GENAI_RATE_LIMIT_PER_MINUTE", "9"))
    GENAI_RATE_LIMIT_WINDOW_SECONDS: float = float(os.getenv("GENAI_RATE_LIMIT_WINDOW_SECONDS", "60.0"))
    GENAI_RATE_LIMIT_CONCURRENCY: int = int(os.getenv("GENAI_RATE_LIMIT_CONCURRENCY", "1"))

    USER_MAX_SERVICE_URL: str = os.getenv("USER_MAX_SERVICE_URL", "http://user-max-service:8003")
    EXERCISES_SERVICE_URL: str = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")
    PLANS_SERVICE_URL: str = os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005")
    WORKOUTS_SERVICE_URL: str = os.getenv("WORKOUTS_SERVICE_URL", "http://workouts-service:8004")
    CRM_SERVICE_URL: str = os.getenv("CRM_SERVICE_URL", "http://crm-service:8008")
    RPE_SERVICE_URL: str = os.getenv("RPE_SERVICE_URL", "http://rpe-service:8001")
    RPE_TABLE_URL: str = os.getenv("RPE_TABLE_URL", "http://rpe-service:8001/rpe/table")

    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
    CELERY_PLAN_QUEUE: str = os.getenv("CELERY_PLAN_QUEUE", "agent.llm")
    CELERY_TOOLS_QUEUE: str = os.getenv("CELERY_TOOLS_QUEUE", "agent.tools")
    CELERY_TASK_TIMEOUT_SECONDS: int = int(os.getenv("CELERY_TASK_TIMEOUT_SECONDS", "600"))

    SERVICE_PORT: int = int(os.getenv("PORT", os.getenv("AGENT_SERVICE_PORT", "8006")))
    APP_ENV: str = os.getenv("APP_ENV", "development")

    # Property accessors for backwards compatibility
    @property
    def llm_provider(self) -> str:
        return self.LLM_PROVIDER.lower()

    @property
    def llm_model(self) -> str:
        return self.LLM_MODEL

    @property
    def staged_llm_provider(self) -> str:
        return self.STAGED_LLM_PROVIDER.lower()

    @property
    def staged_llm_model(self) -> str:
        return self.GENAI_STAGED_MODEL

    @property
    def genai_max_attempts(self) -> int:
        return max(1, self.GENAI_MAX_ATTEMPTS)

    @property
    def genai_base_delay(self) -> float:
        return max(0.1, self.GENAI_BASE_DELAY)

    @property
    def genai_rate_limit_per_minute(self) -> int:
        return max(1, self.GENAI_RATE_LIMIT_PER_MINUTE)

    @property
    def genai_rate_limit_window_seconds(self) -> float:
        return max(1.0, self.GENAI_RATE_LIMIT_WINDOW_SECONDS)

    @property
    def genai_rate_limit_concurrency(self) -> int:
        return max(1, self.GENAI_RATE_LIMIT_CONCURRENCY)

    @property
    def user_max_service_url(self) -> str:
        return self.USER_MAX_SERVICE_URL

    @property
    def exercises_service_url(self) -> str:
        return self.EXERCISES_SERVICE_URL

    @property
    def plans_service_url(self) -> str:
        return self.PLANS_SERVICE_URL

    @property
    def workouts_service_url(self) -> str:
        return self.WORKOUTS_SERVICE_URL

    @property
    def crm_service_url(self) -> str:
        return self.CRM_SERVICE_URL

    @property
    def rpe_service_url(self) -> str:
        return self.RPE_SERVICE_URL

    @property
    def agent_database_url(self) -> str:
        return self.AGENT_DATABASE_URL

    @property
    def celery_task_timeout_seconds(self) -> int:
        return max(30, self.CELERY_TASK_TIMEOUT_SECONDS)

    @property
    def internal_gateway_secret(self) -> str:
        return self.INTERNAL_GATEWAY_SECRET

    @property
    def firebase_project_id(self) -> str | None:
        return self.FIREBASE_PROJECT_ID

    @property
    def hf_token(self) -> str | None:
        return self.HF_TOKEN


settings = Settings()


def get_settings() -> Settings:
    return settings
