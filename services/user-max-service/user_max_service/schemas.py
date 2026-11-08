import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class UserMaxBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: int
    exercise_name: str | None = None
    max_weight: float
    rep_max: int
    date: dt.date
    true_1rm: float | None = None
    verified_1rm: float | None = None
    source: str | None = None


class UserMaxCreate(BaseModel):
    exercise_id: int
    max_weight: float
    rep_max: int
    date: dt.date
    true_1rm: float | None = None
    verified_1rm: float | None = None
    source: str | None = None


class UserMaxResponse(UserMaxBase):
    id: int


class UserMax(UserMaxBase):
    id: int


class UserMaxUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_weight: float | None = Field(default=None, gt=0)
    rep_max: int | None = Field(default=None, gt=0)
    true_1rm: float | None = Field(default=None, gt=0)
    verified_1rm: float | None = Field(default=None, gt=0)
    source: str | None = None
    date: dt.date | None = None


class UserMaxBulkResponse(UserMaxBase):
    id: int
