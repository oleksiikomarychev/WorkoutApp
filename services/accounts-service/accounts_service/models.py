from __future__ import annotations

from enum import Enum
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    LargeBinary,
    String,
    Float,
    Integer,
    func,
)

from .database import Base


class UnitSystem(str, Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True, index=True)
    display_name = Column(String, nullable=True)
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
    is_public = Column(Boolean, nullable=False, server_default="false")
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
