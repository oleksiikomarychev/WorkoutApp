from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"


class ExerciseSet(BaseModel):
    id: int | None = Field(None, description="ID of the set within the instance")
    weight: float | None = Field(None, ge=0, description="Weight in kg")
    volume: int | None = Field(None, ge=1, description="Volume")
    intensity: int | None = Field(None, description="Intensity, % of 1RM")
    effort_type: EffortType | None = Field(None, description="Type of effort")
    effort: int | None = Field(None, description="Effort value")

    class Config:
        extra = "allow"


class CoachWorkoutUpdate(BaseModel):
    name: str | None = None
    notes: str | None = None
    status: str | None = None
    scheduled_for: datetime | None = None
    completed_at: datetime | None = None
    started_at: datetime | None = None
    duration_seconds: int | None = None
    location: str | None = None
    readiness_score: int | None = None
    rpe_session: float | None = None


class CoachExerciseInstanceUpdate(BaseModel):
    notes: str | None = None
    order: int | None = None
    exercise_list_id: int | None = None
    sets: list[ExerciseSet] | None = None


class CoachExerciseInstanceCreate(BaseModel):
    exercise_list_id: int
    sets: list[ExerciseSet] = []
    notes: str | None = None
    order: int | None = None
    user_max_id: int | None = None


class CoachWorkoutMassEditWorkoutItem(BaseModel):
    workout_id: int
    update: CoachWorkoutUpdate


class CoachWorkoutMassEditExerciseItem(BaseModel):
    instance_id: int
    update: CoachExerciseInstanceUpdate


class CoachWorkoutsMassEditRequest(BaseModel):
    workouts: list[CoachWorkoutMassEditWorkoutItem] | None = None
    exercise_instances: list[CoachWorkoutMassEditExerciseItem] | None = None


class CoachPlanAiMassEditRequest(BaseModel):
    prompt: str
    mode: Literal["preview", "apply"] = "apply"
