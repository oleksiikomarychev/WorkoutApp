from pydantic import BaseModel


class CalendarPlanCreate(BaseModel):
    name: str
    duration_weeks: int


class CalendarPlan(CalendarPlanCreate):
    id: int

    class Config:
        from_attributes = True


class MesocycleCreate(BaseModel):
    name: str
    order_index: int
    weeks_count: int


class Mesocycle(MesocycleCreate):
    id: int
    calendar_plan_id: int

    class Config:
        from_attributes = True


class MicrocycleCreate(BaseModel):
    name: str
    order_index: int
    days_count: int


class Microcycle(MicrocycleCreate):
    id: int
    mesocycle_id: int

    class Config:
        from_attributes = True


class PlanWorkoutCreate(BaseModel):
    day_label: str
    order_index: int


class PlanWorkout(PlanWorkoutCreate):
    id: int
    microcycle_id: int

    class Config:
        from_attributes = True


class PlanExerciseCreate(BaseModel):
    exercise_definition_id: int
    exercise_name: str
    order_index: int


class PlanExercise(PlanExerciseCreate):
    id: int
    plan_workout_id: int

    class Config:
        from_attributes = True


class PlanSetCreate(BaseModel):
    order_index: int
    intensity: int | None = None
    effort: int | None = None
    volume: int | None = None


class PlanSet(PlanSetCreate):
    id: int
    plan_exercise_id: int

    class Config:
        from_attributes = True


class TrainingPlan(BaseModel):
    calendar_plan: CalendarPlan
    mesocycles: list[Mesocycle]
    microcycles: list[Microcycle]
    workouts: list[PlanWorkout]
    exercises: list[PlanExercise]
    sets: list[PlanSet]


class TrainingPlanWithRationale(BaseModel):
    plan: TrainingPlan
    plan_rationale: str | None = None


class TrainingPlanWithSummary(BaseModel):
    plan: TrainingPlan
    plan_summary: str | None = None
