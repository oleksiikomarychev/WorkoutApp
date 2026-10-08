import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models import UnitSystem, UserAvatar, UserCoachingProfile, UserProfile, UserSettings

router = APIRouter(prefix="/internal/users", tags=["internal"])


def _deleted_user_id(user_id: str) -> str:
    import hashlib

    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
    return f"deleted:{digest}"


@router.post("/{user_id}/purge")
async def purge_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> dict[str, str]:
    expected_secret = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    now = datetime.now(UTC)
    tombstone = _deleted_user_id(user_id)

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile: UserProfile | None = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user_id, display_name=tombstone)
        db.add(profile)
        await db.flush()

    profile.display_name = tombstone
    profile.bio = None
    profile.photo_url = None
    profile.bodyweight_kg = None
    profile.height_cm = None
    profile.age = None
    profile.sex = None
    profile.training_experience_years = None
    profile.training_experience_level = None
    profile.primary_default_goal = None
    profile.training_environment = None
    profile.weekly_gain_coef = None
    profile.last_active_at = None
    profile.is_public = False
    profile.deleted_at = now

    await db.execute(delete(UserAvatar).where(UserAvatar.user_id == user_id))

    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings: UserSettings | None = result.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.flush()

    settings.unit_system = UnitSystem.METRIC
    settings.locale = "en"
    settings.timezone = None
    settings.notifications_enabled = True

    await db.execute(delete(UserCoachingProfile).where(UserCoachingProfile.user_id == user_id))

    await db.commit()

    return {"status": "ok"}
