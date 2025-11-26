from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from ..database import Base


class CoachAthleteLink(Base):
    __tablename__ = "coach_athlete_links"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(String(255), nullable=False, index=True)
    athlete_id = Column(String(255), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    note = Column(Text, nullable=True)
    channel_id = Column(String(255), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    ended_reason = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("coach_id", "athlete_id", name="uq_coach_athlete_pair"),
        Index("ix_coach_status", "coach_id", "status"),
        Index("ix_athlete_status", "athlete_id", "status"),
        Index("ix_coach_athlete_channel", "channel_id"),
    )


class CoachAthleteEvent(Base):
    __tablename__ = "coach_athlete_events"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, nullable=False, index=True)
    actor_id = Column(String(255), nullable=True, index=True)
    type = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_coach_athlete_events_link_created", "link_id", "created_at"),
        Index("ix_coach_athlete_events_type_created", "type", "created_at"),
    )


class CoachAthleteNote(Base):
    __tablename__ = "coach_athlete_notes"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, nullable=False, index=True)
    author_id = Column(String(255), nullable=False, index=True)
    text = Column(Text, nullable=False)
    note_type = Column(String(64), nullable=True)
    pinned = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_coach_athlete_notes_link_created", "link_id", "created_at"),
        Index("ix_coach_athlete_notes_author_created", "author_id", "created_at"),
    )


class CoachAthleteTag(Base):
    __tablename__ = "coach_athlete_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    color = Column(String(32), nullable=True)
    is_global = Column(Boolean, nullable=False, default=False)
    owner_id = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_coach_tags_owner_name"),
        Index("ix_coach_athlete_tags_active", "is_active"),
    )


class CoachAthleteLinkTag(Base):
    __tablename__ = "coach_athlete_link_tags"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("coach_athlete_links.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("coach_athlete_tags.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("link_id", "tag_id", name="uq_link_tag"),
        Index("ix_coach_athlete_link_tags_tag_created", "tag_id", "created_at"),
    )
