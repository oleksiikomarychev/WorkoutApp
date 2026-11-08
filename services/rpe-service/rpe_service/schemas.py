"""Pydantic schemas for RPE calculation service."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RpeComputeRequest(BaseModel):
    """Request payload for RPE computation."""

    model_config = ConfigDict(extra="ignore")

    intensity: float | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Интенсивность в процентах от 1ПМ (1-100)",
    )
    effort: float | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Усилие по шкале RPE (1-10)",
    )
    volume: int | None = Field(
        default=None,
        ge=1,
        description="Количество повторений",
    )
    max_weight: float | None = Field(
        default=None,
        ge=0,
        description="Базовый максимальный вес",
    )
    user_max_id: int | None = Field(
        default=None,
        description="ID пользовательского 1ПМ в user-max-service",
    )
    rounding_step: float = Field(
        default=2.5,
        gt=0,
        description="Шаг округления веса",
    )
    rounding_mode: Literal["nearest", "floor", "ceil"] = Field(
        default="nearest",
        description="Режим округления: 'nearest', 'floor', или 'ceil'",
    )

    @field_validator("intensity", "effort", "max_weight", "user_max_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, value: Any) -> Any:
        """Convert empty or whitespace-only strings to None for optional numeric parameters."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return None if not stripped else stripped
        return value

    @field_validator("volume", mode="before")
    @classmethod
    def coerce_volume(cls, value: Any) -> Any:
        """Coerce float or numeric string volume to integer count."""
        if value is None or value == "":
            return None
        if isinstance(value, float):
            return int(round(value))
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                return int(round(float(stripped)))
            except ValueError:
                return value
        return value

    @field_validator("rounding_mode", mode="before")
    @classmethod
    def normalize_rounding_mode(cls, value: Any) -> Any:
        """Allow case-insensitive, whitespace-padded, or empty rounding mode strings."""
        if value is None:
            return "nearest"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return "nearest"
            if normalized in ("nearest", "floor", "ceil"):
                return normalized
        return value


class ComputationError(BaseModel):
    """Error payload returned when calculation fails."""

    model_config = ConfigDict(extra="ignore")

    error: str
    message: str


class RpeComputeResponse(BaseModel):
    """Response payload containing computed RPE parameters and target weight."""

    model_config = ConfigDict(extra="ignore")

    intensity: int | None = None
    effort: float | None = None
    volume: int | None = None
    weight: float | None = None


class InternalPurgeResponse(BaseModel):
    """Response payload for internal user purge endpoint."""

    model_config = ConfigDict(extra="ignore")

    status: str = "ok"
    deleted: int = 0


class PlanNotificationRequest(BaseModel):
    """Payload received when another service notifies of a created training plan."""

    model_config = ConfigDict(extra="allow")

    plan: dict[str, Any] | None = None


class PlanNotificationResponse(BaseModel):
    """Response payload for plan notification endpoint."""

    model_config = ConfigDict(extra="ignore")

    status: str = "ok"
    message: str = "Training plan notification received"
