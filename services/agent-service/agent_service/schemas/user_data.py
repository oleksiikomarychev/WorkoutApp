from pydantic import BaseModel


class UserDataInput(BaseModel):
    goals: list[str]
    available_equipment: list[str]
    workouts_per_microcycle: int | None = None
    microcycles_per_mesocycle: int | None = None
    mesocycles_per_plan: int | None = None
    plan_duration_weeks: int | None = None
    limits: dict[str, float] | None = None
    notes: str | None = None
    current_metrics: dict[str, float] | None = None
    target_metrics: dict[str, float] | None = None
    normalization_unit: str | None = None
    normalization_value: float | None = None
