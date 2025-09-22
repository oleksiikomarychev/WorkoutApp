from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from pydantic import Field


class UserMaxBase(BaseModel):
    exercise_id: int
    exercise_name: str
    max_weight: float
    rep_max: int
    date: date
    true_1rm: Optional[float] = None
    verified_1rm: Optional[float] = None

    class Config:
        orm_mode = True


class UserMaxCreate(UserMaxBase):
    pass


class UserMaxResponse(UserMaxBase):
    id: int
    exercise_name: str


class UserMax(UserMaxBase):
    id: int

    class Config:
        orm_mode = True


#Не имеет rep_max чтобы  обновлять только max_weight в рамках прописанного ПМ(повторного максимума)
#При желании указать другой rep_max пользователь создает отдельный user_max с другим ПМ(повторным максимум)
#При достижении нового пользовательского максимума в рамках ПМ(повторного максимума) автоматически обновляется max_weight
class UserMaxUpdate(BaseModel):
    max_weight: Optional[int] = Field(gt=0)


class UserMaxBulkResponse(UserMaxBase):
    id: int
