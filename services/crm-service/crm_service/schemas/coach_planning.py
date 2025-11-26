from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CoachWorkoutUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None
    rpe_session: Optional[float] = None


class CoachExerciseInstanceUpdate(BaseModel):
    notes: Optional[str] = None
    order: Optional[int] = None


class CoachWorkoutMassEditWorkoutItem(BaseModel):
    workout_id: int
    update: CoachWorkoutUpdate


class CoachWorkoutMassEditExerciseItem(BaseModel):
    instance_id: int
    update: CoachExerciseInstanceUpdate


class CoachWorkoutsMassEditRequest(BaseModel):
    workouts: Optional[list[CoachWorkoutMassEditWorkoutItem]] = None
    exercise_instances: Optional[list[CoachWorkoutMassEditExerciseItem]] = None


class CoachPlanAiMassEditRequest(BaseModel):
    prompt: str
    mode: Literal["preview", "apply"] = "apply"
