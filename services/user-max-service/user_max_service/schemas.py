from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class UserMaxBase(BaseModel):
    exercise_id: int
    exercise_name: str
    max_weight: float
    rep_max: int
    date: date
    true_1rm: Optional[float] = None
    verified_1rm: Optional[float] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


class UserMaxCreate(BaseModel):
    """Request schema for creating UserMax (without exercise_name)"""

    exercise_id: int
    max_weight: float
    rep_max: int
    date: date
    true_1rm: Optional[float] = None
    verified_1rm: Optional[float] = None
    source: Optional[str] = None


class UserMaxResponse(UserMaxBase):
    id: int
    exercise_name: str


class UserMax(UserMaxBase):
    id: int

    class Config:
        from_attributes = True


# Не имеет rep_max, чтобы обновлять только max_weight в рамках прописанного
# ПМ (повторного максимума).
# При желании указать другой rep_max пользователь создает отдельный user_max
# с другим ПМ (повторным максимум).
# При достижении нового пользовательского максимума в рамках ПМ (повторного
# максимума) автоматически обновляется max_weight.
class UserMaxUpdate(BaseModel):
    max_weight: Optional[int] = Field(gt=0)


class UserMaxBulkResponse(UserMaxBase):
    id: int
