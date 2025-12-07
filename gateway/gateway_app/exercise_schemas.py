from pydantic import BaseModel


class ExerciseSetCreate(BaseModel):
    weight: float | None = None
    volume: float | None = None
    intensity: float | None = None
    effort_type: str | None = None
    effort: float | None = None
    reps: int | None = None


class ExerciseSet(BaseModel):
    id: int
    weight: float | None = None
    volume: float | None = None
    intensity: float | None = None
    effort_type: str | None = None
    effort: float | None = None
    reps: int | None = None


class ExerciseInstanceCreate(BaseModel):
    exercise_list_id: int
    sets: list[ExerciseSetCreate] = []
    notes: str | None = None
    order: int | None = None


class ExerciseInstanceResponse(BaseModel):
    id: int
    exercise_list_id: int
    sets: list[ExerciseSet] = []
    notes: str | None = None
    order: int | None = None
    workout_id: int
    user_max_id: int | None = None
