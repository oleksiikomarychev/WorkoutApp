from pydantic import BaseModel, Field

from .schedule_item import ParamsSets


class WorkoutExerciseCreate(BaseModel):
    exercise_definition_id: int
    sets: list[ParamsSets]
    rest_seconds: int | None = Field(default=None, ge=0)
    notes: str | None = None


class WorkoutCreate(BaseModel):
    name: str
    exercises: list[WorkoutExerciseCreate]
