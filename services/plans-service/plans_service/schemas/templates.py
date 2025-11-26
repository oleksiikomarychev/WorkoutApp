from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, constr


class MicrocycleTemplateDto(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., max_length=255)
    notes: Optional[constr(max_length=255)] = None
    order_index: int = Field(default=0, ge=0)
    days_count: Optional[int] = Field(default=None, ge=1, le=31)
    schedule: Optional[Dict[str, List[Dict[str, Any]]]] = None

    class Config:
        from_attributes = True


class PlacementMode(str):
    Insert_After_Mesocycle = "Insert_After_Mesocycle"
    Insert_After_Workout = "Insert_After_Workout"
    Append_To_End = "Append_To_End"


class ConflictPolicy(str):
    Shift_Forward = "Shift_Forward"
    Replace_Planned = "Replace_Planned"
    Skip_On_Conflict = "Skip_On_Conflict"


class PlacementDto(BaseModel):
    mode: str = Field(
        ...,
        description="Placement mode: Insert_After_Mesocycle | Insert_After_Workout | Append_To_End",
    )
    mesocycle_index: Optional[int] = Field(default=None, ge=1)
    workout_id: Optional[int] = Field(default=None, ge=1)


class InstantiateFromTemplateRequest(BaseModel):
    template_id: int
    placement: PlacementDto
    on_conflict: str = Field(default=ConflictPolicy.Shift_Forward)


class InstantiateFromExistingRequest(BaseModel):
    source_mesocycle_id: int
    placement: PlacementDto
    on_conflict: str = Field(default=ConflictPolicy.Shift_Forward)


class MesocycleTemplateCreate(BaseModel):
    name: str = Field(..., max_length=255)
    notes: Optional[constr(max_length=255)] = None
    weeks_count: Optional[int] = Field(default=None, ge=0)
    microcycle_length_days: Optional[int] = Field(default=None, ge=1, le=14)
    normalization_value: Optional[float] = Field(default=None)
    normalization_unit: Optional[str] = Field(default=None)
    is_public: bool = Field(default=False)
    microcycles: List[MicrocycleTemplateDto] = Field(default_factory=list)


class MesocycleTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[constr(max_length=255)] = None
    weeks_count: Optional[int] = Field(default=None, ge=0)
    microcycle_length_days: Optional[int] = Field(default=None, ge=1, le=14)
    normalization_value: Optional[float] = Field(default=None)
    normalization_unit: Optional[str] = Field(default=None)
    is_public: Optional[bool] = None
    microcycles: Optional[List[MicrocycleTemplateDto]] = None


class MesocycleTemplateResponse(BaseModel):
    id: int
    user_id: str
    name: str
    notes: Optional[str]
    weeks_count: Optional[int]
    microcycle_length_days: Optional[int]
    normalization_value: Optional[float]
    normalization_unit: Optional[str]
    is_public: bool
    microcycles: List[MicrocycleTemplateDto] = Field(default_factory=list)

    class Config:
        from_attributes = True
