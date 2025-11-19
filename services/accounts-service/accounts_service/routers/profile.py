from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..schemas import (
    ProfileResponse,
    ProfileUpdateRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)
from ..services.profile_service import (
    build_profile_response,
    ensure_profile_and_settings,
    parse_unit_system,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=ProfileResponse)
async def get_profile_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    data = await ensure_profile_and_settings(db, user_id)
    return build_profile_response(data)


@router.patch("/me", response_model=ProfileResponse)
async def update_profile_me(
    payload: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    data = await ensure_profile_and_settings(db, user_id)
    profile = data.profile
    modified = False
    if payload.display_name is not None:
        profile.display_name = payload.display_name.strip() or None
        modified = True
    if payload.bio is not None:
        profile.bio = payload.bio.strip() or None
        modified = True
    if payload.is_public is not None:
        profile.is_public = payload.is_public
        modified = True
    if payload.bodyweight_kg is not None:
        profile.bodyweight_kg = payload.bodyweight_kg
        modified = True
    if payload.height_cm is not None:
        profile.height_cm = payload.height_cm
        modified = True
    if payload.age is not None:
        profile.age = payload.age
        modified = True
    if payload.sex is not None:
        profile.sex = payload.sex
        modified = True
    if payload.training_experience_years is not None:
        profile.training_experience_years = payload.training_experience_years
        modified = True
    if payload.training_experience_level is not None:
        profile.training_experience_level = payload.training_experience_level
        modified = True
    if payload.primary_default_goal is not None:
        profile.primary_default_goal = payload.primary_default_goal
        modified = True
    if payload.training_environment is not None:
        profile.training_environment = payload.training_environment
        modified = True
    if payload.weekly_gain_coef is not None:
        profile.weekly_gain_coef = payload.weekly_gain_coef
        modified = True
    if modified:
        await db.commit()
        await db.refresh(profile)
        await db.refresh(data.settings)
    return build_profile_response(data)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    data = await ensure_profile_and_settings(db, user_id)
    return SettingsResponse(
        unit_system=data.settings.unit_system.value,
        locale=data.settings.locale,
        timezone=data.settings.timezone,
        notifications_enabled=data.settings.notifications_enabled,
        created_at=data.settings.created_at,
        updated_at=data.settings.updated_at,
    )


@router.patch("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    data = await ensure_profile_and_settings(db, user_id)
    settings = data.settings
    modified = False
    if payload.unit_system is not None:
        settings.unit_system = parse_unit_system(payload.unit_system)
        modified = True
    if payload.locale is not None:
        settings.locale = payload.locale
        modified = True
    if payload.timezone is not None:
        settings.timezone = payload.timezone
        modified = True
    if payload.notifications_enabled is not None:
        settings.notifications_enabled = payload.notifications_enabled
        modified = True
    if modified:
        await db.commit()
        await db.refresh(settings)
    return SettingsResponse(
        unit_system=settings.unit_system.value,
        locale=settings.locale,
        timezone=settings.timezone,
        notifications_enabled=settings.notifications_enabled,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )
