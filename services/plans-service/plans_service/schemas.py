from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class CalendarPlanCreate(BaseModel):
    name: str = Field(..., max_length=255)
    schedule: Dict[str, Any]
    duration_weeks: int = Field(..., ge=1)


class CalendarPlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    schedule: Optional[Dict[str, Any]] = None
    duration_weeks: Optional[int] = Field(default=None, ge=1)


class CalendarPlanResponse(BaseModel):
    id: int
    name: str
    schedule: Dict[str, Any]
    duration_weeks: int
    is_active: bool
    is_favorite: bool

    class Config:
        from_attributes = True


class AppliedCalendarPlanResponse(BaseModel):
    id: int
    calendar_plan_id: int
    start_date: str
    end_date: str
    is_active: bool
    user_max_ids: List[int]

    class Config:
        from_attributes = True


# ===== Phase 2: Instances and Apply request =====

class ApplyPlanComputeSettings(BaseModel):
    compute_weights: bool = Field(default=True)
    rounding_step: float = Field(default=2.5, gt=0)
    rounding_mode: str = Field(default="nearest")  # nearest|floor|ceil
    generate_workouts: bool = Field(default=True)
    start_date: Optional[str] = Field(default=None, description="ISO date override")


class ApplyPlanRequest(BaseModel):
    user_max_ids: List[int]
    compute: ApplyPlanComputeSettings = Field(default_factory=ApplyPlanComputeSettings)


class CalendarPlanInstanceCreate(BaseModel):
    source_plan_id: Optional[int] = None
    name: str = Field(..., max_length=255)
    schedule: Dict[str, Any]
    duration_weeks: int = Field(..., ge=1)


class CalendarPlanInstanceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    schedule: Optional[Dict[str, Any]] = None
    duration_weeks: Optional[int] = Field(default=None, ge=1)


class CalendarPlanInstanceResponse(BaseModel):
    id: int
    source_plan_id: Optional[int]
    name: str
    schedule: Dict[str, Any]
    duration_weeks: int

    class Config:
        from_attributes = True
