from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """User settings representation."""

    unit_system: str
    locale: str
    timezone: str | None = None
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime


class CoachingRatePlan(BaseModel):
    """Coaching rate plan pricing."""

    amount_minor: int | None = Field(default=None, ge=0, description="Amount in minor currency units (e.g. cents)")


class CoachingProfileResponse(BaseModel):
    """Coaching profile details for athlete marketplace."""

    enabled: bool
    tagline: str | None = None
    description: str | None = None
    specializations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    rate_plan: CoachingRatePlan | None = None
    stripe_connect_account_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CoachingEligibilityResponse(BaseModel):
    """Eligibility check for publishing coaching profiles."""

    eligible: bool
    threshold: int
    max_unique_adopters: int
    best_root_plan_id: int | None = None


class ProfileResponse(BaseModel):
    """Complete user profile response schema."""

    user_id: str
    display_name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    bodyweight_kg: float | None = None
    height_cm: float | None = None
    age: int | None = None
    sex: str | None = None
    training_experience_years: float | None = None
    training_experience_level: str | None = None
    primary_default_goal: str | None = None
    training_environment: str | None = None
    weekly_gain_coef: float | None = None
    last_active_at: datetime | None = None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    settings: SettingsResponse
    coaching: CoachingProfileResponse | None = None
    coaching_eligibility: CoachingEligibilityResponse | None = None


class UserSummaryResponse(BaseModel):
    """Brief public user profile summary."""

    user_id: str
    display_name: str | None = None
    photo_url: str | None = None
    is_public: bool
    created_at: datetime
    last_active_at: datetime | None = None
    coaching_enabled: bool | None = None
    average_rating: float | None = None
    review_count: int | None = None
    specializations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    rate_amount_minor: int | None = None


class CoachingRatePlanUpdate(BaseModel):
    """Coaching rate plan payload."""

    amount_minor: int | None = Field(default=None, ge=0)


class CoachingProfileUpdateRequest(BaseModel):
    """Request schema for updating coaching details."""

    enabled: bool | None = None
    tagline: str | None = None
    description: str | None = None
    specializations: list[str] | None = None
    languages: list[str] | None = None
    rate_plan: CoachingRatePlanUpdate | None = None


class ProfileUpdateRequest(BaseModel):
    """Request schema for updating user profile fields."""

    display_name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    is_public: bool | None = None
    bodyweight_kg: float | None = Field(default=None, gt=0)
    height_cm: float | None = Field(default=None, gt=0)
    age: int | None = Field(default=None, ge=0, le=150)
    sex: str | None = None
    training_experience_years: float | None = Field(default=None, ge=0)
    training_experience_level: str | None = None
    primary_default_goal: str | None = None
    training_environment: str | None = None
    weekly_gain_coef: float | None = None


class SettingsUpdateRequest(BaseModel):
    """Request schema for updating user settings."""

    unit_system: str | None = None
    locale: str | None = None
    timezone: str | None = None
    notifications_enabled: bool | None = None


class CoachingRatingUpdate(BaseModel):
    """Request schema for internal coaching review aggregate updates."""

    average_rating: float | None = Field(default=None, ge=0.0, le=5.0)
    review_count: int | None = Field(default=None, ge=0)


ProfileResponse.model_rebuild()
CoachingProfileResponse.model_rebuild()
