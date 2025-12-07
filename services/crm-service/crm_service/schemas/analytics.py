from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AthleteTrainingSummary(BaseModel):
    athlete_id: str
    last_workout_at: datetime | None = None
    sessions_count: int
    total_volume: float | None = None
    active_plan_id: int | None = None
    active_plan_name: str | None = None
    days_since_last_workout: int | None = None

    sessions_per_week: float | None = None
    plan_adherence: float | None = None
    avg_intensity: float | None = None
    avg_effort: float | None = None
    rpe_distribution: dict[str, float] | None = None
    segment: str | None = None


class AthleteTrendPoint(BaseModel):
    period_start: datetime
    sessions_count: int
    total_volume: float


class AthleteDetailedAnalyticsResponse(BaseModel):
    athlete_id: str
    generated_at: datetime
    weeks: int
    sessions_count: int
    total_volume: float | None = None
    active_plan_id: int | None = None
    active_plan_name: str | None = None
    last_workout_at: datetime | None = None
    days_since_last_workout: int | None = None
    trend: list[AthleteTrendPoint]
    sessions_per_week: float | None = None
    plan_adherence: float | None = None
    avg_intensity: float | None = None
    avg_effort: float | None = None
    rpe_distribution: dict[str, float] | None = None
    muscle_volume_by_group: dict[str, float] | None = None
    muscle_volume_by_muscle: dict[str, float] | None = None


class CoachAthletesAnalyticsResponse(BaseModel):
    coach_id: str
    generated_at: datetime
    weeks: int
    total_athletes: int
    active_links: int
    athletes: list[AthleteTrainingSummary]


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
