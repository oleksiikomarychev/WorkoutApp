from pydantic import BaseModel, Field, model_validator, validator, field_validator
from typing import Optional, List, Dict, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from .mesocycle import MesocycleResponse
from .schedule_item import ExerciseScheduleItem
from .workout_schemas import WorkoutExerciseCreate


if TYPE_CHECKING:
    from .mesocycle import MesocycleResponse


class UserMaxResponse(BaseModel):
    id: int
    exercise_id: int
    max_weight: float
    rep_max: int

    class Config:
        from_attributes = True


class CalendarPlanBase(BaseModel):
    """Базовая схема календарного плана"""

    name: str = Field(..., max_length=255, description="Plan name must be 1-255 characters")
    #duration_weeks: int = Field(..., ge=1, le=104, description="Duration must be between 1 and 104 weeks")

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class MicrocycleBase(BaseModel):
    name: str
    days_count: int
    order_index: Optional[int] = Field(default=None, ge=0)
    normalization_value: Optional[float] = None
    normalization_unit: Optional[str] = None


# ===== Plan Schemas =====
class PlanWorkoutBase(BaseModel):
    day_label: str = Field(..., max_length=50, description="Day label, e.g., 'Day 1'")
    order_index: int = Field(default=0, ge=0)

class PlanWorkoutCreate(PlanWorkoutBase):
    exercises: List[WorkoutExerciseCreate] = Field(default_factory=list)

class PlanWorkoutResponse(PlanWorkoutBase):
    id: int
    microcycle_id: int
    exercises: List["PlanExerciseResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PlanExerciseBase(BaseModel):
    exercise_definition_id: int
    order_index: int = Field(default=0, ge=0)

class PlanExerciseCreate(PlanExerciseBase):
    pass

class PlanExerciseResponse(PlanExerciseBase):
    id: int
    plan_workout_id: Optional[int] = None  # Make optional
    exercise_name: str  # Add this field for exercise names
    sets: List["PlanSetResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PlanSetBase(BaseModel):
    order_index: Optional[int] = Field(default=None, ge=0)  # Make optional
    intensity: Optional[int] = Field(default=None, ge=0, le=100)
    effort: Optional[int] = Field(default=None, ge=1, le=10)
    volume: Optional[int] = Field(default=None, ge=1)
    working_weight: Optional[float] = Field(default=None, exclude=True)

class PlanSetCreate(PlanSetBase):
    pass

class PlanSetResponse(PlanSetBase):
    id: int
    plan_exercise_id: Optional[int] = None  # Make optional

    class Config:
        from_attributes = True


# Forward references
PlanWorkoutResponse.model_rebuild()
PlanExerciseResponse.model_rebuild()


class MicrocycleCreate(MicrocycleBase):
    normalization_value: Optional[float] = None
    normalization_unit: Optional[str] = None
    plan_workouts: List[PlanWorkoutCreate] = Field(default_factory=list)

    @model_validator(mode='after')
    def generate_day_labels(self):
        """Auto-generate day labels based on days_count"""
        if not self.plan_workouts or self.days_count is None:
            return self
        
        # Generate day labels: Day 1, Day 2, etc.
        day_labels = [f"Day {i+1}" for i in range(self.days_count)]
        
        # Create new plan_workouts with generated labels
        new_workouts = []
        for i, label in enumerate(day_labels):
            # Only include days with workouts
            if i < len(self.plan_workouts):
                workout = self.plan_workouts[i]
                workout.day_label = label
                new_workouts.append(workout)
        self.plan_workouts = new_workouts
        return self


class MicrocycleResponse(BaseModel):
    id: int
    mesocycle_id: int
    name: str = Field(default="")
    notes: Optional[str] = None
    order_index: int = Field(default=0, ge=0)
    normalization_value: Optional[float] = None
    normalization_unit: Optional[str] = None
    days_count: Optional[int] = Field(default=None, ge=1, le=31)
    plan_workouts: List["PlanWorkoutResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MesocycleCreate(BaseModel):
    name: str
    order_index: Optional[int] = Field(default=None, ge=0)
    microcycles: List[MicrocycleCreate]
    duration_weeks: int


class MesocycleResponse(BaseModel):
    id: int
    name: str
    notes: Optional[str] = None
    order_index: int
    weeks_count: Optional[int] = None
    microcycle_length_days: Optional[int] = None
    microcycles: Optional[List[MicrocycleResponse]] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CalendarPlanCreate(CalendarPlanBase):
    """Схема для создания плана"""

    mesocycles: List[MesocycleCreate] = Field(..., description="List of mesocycles in this plan")
    duration_weeks: int = Field(..., ge=1, le=104, description="Duration must be between 1 and 104 weeks")


class CalendarPlanVariantCreate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255, description="Optional name for the plan variant")


class CalendarPlanUpdate(BaseModel):
    """Схема для частичного обновления плана"""

    name: Optional[str] = Field(None, max_length=255, description="Plan name must be 1-255 characters")
    duration_weeks: Optional[int] = Field(default=None, ge=1, le=104, description="Duration must be between 1 and 104 weeks")


class AppliedCalendarPlanBase(BaseModel):
    """Базовая схема примененного плана"""

    start_date: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedCalendarPlanCreate(AppliedCalendarPlanBase):
    """Схема для создания примененного плана"""

    calendar_plan_id: int  # ID плана, который применяем
    user_max_ids: List[int]

    @model_validator(mode="before")
    def validate_start_date(cls, values):
        if "start_date" not in values or values["start_date"] is None:
            values["start_date"] = datetime.now()
        return values


# ===== Apply settings (request) =====
class RoundingMode(str, Enum):
    nearest = "nearest"
    floor = "floor"
    ceil = "ceil"


class ApplyPlanComputeSettings(BaseModel):
    compute_weights: bool
    rounding_step: float
    rounding_mode: RoundingMode = Field(default=RoundingMode.nearest)
    generate_workouts: bool = Field(default=True, description="Automatically generate workouts when applying plan")
    start_date: Optional[datetime] = Field(default=None, description="Start date for the plan")


class CalendarPlanSummaryResponse(BaseModel):
    """Облегченная схема ответа для списка планов"""

    id: int
    name: str
    duration_weeks: int
    is_active: bool
    is_favorite: bool = False
    root_plan_id: int
    is_original: bool = True

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class CalendarPlanNameOnly(BaseModel):
    """Минимальная схема только с идентификатором и названием плана
    Используется внутри AppliedCalendarPlanSummaryResponse для сокращения payload.
    """

    id: int
    name: str

    class Config:
        from_attributes = True


class CalendarPlanResponse(BaseModel):
    """Схема ответа для плана"""

    id: int
    name: str
    duration_weeks: int
    is_active: bool
    root_plan_id: int
    is_original: bool = True
    mesocycles: Optional[List[MesocycleResponse]] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedCalendarPlanSummaryResponse(AppliedCalendarPlanBase):
    """Облегченная схема ответа для списка примененных планов"""

    id: int
    calendar_plan_id: int
    end_date: datetime
    calendar_plan: CalendarPlanNameOnly  # Минимальная схема плана (id, name)

    class NextWorkoutSummary(BaseModel):
        id: int
        name: str
        scheduled_for: Optional[datetime] = None
        plan_order_index: Optional[int] = None

    next_workout: Optional[NextWorkoutSummary] = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedPlanWorkoutResponse(BaseModel):
    """Схема ответа для тренировки в примененном плане"""
    
    id: int
    workout_id: int
    order_index: int
    
    class Config:
        from_attributes = True


class AppliedCalendarPlanResponse(AppliedCalendarPlanBase):
    """Схема ответа для примененного плана"""

    id: int
    calendar_plan_id: int  # ID связанного плана
    end_date: datetime
    calendar_plan: CalendarPlanResponse  # Полный объект плана
    workouts: List[AppliedPlanWorkoutResponse] = Field(default_factory=list)
    # Include selected user maxes attached to the applied plan
    user_maxes: List[UserMaxResponse] = Field(default_factory=list)
    # Optional: next workout summary for active plans

    class NextWorkoutSummary(BaseModel):
        id: int
        name: str
        scheduled_for: Optional[datetime] = None
        plan_order_index: Optional[int] = None

    next_workout: Optional[NextWorkoutSummary] = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedWorkout(BaseModel):
    """Schema for workouts in applied plans"""
    id: int
    order_index: int
    is_current: bool


class AppliedMicrocycle(BaseModel):
    """Schema for microcycles in applied plans"""
    id: int
    name: str
    order_index: int
    workouts: List[AppliedWorkout]


class AppliedMesocycle(BaseModel):
    """Schema for mesocycles in applied plans"""
    id: int
    name: str
    order_index: int
    microcycles: List[AppliedMicrocycle]


# ===== Instances (editable copies) =====
class ParamsSetsInstance(BaseModel):
    id: int


class ExerciseSet(BaseModel):
    intensity: int
    effort: float
    volume: int


class ExerciseScheduleItemInstance(BaseModel):
    id: int
    exercise_id: int
    sets: List[ParamsSetsInstance]


class WorkoutCreate(BaseModel):
    name: str
    parameters: Optional[dict] = Field(default_factory=dict)  # Make optional with default empty dict


class MesocycleCreate(BaseModel):
    name: str
    duration_weeks: int
    microcycles: List[MicrocycleCreate]


class FullCalendarPlanCreate(BaseModel):
    name: str
    mesocycles: List[MesocycleCreate]
    duration_weeks: int
