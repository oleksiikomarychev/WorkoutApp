from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, constr, model_validator


# ===== Mesocycle Schemas =====
class NormalizationUnit(str, Enum):
    kg = "kg"
    percent = "%"


class NormalizationRule(BaseModel):
    exercise_ids: List[int] = Field(
        default_factory=list,
        description="List of exercise_definition_ids affected by this rule",
    )
    muscle_groups: List[str] = Field(
        default_factory=list,
        description="Optional list of muscle_group strings (case-insensitive) to target",
    )
    target_muscles: List[str] = Field(
        default_factory=list,
        description="Optional list of target muscle identifiers to target",
    )
    value: float = Field(..., description="Normalization adjustment to apply")
    unit: NormalizationUnit = Field(..., description="Normalization unit for this rule")

    @model_validator(mode="after")
    def _normalize_scope(self):
        self.exercise_ids = sorted({int(eid) for eid in self.exercise_ids if isinstance(eid, int)})
        self.muscle_groups = sorted({mg.strip() for mg in self.muscle_groups if isinstance(mg, str) and mg.strip()})
        self.target_muscles = sorted({tm.strip() for tm in self.target_muscles if isinstance(tm, str) and tm.strip()})
        if not (self.exercise_ids or self.muscle_groups or self.target_muscles):
            raise ValueError(
                "NormalizationRule requires at least one scope: exercise_ids, muscle_groups or target_muscles"
            )
        return self


class MesocycleBase(BaseModel):
    name: str = Field(..., max_length=255)
    notes: Optional[constr(max_length=100)] = None
    order_index: int = Field(default=0, ge=0)
    normalization_value: Optional[float] = Field(
        default=None, description="Normalization amount to apply at mesocycle boundary"
    )
    normalization_unit: Optional[NormalizationUnit] = Field(default=None, description="Normalization unit: 'kg' or '%'")
    weeks_count: Optional[int] = Field(default=None, ge=0, description="Number of microcycles in this mesocycle")
    microcycle_length_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=14,
        description="Default days per microcycle for this mesocycle",
    )


class MesocycleCreate(MesocycleBase):
    calendar_plan_id: int


class MesocycleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[constr(max_length=100)] = None
    order_index: Optional[int] = Field(default=None, ge=0)
    normalization_value: Optional[float] = Field(default=None)
    normalization_unit: Optional[NormalizationUnit] = Field(default=None)
    weeks_count: Optional[int] = Field(default=None, ge=0)
    microcycle_length_days: Optional[int] = Field(default=None, ge=1, le=14)


class MesocycleResponse(MesocycleBase):
    id: int
    microcycles: List["MicrocycleResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MicrocycleBase(BaseModel):
    name: str = Field(..., max_length=255)
    notes: Optional[constr(max_length=100)] = None
    order_index: int = Field(default=0, ge=0)
    normalization_value: Optional[float] = Field(
        default=None, description="Normalization amount to apply after this microcycle"
    )
    normalization_unit: Optional[NormalizationUnit] = Field(default=None, description="Normalization unit: 'kg' or '%'")
    days_count: Optional[int] = Field(default=None, ge=1, le=31, description="Length of this microcycle in days")
    normalization_rules: Optional[List[NormalizationRule]] = Field(
        default=None,
        description="Optional per-exercise normalization rules applied at the microcycle boundary",
    )


class MicrocycleUpdate(MicrocycleBase):
    # Schedule is a mapping Day->List[ExerciseScheduleItemDto-like dicts]
    schedule: Optional[Dict[str, List[Dict[str, Any]]]] = None


class MicrocycleResponse(MicrocycleBase):
    id: int
    mesocycle_id: int

    class Config:
        from_attributes = True


class MicrocycleCreate(MicrocycleBase):
    schedule: Optional[Dict[str, List[Dict[str, Any]]]] = None


MesocycleResponse.model_rebuild()
