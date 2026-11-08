"""User training input data schemas for agent-service."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserDataInput(BaseModel):
    """Input payload for generating a customized training plan."""

    goals: list[str] = Field(default_factory=list, description="User fitness goals")
    available_equipment: list[str] = Field(default_factory=list, description="Available gym equipment")
    workouts_per_microcycle: int | None = Field(default=None, description="Number of workouts per microcycle/week")
    microcycles_per_mesocycle: int | None = Field(default=None, description="Number of microcycles per mesocycle")
    mesocycles_per_plan: int | None = Field(default=None, description="Number of mesocycles in the plan")
    plan_duration_weeks: int | None = Field(default=None, description="Total plan duration in weeks")
    limits: dict[str, float] | None = Field(default=None, description="User physical limits or restrictions")
    notes: str | None = Field(default=None, description="Additional user notes or preferences")
    current_metrics: dict[str, float] | None = Field(default=None, description="Current strength/body metrics")
    target_metrics: dict[str, float] | None = Field(default=None, description="Target metrics to achieve")
    normalization_unit: str | None = Field(default=None, description="Unit for normalization (e.g. kg, %)")
    normalization_value: float | None = Field(default=None, description="Value for normalization")
