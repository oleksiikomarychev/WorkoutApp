from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
    root_exercise_id: int | None = Field(
        None,
        description=("ID of the root/base exercise definition this exercise is a variant of"),
    )

    image_url: str | None = Field(None, description="URL to exercise image (png/jpg)")
    gif_url: str | None = Field(None, description="URL to exercise gif animation")


class ExerciseListCreate(ExerciseListBase):
    pass


class ExerciseListResponse(ExerciseListBase):
    id: int

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
