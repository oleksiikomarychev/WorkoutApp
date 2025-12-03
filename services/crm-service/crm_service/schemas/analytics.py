from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AthleteTrainingSummary(BaseModel):
    athlete_id: str
    last_workout_at: Optional[datetime] = None
    sessions_count: int
    total_volume: Optional[float] = None
    active_plan_id: Optional[int] = None
    active_plan_name: Optional[str] = None
    days_since_last_workout: Optional[int] = None

    sessions_per_week: Optional[float] = None
    plan_adherence: Optional[float] = None
    avg_intensity: Optional[float] = None
    avg_effort: Optional[float] = None
    rpe_distribution: Optional[dict[str, float]] = None
    segment: Optional[str] = None


class AthleteTrendPoint(BaseModel):
    period_start: datetime
    sessions_count: int
    total_volume: float


class AthleteDetailedAnalyticsResponse(BaseModel):
    athlete_id: str
    generated_at: datetime
    weeks: int
    sessions_count: int
    total_volume: Optional[float] = None
    active_plan_id: Optional[int] = None
    active_plan_name: Optional[str] = None
    last_workout_at: Optional[datetime] = None
    days_since_last_workout: Optional[int] = None
    trend: List[AthleteTrendPoint]
    sessions_per_week: Optional[float] = None
    plan_adherence: Optional[float] = None
    avg_intensity: Optional[float] = None
    avg_effort: Optional[float] = None
    rpe_distribution: Optional[dict[str, float]] = None
    muscle_volume_by_group: Optional[dict[str, float]] = None
    muscle_volume_by_muscle: Optional[dict[str, float]] = None


class CoachAthletesAnalyticsResponse(BaseModel):
    coach_id: str
    generated_at: datetime
    weeks: int
    total_athletes: int
    active_links: int
    athletes: List[AthleteTrainingSummary]


class CoachSummaryAnalyticsResponse(BaseModel):
    coach_id: str
    generated_at: datetime
    weeks: int
    total_athletes: int
    active_links: int
    avg_sessions_per_week: float
    inactive_athletes_count: int
    avg_plan_adherence: float
    avg_intensity: float
    avg_effort: float
    segment_counts: dict[str, int]
