from typing import List

from pydantic import BaseModel

from .schedule_item import ParamsSets


class WorkoutExerciseCreate(BaseModel):
    exercise_definition_id: int
    sets: List[ParamsSets]


class WorkoutCreate(BaseModel):
    name: str
    exercises: List[WorkoutExerciseCreate]
