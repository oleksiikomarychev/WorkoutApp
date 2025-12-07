from datetime import date

from pydantic import BaseModel, Field


class UserMaxBase(BaseModel):
    exercise_id: int
    exercise_name: str
    max_weight: float
    rep_max: int
    date: date
    true_1rm: float | None = None
    verified_1rm: float | None = None
    source: str | None = None

    class Config:
        from_attributes = True


class UserMaxCreate(BaseModel):
    exercise_id: int
    max_weight: float
    rep_max: int
    date: date
    true_1rm: float | None = None
    verified_1rm: float | None = None
    source: str | None = None


class UserMaxResponse(UserMaxBase):
    id: int
    exercise_name: str


class UserMax(UserMaxBase):
    id: int

    class Config:
        from_attributes = True


class UserMaxUpdate(BaseModel):
    max_weight: int | None = Field(gt=0)


class UserMaxBulkResponse(UserMaxBase):
    id: int
