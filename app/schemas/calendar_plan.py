from pydantic import BaseModel, Field, computed_field, validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, Annotated
from app.schemas.user_max import UserMaxResponse
from app.schemas.mesocycle import MesocycleResponse
from app.schemas.schedule_item import ExerciseScheduleItem, ParamsSets



class CalendarPlanBase(BaseModel):
    """Базовая схема календарного плана"""
    name: str = Field(..., max_length=255)
    schedule: Dict[str, List[ExerciseScheduleItem]]
    duration_weeks: int = Field(..., ge=1)

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class CalendarPlanCreate(BaseModel):
    """Схема для создания плана"""
    name: str = Field(..., max_length=255)
    schedule: Dict[str, List[ExerciseScheduleItem]]
    duration_weeks: int = Field(..., ge=1)

class AppliedCalendarPlanBase(BaseModel):
    """Базовая схема примененного плана"""
    start_date: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class AppliedCalendarPlanCreate(AppliedCalendarPlanBase):
    """Схема для создания примененного плана"""
    calendar_plan_id: int  # ID плана, который применяем
    user_maxes: List[int]  # Список ID user_max для этого плана

    @model_validator(mode='before')
    def validate_start_date(cls, values):
        if 'start_date' not in values or values['start_date'] is None:
            values['start_date'] = datetime.utcnow()
        return values

# ===== Apply settings (request) =====
class RoundingMode(str, Enum):
    nearest = "nearest"
    floor = "floor"
    ceil = "ceil"

class ApplyPlanComputeSettings(BaseModel):
    compute_weights: bool = Field(default=True)
    rounding_step: float = Field(default=2.5, gt=0)
    rounding_mode: RoundingMode = Field(default=RoundingMode.nearest)
    generate_workouts: bool = Field(default=True, description="Generate Workout instances linked to the applied plan")
    start_date: Optional[datetime] = Field(default=None, description="Override plan start date")

class ApplyPlanRequest(BaseModel):
    user_max_ids: List[int]
    compute: ApplyPlanComputeSettings = Field(default_factory=ApplyPlanComputeSettings)

class CalendarPlanResponse(CalendarPlanBase):
    """Схема ответа для плана"""
    id: int
    is_active: bool
    mesocycles: List[MesocycleResponse] = []

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class AppliedCalendarPlanResponse(AppliedCalendarPlanBase):
    """Схема ответа для примененного плана"""
    id: int
    calendar_plan_id: int  # ID связанного плана
    end_date: datetime
    calendar_plan: CalendarPlanResponse  # Полный объект плана
    user_maxes: List[UserMaxResponse]  # Полные объекты UserMax
    # Optional: next workout summary for active plans
    
    class NextWorkoutSummary(BaseModel):
        id: int
        name: str
        scheduled_for: Optional[datetime] = None
        plan_order_index: Optional[int] = None

    next_workout: Optional[NextWorkoutSummary] = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

# ===== Instances (editable copies) =====
class ParamsSetsInstance(ParamsSets):
    id: int

class ExerciseScheduleItemInstance(BaseModel):
    id: int
    exercise_id: int
    sets: List[ParamsSetsInstance]

class CalendarPlanInstanceBase(BaseModel):
    name: str
    schedule: Dict[str, List[ExerciseScheduleItemInstance]]
    duration_weeks: int = Field(..., ge=1)

class CalendarPlanInstanceCreate(BaseModel):
    source_plan_id: Optional[int] = None
    name: str
    schedule: Dict[str, List[ExerciseScheduleItemInstance]]
    duration_weeks: int = Field(..., ge=1)

class CalendarPlanInstanceUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[Dict[str, List[ExerciseScheduleItemInstance]]] = None
    duration_weeks: Optional[int] = Field(default=None, ge=1)

class CalendarPlanInstanceResponse(CalendarPlanInstanceBase):
    id: int
    source_plan_id: Optional[int]

    class Config:
        from_attributes = True
