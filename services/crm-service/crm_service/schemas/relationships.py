from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CoachAthleteStatus(StrEnum):
    pending = "pending"
    active = "active"
    paused = "paused"
    ended = "ended"


class CoachAthleteLinkBase(BaseModel):
    athlete_id: str | None = Field(None, description="ID подопечного (атлета)")
    coach_id: str | None = Field(None, description="ID тренера")
    note: str | None = Field(None, description="Сообщение при запросе коучинга")


class CoachAthleteLinkCreate(CoachAthleteLinkBase):
    pass


class CoachAthleteLinkStatusUpdate(BaseModel):
    status: CoachAthleteStatus
    ended_reason: str | None = None


class CoachAthleteLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coach_id: str
    athlete_id: str
    status: CoachAthleteStatus
    note: str | None = None
    channel_id: str | None = None
    created_at: datetime
    updated_at: datetime
    ended_at: datetime | None = None
    ended_reason: str | None = None


class CoachAthleteTagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    color: str | None = Field(None, max_length=32)


class CoachAthleteTagCreate(CoachAthleteTagBase):
    is_global: bool = Field(False, description="Глобальный ли тег (доступен всем)")


class CoachAthleteTagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    color: str | None = Field(None, max_length=32)
    is_active: bool | None = None
    is_global: bool | None = Field(None, description="Изменение скоупа тега")


class CoachAthleteTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str | None
    is_global: bool
    owner_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CoachAthleteTagAssignRequest(BaseModel):
    tag_id: int


class CoachAthleteNoteBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=10_000)
    note_type: str | None = Field(None, description="Категория заметки (progress, risk и т.п.)")
    pinned: bool = Field(False, description="Закреплена ли заметка")


class CoachAthleteNoteCreate(CoachAthleteNoteBase):
    pass


class CoachAthleteNoteUpdate(BaseModel):
    text: str | None = Field(None, min_length=1, max_length=10_000)
    note_type: str | None = Field(None, description="Категория заметки")
    pinned: bool | None = Field(None, description="Флаг закрепления")


class CoachAthleteNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    link_id: int
    author_id: str
    text: str
    note_type: str | None = None
    pinned: bool
    created_at: datetime
    updated_at: datetime
