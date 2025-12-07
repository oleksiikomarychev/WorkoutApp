from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkoutSessionBase(BaseModel):
    workout_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None = None


class WorkoutSessionCreate(BaseModel):
    started_at: datetime | None = None


class WorkoutSessionResponse(WorkoutSessionBase):
    id: int
    duration_seconds: int | None = None
    rpe_session: float | None = None
    location: str | None = None
    readiness_score: int | None = None
    progress: dict[str, Any] = Field(default_factory=dict)
    macro_suggestion: dict[str, Any] | None = None

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class SessionFinishRequest(BaseModel):
    cancelled: bool = False
    mark_workout_completed: bool = False


class SessionProgressUpdate(BaseModel):
    instance_id: int
    set_id: int
    completed: bool = True
