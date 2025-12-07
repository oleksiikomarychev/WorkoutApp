from datetime import datetime

from pydantic import BaseModel


class WorkoutBase(BaseModel):
    name: str
    notes: str | None = None
    status: str | None = None
    started_at: datetime | None = None
    duration_seconds: int | None = None
    rpe_session: int | None = None
    location: str | None = None
    readiness_score: int | None = None
    applied_plan_id: int | None = None
    plan_order_index: int | None = None
    scheduled_for: datetime | None = None
    completed_at: datetime | None = None


class ExerciseSetCreate(BaseModel):
    weight: float | None = None
    reps: int | None = None
    rpe: float | None = None
    duration_seconds: int | None = None
    distance_meters: float | None = None


class ExerciseInstanceCreate(BaseModel):
    exercise_list_id: int
    sets: list[ExerciseSetCreate] = []
    notes: str | None = None
    user_max_id: int | None = None


class WorkoutCreateWithExercises(WorkoutBase):
    exercise_instances: list[ExerciseInstanceCreate] | None = None


class WorkoutResponse(WorkoutBase):
    id: int


class WorkoutResponseWithExercises(WorkoutBase):
    id: int


class MicrocycleCreate(BaseModel):
    name: str
    order_index: int
    normalization_value: float | None = None
    normalization_unit: str | None = None


class MesocycleCreate(BaseModel):
    name: str
    order_index: int
    microcycles: list[MicrocycleCreate]


class CalendarPlanCreate(BaseModel):
    name: str
    duration_weeks: int
    mesocycles: list[MesocycleCreate]


class DayActivity(BaseModel):
    session_count: int
    volume: float


class SessionLite(BaseModel):
    id: int
    workout_id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: str


class ProfileAggregatesResponse(BaseModel):
    generated_at: datetime
    weeks: int
    total_workouts: int
    total_volume: float
    active_days: int
    max_day_volume: float
    activity_map: dict[str, DayActivity]
    completed_sessions: list[SessionLite]
