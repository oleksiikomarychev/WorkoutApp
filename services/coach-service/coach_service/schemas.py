from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ClientBrief(BaseModel):
    id: str
    display_name: Optional[str] = Field(default=None, max_length=80)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    status: str = Field(default="active")


class ClientsListOut(BaseModel):
    items: List[ClientBrief]


# Invitations
class InvitationCreate(BaseModel):
    email_or_user_id: str
    ttl_hours: int | None = Field(default=None, ge=1, le=24 * 30)


class InvitationOut(BaseModel):
    id: str
    coach_user_id: str
    email_or_user_id: str
    code: str
    status: str
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationsListOut(BaseModel):
    items: List[InvitationOut]


# Tags
class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: Optional[str] = Field(default=None, max_length=7)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    color: Optional[str] = Field(default=None, max_length=7)


class TagOut(BaseModel):
    id: str
    coach_user_id: str
    name: str
    color: Optional[str] = None

    class Config:
        from_attributes = True


class TagsListOut(BaseModel):
    items: List[TagOut]


# Notes
class ClientNoteCreate(BaseModel):
    client_user_id: str
    text: str = Field(min_length=1, max_length=4000)
    visibility: Literal["coach_only", "shared_with_client"] = "coach_only"


class ClientNoteUpdate(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    visibility: Optional[Literal["coach_only", "shared_with_client"]] = None


class ClientNoteOut(BaseModel):
    id: str
    coach_user_id: str
    client_user_id: str
    visibility: str
    text: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientNotesListOut(BaseModel):
    items: List[ClientNoteOut]
