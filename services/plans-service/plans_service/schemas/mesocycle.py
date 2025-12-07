from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, constr, model_validator


class NormalizationUnit(str, Enum):
    kg = "kg"
    percent = "%"


class NormalizationRule(BaseModel):
    exercise_ids: list[int] = Field(
        default_factory=list,
        description="List of exercise_definition_ids affected by this rule",
    )
    muscle_groups: list[str] = Field(
        default_factory=list,
        description="Optional list of muscle_group strings (case-insensitive) to target",
    )
    target_muscles: list[str] = Field(
        default_factory=list,
        description="Optional list of target muscle identifiers to target",
    )
    value: float = Field(..., description="Normalization adjustment to apply")
    unit: NormalizationUnit = Field(..., description="Normalization unit for this rule")

    @model_validator(mode="after")
    def _normalize_scope(self):
        self.exercise_ids = sorted(set(self.exercise_ids))
        self.muscle_groups = sorted({mg.strip() for mg in self.muscle_groups if mg and mg.strip()})
        self.target_muscles = sorted({tm.strip() for tm in self.target_muscles if tm and tm.strip()})
        if not (self.exercise_ids or self.muscle_groups or self.target_muscles):
            raise ValueError(
                "NormalizationRule requires at least one scope: exercise_ids, muscle_groups or target_muscles"
            )
        return self


class MesocycleBase(BaseModel):
    name: str = Field(..., max_length=255)
    notes: constr(max_length=100) | None = None
    order_index: int = Field(default=0, ge=0)
    normalization_value: float | None = Field(
        default=None, description="Normalization amount to apply at mesocycle boundary"
    )
    normalization_unit: NormalizationUnit | None = Field(default=None, description="Normalization unit: 'kg' or '%'")
    weeks_count: int | None = Field(default=None, ge=0, description="Number of microcycles in this mesocycle")
    microcycle_length_days: int | None = Field(
        default=None,
        ge=1,
        le=14,
        description="Default days per microcycle for this mesocycle",
    )


class MesocycleCreate(MesocycleBase):
    calendar_plan_id: int


class MesocycleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    notes: constr(max_length=100) | None = None
    order_index: int | None = Field(default=None, ge=0)
    normalization_value: float | None = Field(default=None)
    normalization_unit: NormalizationUnit | None = Field(default=None)
    weeks_count: int | None = Field(default=None, ge=0)
    microcycle_length_days: int | None = Field(default=None, ge=1, le=14)


class MesocycleResponse(MesocycleBase):
    id: int
    microcycles: list["MicrocycleResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MicrocycleBase(BaseModel):
    name: str = Field(..., max_length=255)
    notes: constr(max_length=100) | None = None
    order_index: int = Field(default=0, ge=0)
    normalization_value: float | None = Field(
        default=None, description="Normalization amount to apply after this microcycle"
    )
    normalization_unit: NormalizationUnit | None = Field(default=None, description="Normalization unit: 'kg' or '%'")
    days_count: int | None = Field(default=None, ge=1, le=31, description="Length of this microcycle in days")
    normalization_rules: list[NormalizationRule] | None = Field(
        default=None,
        description="Optional per-exercise normalization rules applied at the microcycle boundary",
    )


class MicrocycleUpdate(MicrocycleBase):
    schedule: dict[str, list[dict[str, Any]]] | None = None


class MicrocycleResponse(MicrocycleBase):
    id: int
    mesocycle_id: int

    class Config:
        from_attributes = True


class MicrocycleCreate(MicrocycleBase):
    schedule: dict[str, list[dict[str, Any]]] | None = None


MesocycleResponse.model_rebuild()
