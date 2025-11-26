from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .mesocycle import MesocycleResponse, NormalizationRule
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
    # duration_weeks: int = Field(..., ge=1, le=104, description="Duration must be between 1 and 104 weeks")
    primary_goal: Optional[str] = Field(
        default=None,
        description="Primary goal of the plan (e.g. strength, hypertrophy, recomposition)",
    )
    intended_experience_level: Optional[str] = Field(
        default=None, description="Intended lifter level (novice/intermediate/advanced)"
    )
    intended_frequency_per_week: Optional[int] = Field(
        default=None, ge=1, le=14, description="Intended training frequency per week"
    )
    session_duration_target_min: Optional[int] = Field(
        default=None, ge=1, le=300, description="Target session duration in minutes"
    )
    primary_focus_lifts: Optional[List[int]] = Field(
        default=None, description="List of primary focus exercise_definition_ids"
    )
    required_equipment: Optional[List[str]] = Field(
        default=None, description="List of required equipment tags (e.g. barbell, rack, bench)"
    )
    supported_constraints: Optional[List[str]] = Field(
        default=None,
        description="List of supported constraint codes (e.g. shoulder_overhead_limit)",
    )

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class MicrocycleBase(BaseModel):
    name: str
    days_count: int
    order_index: Optional[int] = Field(default=None, ge=0)
    normalization_value: Optional[float] = None
    normalization_unit: Optional[str] = None
    normalization_rules: Optional[List[NormalizationRule]] = Field(default=None)


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
    intensity: Optional[int] = Field(default=None, ge=0, le=110)
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

    @model_validator(mode="after")
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
    normalization_rules: Optional[List[NormalizationRule]] = Field(default=None)
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
    duration_weeks: Optional[int] = Field(
        default=None, ge=1, le=104, description="Duration must be between 1 and 104 weeks"
    )
    primary_goal: Optional[str] = None
    intended_experience_level: Optional[str] = None
    intended_frequency_per_week: Optional[int] = Field(default=None, ge=1, le=14)
    session_duration_target_min: Optional[int] = Field(default=None, ge=1, le=300)
    primary_focus_lifts: Optional[List[int]] = None
    required_equipment: Optional[List[str]] = None
    supported_constraints: Optional[List[str]] = None


class AppliedCalendarPlanBase(BaseModel):
    """Базовая схема примененного плана"""

    start_date: Optional[datetime] = None
    is_active: bool = True
    status: Optional[str] = Field(default=None, description="User plan status: active/completed/dropped/etc.")
    planned_sessions_total: Optional[int] = Field(default=None, ge=0)
    actual_sessions_completed: Optional[int] = Field(default=None, ge=0)
    adherence_pct: Optional[float] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=512)
    dropout_reason: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Dropout reason code or short description (e.g. injury/no_time/too_hard)",
    )
    dropped_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when plan was considered dropped",
    )

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
    primary_goal: Optional[str] = None
    intended_experience_level: Optional[str] = None
    intended_frequency_per_week: Optional[int] = None
    session_duration_target_min: Optional[int] = None

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
    primary_goal: Optional[str] = None
    intended_experience_level: Optional[str] = None
    intended_frequency_per_week: Optional[int] = None
    session_duration_target_min: Optional[int] = None
    primary_focus_lifts: Optional[List[int]] = None
    required_equipment: Optional[List[str]] = None
    supported_constraints: Optional[List[str]] = None
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


class PlanExerciseFilter(BaseModel):
    """Фильтры для выборки упражнений в плане для mass edit/replace"""

    exercise_name_exact: Optional[str] = None
    exercise_name_contains: Optional[str] = None

    intensity_lt: Optional[int] = Field(default=None, ge=0, le=110)
    intensity_lte: Optional[int] = Field(default=None, ge=0, le=110)
    intensity_gt: Optional[int] = Field(default=None, ge=0, le=110)
    intensity_gte: Optional[int] = Field(default=None, ge=0, le=110)

    volume_lt: Optional[int] = Field(default=None, ge=1)
    volume_gt: Optional[int] = Field(default=None, ge=1)

    mesocycle_indices: Optional[List[int]] = None
    microcycle_indices: Optional[List[int]] = None
    workout_day_labels: Optional[List[str]] = None


class PlanExerciseActions(BaseModel):
    """Действия, которые нужно применить к выбранным упражнениям/сетам"""

    set_intensity: Optional[int] = Field(default=None, ge=0, le=110)
    increase_intensity_by: Optional[int] = None
    decrease_intensity_by: Optional[int] = None

    set_volume: Optional[int] = Field(default=None, ge=1)
    increase_volume_by: Optional[int] = None
    decrease_volume_by: Optional[int] = None

    replace_exercise_definition_id_to: Optional[int] = None
    replace_exercise_name_to: Optional[str] = None


class PlanMassEditCommand(BaseModel):
    """Команда для mass edit/replace упражнений в плане (используется ЛЛМ)"""

    operation: Literal["mass_edit", "replace_exercises"]
    mode: Literal["preview", "apply"] = "preview"
    filter: PlanExerciseFilter
    actions: PlanExerciseActions
