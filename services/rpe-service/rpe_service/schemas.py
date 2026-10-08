from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RpeComputeRequest(BaseModel):
    """Request payload for RPE computation."""

    model_config = ConfigDict(extra="ignore")

    intensity: float | None = Field(default=None, ge=1, le=100, description="Интенсивность в процентах от 1ПМ (1-100)")
    effort: float | None = Field(default=None, ge=1, le=10, description="Усилие по шкале RPE (1-10)")
    volume: int | None = Field(default=None, ge=1, description="Количество повторений")

    max_weight: float | None = Field(default=None, ge=0, description="Базовый максимальный вес")
    user_max_id: int | None = Field(default=None, description="ID пользовательского 1ПМ в user-max-service")
    rounding_step: float = Field(default=2.5, gt=0, description="Шаг округления веса")
    rounding_mode: Literal["nearest", "floor", "ceil"] = Field(default="nearest", description="Режим округления")


class ComputationError(BaseModel):
    """Error payload returned when calculation fails."""

    model_config = ConfigDict(extra="ignore")

    error: str
    message: str


class RpeComputeResponse(BaseModel):
    """Response payload containing computed RPE parameters and weight."""

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

