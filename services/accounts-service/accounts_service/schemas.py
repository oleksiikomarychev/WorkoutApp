from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    unit_system: str
    locale: str
    timezone: str | None = None
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime


class ProfileResponse(BaseModel):
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


class UserSummaryResponse(BaseModel):
    user_id: str
    display_name: str | None = None
    photo_url: str | None = None
    is_public: bool
    created_at: datetime
    last_active_at: datetime | None = None


class CoachingRatePlan(BaseModel):
    type: str | None = None
    currency: str | None = None
    amount_minor: int | None = None


class CoachingProfileResponse(BaseModel):
    enabled: bool
    accepting_clients: bool
    tagline: str | None = None
    description: str | None = None
    specializations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    timezone: str | None = None
    rate_plan: CoachingRatePlan | None = None
    created_at: datetime
    updated_at: datetime


class CoachingRatePlanUpdate(BaseModel):
    type: str | None = None
    currency: str | None = None
    amount_minor: int | None = None


class CoachingProfileUpdateRequest(BaseModel):
    enabled: bool | None = None
    accepting_clients: bool | None = None
    tagline: str | None = None
    description: str | None = None
    specializations: list[str] | None = None
    languages: list[str] | None = None
    experience_years: int | None = None
    timezone: str | None = None
    rate_plan: CoachingRatePlanUpdate | None = None


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    is_public: bool | None = None
    bodyweight_kg: float | None = None
    height_cm: float | None = None
    age: int | None = None
    sex: str | None = None
    training_experience_years: float | None = None
    training_experience_level: str | None = None
    primary_default_goal: str | None = None
    training_environment: str | None = None
    weekly_gain_coef: float | None = None


class SettingsUpdateRequest(BaseModel):
    unit_system: str | None = None
    locale: str | None = None
    timezone: str | None = None
    notifications_enabled: bool | None = None


ProfileResponse.model_rebuild()
CoachingProfileResponse.model_rebuild()
