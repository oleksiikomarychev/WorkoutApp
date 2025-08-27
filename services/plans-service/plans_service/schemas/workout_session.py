from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class WorkoutSessionBase(BaseModel):
    workout_id: int


class WorkoutSessionCreate(WorkoutSessionBase):
    pass


class WorkoutSessionResponse(WorkoutSessionBase):
    id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str = Field(default="active")
    duration_seconds: Optional[int] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    # Optional session metrics
    device_source: Optional[str] = None
    hr_avg: Optional[int] = None
    hr_max: Optional[int] = None
    hydration_liters: Optional[float] = None
    mood: Optional[str] = None
    injury_flags: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }


class SessionProgressUpdate(BaseModel):
    instance_id: int
    set_id: int
    completed: bool = True


class SessionFinishRequest(BaseModel):
    cancelled: bool = False
    mark_workout_completed: bool = False
    # Optional metrics to store on finish
    device_source: Optional[str] = None
    hr_avg: Optional[int] = None
    hr_max: Optional[int] = None
    hydration_liters: Optional[float] = None
    mood: Optional[str] = None
    injury_flags: Optional[Dict[str, Any]] = None
