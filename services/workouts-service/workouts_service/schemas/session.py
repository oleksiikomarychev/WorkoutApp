from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WorkoutSessionBase(BaseModel):
    workout_id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None


class WorkoutSessionCreate(BaseModel):
    started_at: Optional[datetime] = None


class WorkoutSessionResponse(WorkoutSessionBase):
    id: int
    duration_seconds: Optional[int] = None
    rpe_session: Optional[float] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    macro_suggestion: Optional[Dict[str, Any]] = None

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
