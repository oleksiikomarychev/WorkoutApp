from typing import Literal

from pydantic import BaseModel, Field


class RpeComputeRequest(BaseModel):
    intensity: int | None = Field(default=None, ge=1, le=100)
    effort: int | None = Field(default=None, ge=1, le=10)
    volume: int | None = Field(default=None, ge=1)

    max_weight: float | None = Field(default=None, ge=0)
    user_max_id: int | None = Field(default=None, description="ID пользовательского 1ПМ в user-max-service")
    rounding_step: float = Field(default=2.5, gt=0)
    rounding_mode: Literal["nearest", "floor", "ceil"] = Field(default="nearest")


class ComputationError(BaseModel):
    error: str
    message: str


class RpeComputeResponse(BaseModel):
    intensity: int | None = None
    effort: int | None = None
    volume: int | None = None
    weight: int | None = None
