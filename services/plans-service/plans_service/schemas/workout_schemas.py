from pydantic import BaseModel

from .schedule_item import ParamsSets


class WorkoutExerciseCreate(BaseModel):
    exercise_definition_id: int
    sets: list[ParamsSets]


class WorkoutCreate(BaseModel):
    name: str
    exercises: list[WorkoutExerciseCreate]
