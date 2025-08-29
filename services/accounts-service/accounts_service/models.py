from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Enum,
    UniqueConstraint,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid

from .db import Base


# Use portable UUID as string for SQLite; if Postgres used, PG UUID can be applied via Alembic

def uuid4_str() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    firebase_uid: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    locale: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    onboarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CoachClientStatusEnum(str, Enum):  # type: ignore[misc]
    pending = "pending"
    active = "active"
    paused = "paused"
    ended = "ended"


class CoachClientLink(Base):
    __tablename__ = "coach_client_links"
    __table_args__ = (
        UniqueConstraint("coach_user_id", "client_user_id", name="uq_coach_client_unique"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    coach_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    client_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, index=True, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pricing_plan_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes_short: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)


class ClientTag(Base):
    __tablename__ = "client_tags"
    __table_args__ = (
        UniqueConstraint("coach_user_id", "name", name="uq_tag_name_per_coach"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    coach_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class ClientTagLink(Base):
    __tablename__ = "client_tag_links"
    __table_args__ = (
        UniqueConstraint("tag_id", "client_user_id", "coach_user_id", name="uq_tag_client_coach"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    tag_id: Mapped[str] = mapped_column(String, ForeignKey("client_tags.id"), nullable=False)
    client_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    coach_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)


class ClientNote(Base):
    __tablename__ = "client_notes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    coach_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    client_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    visibility: Mapped[str] = mapped_column(String, default="coach_only")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    coach_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    email_or_user_id: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="sent", index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
