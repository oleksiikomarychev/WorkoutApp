from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class WorkoutBase(BaseModel):
    name: str = Field(..., max_length=255)


class WorkoutCreate(WorkoutBase):
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


class WorkoutUpdate(WorkoutBase):
    name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    rpe_session: Optional[float] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkoutResponse(WorkoutBase):
    id: int
    # For microservice split we do not embed exercise instances here; gateway may aggregate.
    exercise_instances: List[Dict[str, Any]] = []
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    rpe_session: Optional[float] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None

    class Config:
        from_attributes = True


# Workout Session Schemas
class WorkoutSessionBase(BaseModel):
    workout_id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None


class WorkoutSessionCreate(BaseModel):
    started_at: Optional[datetime] = None


class WorkoutSessionResponse(WorkoutSessionBase):
    id: int

    class Config:
        from_attributes = True
