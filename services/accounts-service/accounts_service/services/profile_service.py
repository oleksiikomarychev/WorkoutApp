from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UnitSystem, UserCoachingProfile, UserProfile, UserSettings
from ..schemas import (
    CoachingProfileResponse,
    CoachingRatePlan,
    ProfileResponse,
    SettingsResponse,
)


@dataclass
class ProfileData:
    profile: UserProfile
    settings: UserSettings
    coaching: UserCoachingProfile | None = None


async def _fetch_profile(db: AsyncSession, user_id: str) -> UserProfile | None:
    return await db.get(UserProfile, user_id)


async def _fetch_settings(db: AsyncSession, user_id: str) -> UserSettings | None:
    return await db.get(UserSettings, user_id)


async def _fetch_coaching_profile(db: AsyncSession, user_id: str) -> UserCoachingProfile | None:
    return await db.get(UserCoachingProfile, user_id)


async def ensure_profile_and_settings(db: AsyncSession, user_id: str) -> ProfileData:
    profile = await _fetch_profile(db, user_id)
    settings = await _fetch_settings(db, user_id)
    created = False
    if profile is None:
        profile = UserProfile(user_id=user_id, display_name=user_id)
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
    coaching = await _fetch_coaching_profile(db, user_id)
    return ProfileData(profile=profile, settings=settings, coaching=coaching)


async def ensure_coaching_profile(db: AsyncSession, user_id: str) -> UserCoachingProfile:
    coaching = await _fetch_coaching_profile(db, user_id)
    if coaching is None:
        coaching = UserCoachingProfile(user_id=user_id)
        db.add(coaching)
        await db.flush()
    return coaching


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
        coaching=build_coaching_response(data.coaching),
    )


def build_coaching_response(
    entity: UserCoachingProfile | None,
) -> CoachingProfileResponse | None:
    if entity is None:
        return None

    rate_plan = None
    if any([entity.rate_type, entity.rate_currency, entity.rate_amount_minor is not None]):
        rate_plan = CoachingRatePlan(
            type=entity.rate_type,
            currency=entity.rate_currency,
            amount_minor=entity.rate_amount_minor,
        )

    return CoachingProfileResponse(
        enabled=bool(entity.enabled),
        accepting_clients=bool(entity.accepting_clients),
        tagline=entity.tagline,
        description=entity.description,
        specializations=list(entity.specializations or []),
        languages=list(entity.languages or []),
        experience_years=entity.experience_years,
        timezone=entity.timezone,
        rate_plan=rate_plan,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def parse_unit_system(raw: str | None) -> UnitSystem | None:
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
