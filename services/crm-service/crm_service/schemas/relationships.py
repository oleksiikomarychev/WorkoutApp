from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CoachAthleteStatus(str, Enum):
    pending = "pending"
    active = "active"
    paused = "paused"
    ended = "ended"


class CoachAthleteLinkBase(BaseModel):
    athlete_id: Optional[str] = Field(None, description="ID подопечного (атлета)")
    coach_id: Optional[str] = Field(None, description="ID тренера")
    note: Optional[str] = Field(None, description="Сообщение при запросе коучинга")


class CoachAthleteLinkCreate(CoachAthleteLinkBase):
    pass


class CoachAthleteLinkStatusUpdate(BaseModel):
    status: CoachAthleteStatus
    ended_reason: Optional[str] = None


class CoachAthleteLinkResponse(BaseModel):
    id: int
    coach_id: str
    athlete_id: str
    status: CoachAthleteStatus
    note: Optional[str] = None
    channel_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None
    ended_reason: Optional[str] = None

    class Config:
        from_attributes = True


class CoachAthleteTagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    color: Optional[str] = Field(None, max_length=32)


class CoachAthleteTagCreate(CoachAthleteTagBase):
    is_global: bool = Field(False, description="Глобальный ли тег (доступен всем)")


class CoachAthleteTagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    color: Optional[str] = Field(None, max_length=32)
    is_active: Optional[bool] = None
    is_global: Optional[bool] = Field(None, description="Изменение скоупа тега")


class CoachAthleteTagResponse(BaseModel):
    id: int
    name: str
    color: Optional[str]
    is_global: bool
    owner_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CoachAthleteTagAssignRequest(BaseModel):
    tag_id: int


class CoachAthleteNoteBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=10_000)
    note_type: Optional[str] = Field(None, description="Категория заметки (progress, risk и т.п.)")
    pinned: bool = Field(False, description="Закреплена ли заметка")


class CoachAthleteNoteCreate(CoachAthleteNoteBase):
    pass


class CoachAthleteNoteUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=1, max_length=10_000)
    note_type: Optional[str] = Field(None, description="Категория заметки")
    pinned: Optional[bool] = Field(None, description="Флаг закрепления")


class CoachAthleteNoteResponse(BaseModel):
    id: int
    link_id: int
    author_id: str
    text: str
    note_type: Optional[str] = None
    pinned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
