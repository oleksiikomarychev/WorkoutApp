from enum import Enum

from pydantic import BaseModel, Field


class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"


class MovementType(str, Enum):
    compound = "compound"
    isolation = "isolation"


class Region(str, Enum):
    upper = "upper"
    lower = "lower"


class MuscleInfo(BaseModel):
    key: str
    label: str
    group: str


class ExerciseListBase(BaseModel):
    name: str = Field(..., max_length=255)
    muscle_group: str | None = None
    equipment: str | None = None
    target_muscles: list[str] | None = Field(None, description="Primary target muscles")
    synergist_muscles: list[str] | None = Field(None, description="Synergist muscles involved")
    movement_type: MovementType | None = Field(None, description="compound or isolation")
    region: Region | None = Field(None, description="upper or lower")
    category: str | None = Field(None, description="Logical category, e.g. main_lift/accessory/isolation/conditioning")
    movement_pattern: str | None = Field(None, description="Movement pattern, e.g. horizontal_press/hinge/squat/row")
    is_competition_lift: bool | None = Field(None, description="Whether this exercise is a competition lift variant")


class ExerciseListCreate(ExerciseListBase):
    pass


class ExerciseListResponse(ExerciseListBase):
    id: int

    class Config:
        from_attributes = True


class ExerciseSet(BaseModel):
    id: int | None = Field(None, description="ID of the set within the instance")
    weight: float | None = Field(None, ge=0, description="Weight in kg")
    volume: int | None = Field(None, ge=1, description="Volume")
    intensity: int | None = Field(None, description="Intensity, % of 1RM")
    effort_type: EffortType | None = Field(None, description="Type of effort")
    effort: int | None = Field(None, description="Effort value")

    class Config:
        extra = "allow"


class ExerciseSetUpdate(BaseModel):
    weight: float | None = Field(None, ge=0)
    volume: int | None = Field(None, ge=1)
    reps: int | None = Field(None, ge=0)
    effort: int | None = Field(None, ge=4, le=10)

    class Config:
        extra = "allow"


class ExerciseInstanceBase(BaseModel):
    exercise_list_id: int
    sets: list[ExerciseSet]
    notes: str | None = None
    order: int | None = None

    class Config:
        from_attributes = True


class ExerciseInstanceCreate(ExerciseInstanceBase):
    user_max_id: int | None = None


class ExerciseInstanceResponse(ExerciseInstanceBase):
    id: int
    workout_id: int | None = None
    user_max_id: int | None = None
    exercise_definition: ExerciseListResponse | None = None

    class Config:
        from_attributes = True


class ExerciseInstanceCoachUpdate(BaseModel):
    notes: str | None = None
    order: int | None = None
    exercise_list_id: int | None = None
    sets: list[ExerciseSet] | None = None

    class Config:
        from_attributes = True
