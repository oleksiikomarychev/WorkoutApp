from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Literal

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
    name: str = Field(..., max_length=255, description="Plan name must be 1-255 characters")

    is_public: bool = Field(default=False, description="Whether the plan template is public")

    primary_goal: str | None = Field(
        default=None,
        description="Primary goal of the plan (e.g. strength, hypertrophy, recomposition)",
    )
    intended_experience_level: str | None = Field(
        default=None, description="Intended lifter level (novice/intermediate/advanced)"
    )
    intended_frequency_per_week: int | None = Field(
        default=None, ge=1, le=14, description="Intended training frequency per week"
    )
    session_duration_target_min: int | None = Field(
        default=None, ge=1, le=300, description="Target session duration in minutes"
    )
    primary_focus_lifts: list[int] | None = Field(
        default=None, description="List of primary focus exercise_definition_ids"
    )
    required_equipment: list[str] | None = Field(
        default=None, description="List of required equipment tags (e.g. barbell, rack, bench)"
    )
    supported_constraints: list[str] | None = Field(
        default=None,
        description="List of supported constraint codes (e.g. shoulder_overhead_limit)",
    )

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class MicrocycleBase(BaseModel):
    name: str
    days_count: int
    order_index: int | None = Field(default=None, ge=0)
    normalization_value: float | None = None
    normalization_unit: str | None = None
    normalization_rules: list[NormalizationRule] | None = Field(default=None)


class PlanWorkoutBase(BaseModel):
    day_label: str = Field(..., max_length=50, description="Day label, e.g., 'Day 1'")
    order_index: int = Field(default=0, ge=0)


class PlanWorkoutCreate(PlanWorkoutBase):
    exercises: list[WorkoutExerciseCreate] = Field(default_factory=list)


class PlanWorkoutResponse(PlanWorkoutBase):
    id: int
    microcycle_id: int
    exercises: list["PlanExerciseResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PlanExerciseBase(BaseModel):
    exercise_definition_id: int
    order_index: int = Field(default=0, ge=0)


class PlanExerciseCreate(PlanExerciseBase):
    pass


class PlanExerciseResponse(PlanExerciseBase):
    id: int
    plan_workout_id: int | None = None
    exercise_name: str
    sets: list["PlanSetResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PlanSetBase(BaseModel):
    order_index: int | None = Field(default=None, ge=0)
    intensity: int | None = Field(default=None, ge=0, le=110)
    effort: int | None = Field(default=None, ge=1, le=10)
    volume: int | None = Field(default=None, ge=1)
    working_weight: float | None = Field(default=None, exclude=True)


class PlanSetCreate(PlanSetBase):
    pass


class PlanSetResponse(PlanSetBase):
    id: int
    plan_exercise_id: int | None = None

    class Config:
        from_attributes = True


PlanWorkoutResponse.model_rebuild()
PlanExerciseResponse.model_rebuild()


class MicrocycleCreate(MicrocycleBase):
    normalization_value: float | None = None
    normalization_unit: str | None = None
    plan_workouts: list[PlanWorkoutCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def generate_day_labels(self):
        if not self.plan_workouts or self.days_count is None:
            return self

        day_labels = [f"Day {i+1}" for i in range(self.days_count)]

        new_workouts = []
        for i, label in enumerate(day_labels):
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
    notes: str | None = None
    order_index: int = Field(default=0, ge=0)
    normalization_value: float | None = None
    normalization_unit: str | None = None
    days_count: int | None = Field(default=None, ge=1, le=31)
    normalization_rules: list[NormalizationRule] | None = Field(default=None)
    plan_workouts: list["PlanWorkoutResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MesocycleCreate(BaseModel):
    name: str
    order_index: int | None = Field(default=None, ge=0)
    microcycles: list[MicrocycleCreate]
    duration_weeks: int


class MesocycleResponse(BaseModel):
    id: int
    name: str
    notes: str | None = None
    order_index: int
    weeks_count: int | None = None
    microcycle_length_days: int | None = None
    microcycles: list[MicrocycleResponse] | None = Field(default_factory=list)

    class Config:
        from_attributes = True


class CalendarPlanCreate(CalendarPlanBase):
    mesocycles: list[MesocycleCreate] = Field(..., description="List of mesocycles in this plan")
    duration_weeks: int = Field(..., ge=1, le=104, description="Duration must be between 1 and 104 weeks")


class CalendarPlanVariantCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255, description="Optional name for the plan variant")


class CalendarPlanUpdate(BaseModel):
    name: str | None = Field(None, max_length=255, description="Plan name must be 1-255 characters")
    duration_weeks: int | None = Field(
        default=None, ge=1, le=104, description="Duration must be between 1 and 104 weeks"
    )
    primary_goal: str | None = None
    intended_experience_level: str | None = None
    intended_frequency_per_week: int | None = Field(default=None, ge=1, le=14)
    session_duration_target_min: int | None = Field(default=None, ge=1, le=300)
    primary_focus_lifts: list[int] | None = None
    required_equipment: list[str] | None = None
    supported_constraints: list[str] | None = None

    is_public: bool | None = None


class AppliedCalendarPlanBase(BaseModel):
    start_date: datetime | None = None
    is_active: bool = True
    status: str | None = Field(default=None, description="User plan status: active/completed/dropped/etc.")
    planned_sessions_total: int | None = Field(default=None, ge=0)
    actual_sessions_completed: int | None = Field(default=None, ge=0)
    adherence_pct: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=512)
    dropout_reason: str | None = Field(
        default=None,
        max_length=64,
        description="Dropout reason code or short description (e.g. injury/no_time/too_hard)",
    )
    dropped_at: datetime | None = Field(
        default=None,
        description="Timestamp when plan was considered dropped",
    )

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedCalendarPlanCreate(AppliedCalendarPlanBase):
    calendar_plan_id: int
    user_max_ids: list[int]

    @model_validator(mode="before")
    def validate_start_date(cls, values):
        if "start_date" not in values or values["start_date"] is None:
            values["start_date"] = datetime.now()
        return values


class RoundingMode(str, Enum):
    nearest = "nearest"
    floor = "floor"
    ceil = "ceil"


class ApplyPlanComputeSettings(BaseModel):
    compute_weights: bool
    rounding_step: float
    rounding_mode: RoundingMode = Field(default=RoundingMode.nearest)
    generate_workouts: bool = Field(default=True, description="Automatically generate workouts when applying plan")
    start_date: datetime | None = Field(default=None, description="Start date for the plan")


class CalendarPlanSummaryResponse(BaseModel):
    id: int
    name: str
    duration_weeks: int
    is_active: bool
    is_favorite: bool = False
    root_plan_id: int
    is_original: bool = True
    is_public: bool = False
    primary_goal: str | None = None
    intended_experience_level: str | None = None
    intended_frequency_per_week: int | None = None
    session_duration_target_min: int | None = None

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class CalendarPlanNameOnly(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CalendarPlanResponse(BaseModel):
    id: int
    name: str
    duration_weeks: int
    is_active: bool
    root_plan_id: int
    is_original: bool = True
    is_public: bool = False
    primary_goal: str | None = None
    intended_experience_level: str | None = None
    intended_frequency_per_week: int | None = None
    session_duration_target_min: int | None = None
    primary_focus_lifts: list[int] | None = None
    required_equipment: list[str] | None = None
    supported_constraints: list[str] | None = None
    mesocycles: list[MesocycleResponse] | None = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedCalendarPlanSummaryResponse(AppliedCalendarPlanBase):
    id: int
    calendar_plan_id: int
    end_date: datetime
    calendar_plan: CalendarPlanNameOnly

    class NextWorkoutSummary(BaseModel):
        id: int
        name: str
        scheduled_for: datetime | None = None
        plan_order_index: int | None = None

    next_workout: NextWorkoutSummary | None = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedPlanWorkoutResponse(BaseModel):
    id: int
    workout_id: int
    order_index: int

    class Config:
        from_attributes = True


class AppliedCalendarPlanResponse(AppliedCalendarPlanBase):
    id: int
    calendar_plan_id: int
    end_date: datetime
    calendar_plan: CalendarPlanResponse
    workouts: list[AppliedPlanWorkoutResponse] = Field(default_factory=list)

    user_maxes: list[UserMaxResponse] = Field(default_factory=list)

    class NextWorkoutSummary(BaseModel):
        id: int
        name: str
        scheduled_for: datetime | None = None
        plan_order_index: int | None = None

    next_workout: NextWorkoutSummary | None = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedWorkout(BaseModel):
    id: int
    order_index: int
    is_current: bool


class AppliedMicrocycle(BaseModel):
    id: int
    name: str
    order_index: int
    workouts: list[AppliedWorkout]


class AppliedMesocycle(BaseModel):
    id: int
    name: str
    order_index: int
    microcycles: list[AppliedMicrocycle]


class ParamsSetsInstance(BaseModel):
    id: int


class ExerciseSet(BaseModel):
    intensity: int
    effort: float
    volume: int


class ExerciseScheduleItemInstance(BaseModel):
    id: int
    exercise_id: int
    sets: list[ParamsSetsInstance]


class WorkoutCreate(BaseModel):
    name: str
    parameters: dict | None = Field(default_factory=dict)


class MesocycleCreate(BaseModel):
    name: str
    duration_weeks: int
    microcycles: list[MicrocycleCreate]


class FullCalendarPlanCreate(BaseModel):
    name: str
    mesocycles: list[MesocycleCreate]
    duration_weeks: int


class PlanExerciseFilter(BaseModel):
    exercise_name_exact: str | None = None
    exercise_name_contains: str | None = None

    intensity_lt: int | None = Field(default=None, ge=0, le=110)
    intensity_lte: int | None = Field(default=None, ge=0, le=110)
    intensity_gt: int | None = Field(default=None, ge=0, le=110)
    intensity_gte: int | None = Field(default=None, ge=0, le=110)

    volume_lt: int | None = Field(default=None, ge=1)
    volume_gt: int | None = Field(default=None, ge=1)

    mesocycle_indices: list[int] | None = None
    microcycle_indices: list[int] | None = None
    workout_day_labels: list[str] | None = None


class PlanExerciseActions(BaseModel):
    set_intensity: int | None = Field(default=None, ge=0, le=110)
    increase_intensity_by: int | None = None
    decrease_intensity_by: int | None = None

    set_volume: int | None = Field(default=None, ge=1)
    increase_volume_by: int | None = None
    decrease_volume_by: int | None = None

    replace_exercise_definition_id_to: int | None = None
    replace_exercise_name_to: str | None = None


class PlanMassEditCommand(BaseModel):
    operation: Literal["mass_edit", "replace_exercises"]
    mode: Literal["preview", "apply"] = "preview"
    filter: PlanExerciseFilter
    actions: PlanExerciseActions
