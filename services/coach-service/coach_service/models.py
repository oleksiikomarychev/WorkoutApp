from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from .database import Base


def uuid4_str() -> str:
    return str(uuid.uuid4())


class CoachClientLink(Base):
    __tablename__ = "coach_client_links"
    __table_args__ = (
        UniqueConstraint("coach_user_id", "client_user_id", name="uq_coach_client_unique"),
        Index("idx_ccl_coach", "coach_user_id"),
        Index("idx_ccl_client", "client_user_id"),
        Index("idx_ccl_status", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    coach_user_id: Mapped[str] = mapped_column(String, nullable=False)
    client_user_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pricing_plan_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes_short: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # Denormalized snapshot for client display in lists
    client_display_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    client_avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


class ClientTag(Base):
    __tablename__ = "client_tags"
    __table_args__ = (
        UniqueConstraint("coach_user_id", "name", name="uq_tag_name_per_coach"),
        Index("idx_ct_coach", "coach_user_id"),
        Index("idx_ct_name", "name"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    coach_user_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class ClientTagLink(Base):
    __tablename__ = "client_tag_links"
    __table_args__ = (
        UniqueConstraint("tag_id", "client_user_id", "coach_user_id", name="uq_tag_client_coach"),
        Index("idx_ctl_tag", "tag_id"),
        Index("idx_ctl_client", "client_user_id"),
        Index("idx_ctl_coach", "coach_user_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)
    client_user_id: Mapped[str] = mapped_column(String, nullable=False)
    coach_user_id: Mapped[str] = mapped_column(String, nullable=False)


class ClientNote(Base):
    __tablename__ = "client_notes"
    __table_args__ = (
        Index("idx_cn_coach", "coach_user_id"),
        Index("idx_cn_client", "client_user_id"),
        Index("idx_cn_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    coach_user_id: Mapped[str] = mapped_column(String, nullable=False)
    client_user_id: Mapped[str] = mapped_column(String, nullable=False)
    visibility: Mapped[str] = mapped_column(String, default="coach_only")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        Index("idx_inv_coach", "coach_user_id"),
        Index("idx_inv_status", "status"),
        Index("idx_inv_created", "created_at"),
        Index("idx_inv_code", "code", unique=True),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_str)
    coach_user_id: Mapped[str] = mapped_column(String, nullable=False)
    email_or_user_id: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="sent")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
