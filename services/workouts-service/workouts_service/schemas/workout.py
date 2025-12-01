from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# Define enum for schemas
class WorkoutTypeEnum(str, Enum):
    manual = "manual"
    generated = "generated"


class WorkoutBase(BaseModel):
    name: str = Field(..., max_length=255)
    notes: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    rpe_session: Optional[float] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    # Add workout type classification
    workout_type: WorkoutTypeEnum = Field(default="manual")


class WorkoutCreate(WorkoutBase):
    microcycle_id: Optional[int] = None

    class Config:
        extra = "forbid"


class WorkoutUpdate(WorkoutBase):
    name: Optional[str] = Field(None, max_length=255)


class WorkoutSetResponse(BaseModel):
    id: int
    intensity: Optional[float] = None
    effort: Optional[float] = None
    volume: Optional[int] = None
    working_weight: Optional[float] = None
    set_type: Optional[str] = None

    class Config:
        from_attributes = True


class WorkoutExerciseResponse(BaseModel):
    id: int
    exercise_id: int
    sets: List[WorkoutSetResponse] = Field(default_factory=list)

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
    # Include workout type in response
    workout_type: WorkoutTypeEnum
    exercises: List[WorkoutExerciseResponse]
    # Removed redundant exercise_instances field

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}
        extra = "ignore"


class WorkoutSummaryResponse(BaseModel):
    id: int
    name: str
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    status: Optional[str] = None
    plan_workout_id: Optional[int] = None  # Add this field
    workout_type: WorkoutTypeEnum = Field(default="manual")

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class WorkoutListResponse(BaseModel):
    id: int
    name: str
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    status: Optional[str] = None
    plan_workout_id: Optional[int] = None  # Add this field
    workout_type: WorkoutTypeEnum = Field(default="manual")

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class WorkoutPlanDetailItem(BaseModel):
    """Lightweight representation of a workout with exercise IDs for analysis."""

    id: int
    name: str
    scheduled_for: Optional[datetime] = None
    status: Optional[str] = None
    plan_order_index: Optional[int] = None
    exercise_ids: List[int] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}
