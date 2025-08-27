from pydantic import BaseModel, Field
from typing import Optional, List

class UserMaxBase(BaseModel):
    exercise_id: int
    max_weight: int
    rep_max: int

class UserMaxCreate(UserMaxBase):
    pass

class UserMax(UserMaxBase):
    id: int

    class Config:
        orm_mode = True

class UserMaxResponse(UserMaxBase):
    id: int

    class Config:
        orm_mode = True

class UserMaxUpdate(BaseModel):
    id: int
    max_weight: Optional[int] = None
    rep_max: Optional[int] = None
