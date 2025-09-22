from typing import List, Dict, Optional
from pydantic import BaseModel, Field, constr, model_validator
from enum import Enum

# ===== Mesocycle Schemas =====
class NormalizationUnit(str, Enum):
    kg = "kg"
    percent = "%"


class MesocycleBase(BaseModel):
    name: str = Field(..., max_length=255)
    notes: Optional[constr(max_length=100)] = None
    order_index: int = Field(default=0, ge=0)
    normalization_value: Optional[float] = Field(
        default=None, description="Normalization amount to apply at mesocycle boundary"
    )
    normalization_unit: Optional[NormalizationUnit] = Field(
        default=None, description="Normalization unit: 'kg' or '%'"
    )
    weeks_count: Optional[int] = Field(
        default=None, ge=0, description="Number of microcycles in this mesocycle"
    )
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
    normalization_value: Optional[float] = Field(default=None, description="Normalization amount to apply after this microcycle")
    normalization_unit: Optional[NormalizationUnit] = Field(default=None, description="Normalization unit: 'kg' or '%'")
    days_count: Optional[int] = Field(default=None, ge=1, le=31, description="Length of this microcycle in days")


class MicrocycleUpdate(MicrocycleBase):
    pass


class MicrocycleResponse(MicrocycleBase):
    id: int
    mesocycle_id: int

    class Config:
        from_attributes = True


class MicrocycleCreate(MicrocycleBase):
    pass


MesocycleResponse.model_rebuild()
