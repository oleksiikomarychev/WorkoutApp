from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"


class ExerciseSet(BaseModel):
    id: Optional[int] = Field(None, description="ID of the set within the instance")
    weight: Optional[float] = Field(None, ge=0, description="Weight in kg")
    volume: Optional[int] = Field(None, ge=1, description="Volume")
    intensity: Optional[int] = Field(None, description="Intensity, % of 1RM")
    effort_type: Optional[EffortType] = Field(None, description="Type of effort")
    effort: Optional[int] = Field(None, description="Effort value")

    class Config:
        extra = "allow"


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
    exercise_list_id: Optional[int] = None
    sets: Optional[List[ExerciseSet]] = None


class CoachExerciseInstanceCreate(BaseModel):
    exercise_list_id: int
    sets: List[ExerciseSet] = []
    notes: Optional[str] = None
    order: Optional[int] = None
    user_max_id: Optional[int] = None


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
