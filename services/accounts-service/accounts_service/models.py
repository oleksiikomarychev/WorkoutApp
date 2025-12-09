from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
    text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import JSONB

from .database import Base


class UnitSystem(str, Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True, index=True)
    display_name = Column(String, nullable=False)
    bio = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    bodyweight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    sex = Column(String(16), nullable=True)
    training_experience_years = Column(Float, nullable=True)
    training_experience_level = Column(String(32), nullable=True)
    primary_default_goal = Column(String(32), nullable=True)
    training_environment = Column(String(32), nullable=True)
    weekly_gain_coef = Column(Float, nullable=True)
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    is_public = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UserCoachingProfile(Base):
    __tablename__ = "user_coaching_profiles"

    user_id = Column(String, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), primary_key=True)
    enabled = Column(Boolean, nullable=False, server_default="false")
    accepting_clients = Column(Boolean, nullable=False, server_default="false")
    tagline = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    specializations = Column(
        JSONB(astext_type=Text()),
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    languages = Column(
        JSONB(astext_type=Text()),
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    experience_years = Column(Integer, nullable=True)
    timezone = Column(String, nullable=True)
    rate_type = Column(String(32), nullable=True)
    rate_currency = Column(String(3), nullable=True)
    rate_amount_minor = Column(Integer, nullable=True)
    stripe_connect_account_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UserAvatar(Base):
    __tablename__ = "user_avatars"

    user_id = Column(String, primary_key=True, index=True)
    content_type = Column(String(64), nullable=False, default="image/png")
    image = Column(LargeBinary, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(String, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), primary_key=True)
    unit_system = Column(
        SqlEnum(
            UnitSystem,
            name="unitsystem",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        server_default=UnitSystem.METRIC.value,
    )
    locale = Column(String, nullable=False, server_default="en")
    timezone = Column(String, nullable=True)
    notifications_enabled = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
