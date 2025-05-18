from pydantic import BaseModel, EmailStr, Field, SecretStr
from typing import Optional, List
from datetime import date
from .user_models import UserRole
from .workout_models import Workout


class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.ATHLETE

class UserCreate(UserBase):
    password: SecretStr = Field(min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    

class UserInDBBase(UserBase):
    id: int

    class Config:
        orm_mode = True


class AthleteBase(BaseModel):
    date_of_birth: Optional[date] = None
    

class AthleteCreate(AthleteBase):
    user: UserCreate

class AthleteUpdate(AthleteBase):
    pass

class AthleteInDB(AthleteBase):
    id: int
    user_id: int
    user: UserInDBBase

    class Config:
        orm_mode = True


class TrainerBase(BaseModel):
    specialization: Optional[str] = None


class TrainerCreate(TrainerBase):
    user: UserCreate

class TrainerUpdate(TrainerBase):
    pass

class TrainerInDB(TrainerBase):
    id: int
    user_id: int
    user: UserInDBBase

    class Config:
        orm_mode = True


class UserResponse(UserInDBBase):
    athlete_profile: Optional[AthleteInDB] = None
    trainer_profile: Optional[TrainerInDB] = None
    assigned_trainer_id: Optional[int] = None


class AssignTrainerRequest(BaseModel):
    athlete_id: int
    trainer_id: int
