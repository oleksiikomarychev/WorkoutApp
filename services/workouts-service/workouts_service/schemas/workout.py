from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WorkoutTypeEnum(str, Enum):
    manual = "manual"
    generated = "generated"


class WorkoutBase(BaseModel):
    name: str = Field(..., max_length=255)
    notes: str | None = None
    status: str | None = None
    started_at: datetime | None = None
    duration_seconds: int | None = None
    rpe_session: float | None = None
    location: str | None = None
    readiness_score: int | None = None
    applied_plan_id: int | None = None
    plan_order_index: int | None = None
    scheduled_for: datetime | None = None
    completed_at: datetime | None = None

    workout_type: WorkoutTypeEnum = Field(default="manual")


class WorkoutCreate(WorkoutBase):
    microcycle_id: int | None = None

    class Config:
        extra = "forbid"


class WorkoutUpdate(WorkoutBase):
    name: str | None = Field(None, max_length=255)


class WorkoutSetResponse(BaseModel):
    id: int
    intensity: float | None = None
    effort: float | None = None
    volume: int | None = None
    working_weight: float | None = None
    set_type: str | None = None

    class Config:
        from_attributes = True


class WorkoutExerciseResponse(BaseModel):
    id: int
    exercise_id: int
    sets: list[WorkoutSetResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class WorkoutResponse(WorkoutBase):
    id: int
    name: str
    notes: str | None
    status: str | None
    started_at: datetime | None
    duration_seconds: int | None
    rpe_session: float | None
    location: str | None
    readiness_score: float | None
    applied_plan_id: int | None
    plan_order_index: int | None
    scheduled_for: datetime | None
    completed_at: datetime | None

    workout_type: WorkoutTypeEnum
    exercises: list[WorkoutExerciseResponse]

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}
        extra = "ignore"


class WorkoutSummaryResponse(BaseModel):
    id: int
    name: str
    applied_plan_id: int | None = None
    plan_order_index: int | None = None
    scheduled_for: datetime | None = None
    status: str | None = None
    plan_workout_id: int | None = None
    workout_type: WorkoutTypeEnum = Field(default="manual")

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class WorkoutListResponse(BaseModel):
    id: int
    name: str
    applied_plan_id: int | None = None
    plan_order_index: int | None = None
    scheduled_for: datetime | None = None
    status: str | None = None
    plan_workout_id: int | None = None
    workout_type: WorkoutTypeEnum = Field(default="manual")

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class WorkoutPlanDetailItem(BaseModel):
    id: int
    name: str
    scheduled_for: datetime | None = None
    status: str | None = None
    plan_order_index: int | None = None
    exercise_ids: list[int] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}
