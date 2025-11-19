from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UnitSystem, UserProfile, UserSettings
from ..schemas import ProfileResponse, SettingsResponse


@dataclass
class ProfileData:
    profile: UserProfile
    settings: UserSettings


async def _fetch_profile(db: AsyncSession, user_id: str) -> Optional[UserProfile]:
    return await db.get(UserProfile, user_id)


async def _fetch_settings(db: AsyncSession, user_id: str) -> Optional[UserSettings]:
    return await db.get(UserSettings, user_id)


async def ensure_profile_and_settings(db: AsyncSession, user_id: str) -> ProfileData:
    profile = await _fetch_profile(db, user_id)
    settings = await _fetch_settings(db, user_id)
    created = False
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        created = True
    if settings is None:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        created = True
    if created:
        await db.commit()
        await db.refresh(profile)
        await db.refresh(settings)
    return ProfileData(profile=profile, settings=settings)


def build_profile_response(data: ProfileData) -> ProfileResponse:
    return ProfileResponse(
        user_id=data.profile.user_id,
        display_name=data.profile.display_name,
        bio=data.profile.bio,
        photo_url=data.profile.photo_url,
        bodyweight_kg=data.profile.bodyweight_kg,
        height_cm=data.profile.height_cm,
        age=data.profile.age,
        sex=data.profile.sex,
        training_experience_years=data.profile.training_experience_years,
        training_experience_level=data.profile.training_experience_level,
        primary_default_goal=data.profile.primary_default_goal,
        training_environment=data.profile.training_environment,
        weekly_gain_coef=data.profile.weekly_gain_coef,
        last_active_at=data.profile.last_active_at,
        is_public=data.profile.is_public,
        created_at=data.profile.created_at,
        updated_at=data.profile.updated_at,
        settings=SettingsResponse(
            unit_system=data.settings.unit_system.value,
            locale=data.settings.locale,
            timezone=data.settings.timezone,
            notifications_enabled=data.settings.notifications_enabled,
            created_at=data.settings.created_at,
            updated_at=data.settings.updated_at,
        ),
    )


def parse_unit_system(raw: Optional[str]) -> Optional[UnitSystem]:
    if raw is None:
        return None
    try:
        return UnitSystem(raw)
    except ValueError as exc:  # pragma: no cover - validation error path
        allowed = ", ".join(u.value for u in UnitSystem)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unit_system must be one of: {allowed}",
        ) from exc
