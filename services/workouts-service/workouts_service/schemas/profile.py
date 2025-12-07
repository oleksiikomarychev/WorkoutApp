from datetime import datetime

from pydantic import BaseModel


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
