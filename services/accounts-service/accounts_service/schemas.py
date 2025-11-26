from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    unit_system: str
    locale: str
    timezone: Optional[str] = None
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime


class ProfileResponse(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    bodyweight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    training_experience_years: Optional[float] = None
    training_experience_level: Optional[str] = None
    primary_default_goal: Optional[str] = None
    training_environment: Optional[str] = None
    weekly_gain_coef: Optional[float] = None
    last_active_at: Optional[datetime] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    settings: SettingsResponse
    coaching: Optional["CoachingProfileResponse"] = None


class UserSummaryResponse(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    is_public: bool
    created_at: datetime
    last_active_at: Optional[datetime] = None


class CoachingRatePlan(BaseModel):
    type: Optional[str] = None
    currency: Optional[str] = None
    amount_minor: Optional[int] = None


class CoachingProfileResponse(BaseModel):
    enabled: bool
    accepting_clients: bool
    tagline: Optional[str] = None
    description: Optional[str] = None
    specializations: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    timezone: Optional[str] = None
    rate_plan: Optional[CoachingRatePlan] = None
    created_at: datetime
    updated_at: datetime


class CoachingRatePlanUpdate(BaseModel):
    type: Optional[str] = None
    currency: Optional[str] = None
    amount_minor: Optional[int] = None


class CoachingProfileUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    accepting_clients: Optional[bool] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    specializations: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    experience_years: Optional[int] = None
    timezone: Optional[str] = None
    rate_plan: Optional[CoachingRatePlanUpdate] = None


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    is_public: Optional[bool] = None
    bodyweight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    training_experience_years: Optional[float] = None
    training_experience_level: Optional[str] = None
    primary_default_goal: Optional[str] = None
    training_environment: Optional[str] = None
    weekly_gain_coef: Optional[float] = None


class SettingsUpdateRequest(BaseModel):
    unit_system: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = None


ProfileResponse.model_rebuild()
CoachingProfileResponse.model_rebuild()
