from pydantic import BaseModel


class WorkoutSet(BaseModel):
    exercise_id: int
    intensity: float | None = None
    effort: float | None = None
    volume: int | None = None
    working_weight: float | None = None


class ExerciseSet(BaseModel):
    exercise_id: int
    intensity: float | None = None
    effort: float | None = None
    volume: int | None = None
    working_weight: float | None = None


class ExerciseInWorkout(BaseModel):
    exercise_id: int
    sets: list[ExerciseSet]


class WorkoutExercise(BaseModel):
    exercise_id: int
    sets: list[WorkoutSet]


class WorkoutGenerationItem(BaseModel):
    name: str
    exercises: list[ExerciseInWorkout]

    scheduled_for: str | None = None
    plan_order_index: int | None = None


class WorkoutGenerationRequest(BaseModel):
    applied_plan_id: int
    compute_weights: bool
    rounding_step: float
    rounding_mode: str
    workouts: list[WorkoutGenerationItem]


class WorkoutGenerationResponse(BaseModel):
    workout_ids: list[int]
    created_count: int | None = None
    existing_count: int | None = None
