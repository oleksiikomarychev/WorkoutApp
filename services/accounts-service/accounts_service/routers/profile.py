from __future__ import annotations

import stripe
import structlog
from backend_common.http_client import ServiceClient
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..dependencies import get_current_user_id, get_db
from ..metrics import (
    COACHING_PROFILES_UPDATED_TOTAL,
    PROFILES_UPDATED_TOTAL,
    SETTINGS_UPDATED_TOTAL,
)
from ..schemas import (
    CoachingEligibilityResponse,
    CoachingProfileUpdateRequest,
    CoachingRatingUpdate,
    ProfileResponse,
    ProfileUpdateRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)
from ..services.profile_service import (
    build_profile_response,
    ensure_coaching_profile,
    ensure_profile_and_settings,
    parse_unit_system,
)

logger = structlog.get_logger(__name__)

if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/profile", tags=["profile"])


# --- Current User Profile Endpoints (/profile/me) ---

@router.get("/me", response_model=ProfileResponse)
async def get_profile_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Get the current authenticated user's profile and settings."""
    data = await ensure_profile_and_settings(db, user_id)
    if settings.PLANS_SERVICE_URL:
        try:
            async with ServiceClient() as client:
                url = f"{settings.PLANS_SERVICE_URL}/plans/adoption/coaching-eligibility/me"
                payload = await client.get_json(
                    url,
                    headers={"X-User-Id": user_id},
                    default=None,
                    expected_status=200,
                    user_id=user_id,
                )
                if isinstance(payload, dict):
                    data.coaching_eligibility = CoachingEligibilityResponse.model_validate(payload)
        except Exception as exc:
            logger.warning("fetch_coaching_eligibility_failed", user_id=user_id, error=str(exc))
            data.coaching_eligibility = None

    return build_profile_response(data)


@router.patch("/me", response_model=ProfileResponse)
async def update_profile_me(
    payload: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Update current user profile attributes."""
    data = await ensure_profile_and_settings(db, user_id)
    profile = data.profile
    modified = False

    if payload.display_name is not None:
        new_name = (payload.display_name or "").strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="display_name must not be empty",
            )
        profile.display_name = new_name
        modified = True

    if payload.bio is not None:
        profile.bio = payload.bio.strip() or None
        modified = True

    if payload.photo_url is not None:
        profile.photo_url = payload.photo_url.strip() or None
        modified = True

    if payload.is_public is not None:
        profile.is_public = payload.is_public
        modified = True

    if payload.bodyweight_kg is not None:
        if payload.bodyweight_kg <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bodyweight_kg must be positive",
            )
        profile.bodyweight_kg = payload.bodyweight_kg
        modified = True

    if payload.height_cm is not None:
        if payload.height_cm <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="height_cm must be positive",
            )
        profile.height_cm = payload.height_cm
        modified = True

    if payload.age is not None:
        if payload.age < 0 or payload.age > 150:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="age must be between 0 and 150",
            )
        profile.age = payload.age
        modified = True

    if payload.sex is not None:
        profile.sex = payload.sex
        modified = True

    if payload.training_experience_years is not None:
        if payload.training_experience_years < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="training_experience_years cannot be negative",
            )
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
        PROFILES_UPDATED_TOTAL.inc()

    return build_profile_response(data)


@router.patch("/me/coaching", response_model=ProfileResponse)
async def update_coaching_profile_me(
    payload: CoachingProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Update coaching marketplace profile for the current authenticated user."""
    data = await ensure_profile_and_settings(db, user_id)
    coaching = await ensure_coaching_profile(db, user_id)
    modified = False

    if payload.enabled is not None:
        if payload.enabled:
            if not settings.PLANS_SERVICE_URL:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Plans service is not configured",
                )
            try:
                async with ServiceClient() as client:
                    url = f"{settings.PLANS_SERVICE_URL}/plans/adoption/coaching-eligibility/me"
                    raw = await client.get_json(
                        url,
                        headers={"X-User-Id": user_id},
                        default=None,
                        expected_status=200,
                        user_id=user_id,
                    )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to contact plans service for coaching eligibility",
                ) from exc

            if not isinstance(raw, dict):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch coaching eligibility",
                )
            try:
                eligibility = CoachingEligibilityResponse.model_validate(raw)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid coaching eligibility response",
                ) from exc

            data.coaching_eligibility = eligibility
            if not eligibility.eligible:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Coaching is not yet available for this account",
                )
        coaching.enabled = payload.enabled
        modified = True

    if payload.tagline is not None:
        coaching.tagline = payload.tagline.strip() or None
        modified = True

    if payload.description is not None:
        coaching.description = payload.description.strip() or None
        modified = True

    if payload.specializations is not None:
        coaching.specializations = [s.strip() for s in payload.specializations if s and s.strip()]
        modified = True

    if payload.languages is not None:
        coaching.languages = [s.strip() for s in payload.languages if s and s.strip()]
        modified = True

    if payload.rate_plan is not None:
        rp = payload.rate_plan
        rp_data = rp.model_dump(exclude_unset=True)
        if "amount_minor" in rp_data:
            coaching.rate_amount_minor = rp_data.get("amount_minor")
            modified = True

    if modified:
        await db.commit()
        await db.refresh(coaching)
        COACHING_PROFILES_UPDATED_TOTAL.inc()

    data.coaching = coaching
    return build_profile_response(data)


@router.post("/me/stripe/connect/onboarding-link")
async def create_stripe_connect_onboarding_link(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Generate a Stripe Connect onboarding link for the current coach."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe secret key not configured",
        )
    if not settings.STRIPE_CONNECT_RETURN_URL or not settings.STRIPE_CONNECT_REFRESH_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe Connect URLs not configured",
        )

    coaching = await ensure_coaching_profile(db, user_id)
    account_id = coaching.stripe_connect_account_id

    try:
        if not account_id:
            account = stripe.Account.create(
                type="express",
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
            )
            account_id = account.get("id")
            if not account_id:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Stripe did not return account id",
                )
            coaching.stripe_connect_account_id = account_id
            await db.commit()
            await db.refresh(coaching)

        account_link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=settings.STRIPE_CONNECT_REFRESH_URL,
            return_url=settings.STRIPE_CONNECT_RETURN_URL,
            type="account_onboarding",
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - external Stripe errors
        logger.error("stripe_connect_link_failed", user_id=user_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Stripe Connect onboarding link",
        ) from exc

    url = account_link.get("url")
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return onboarding url",
        )
    return {"onboarding_url": url}


# --- Settings Endpoints (/profile/settings) ---
# NOTE: Must be defined before /{user_id} to avoid path collision!

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Retrieve settings for the current user."""
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
    """Update settings (unit system, locale, timezone, notifications) for the current user."""
    data = await ensure_profile_and_settings(db, user_id)
    curr_settings = data.settings
    modified = False

    if payload.unit_system is not None:
        curr_settings.unit_system = parse_unit_system(payload.unit_system)
        modified = True

    if payload.locale is not None:
        curr_settings.locale = payload.locale
        modified = True

    if payload.timezone is not None:
        curr_settings.timezone = payload.timezone
        modified = True

    if payload.notifications_enabled is not None:
        curr_settings.notifications_enabled = payload.notifications_enabled
        modified = True

    if modified:
        await db.commit()
        await db.refresh(curr_settings)
        SETTINGS_UPDATED_TOTAL.inc()

    return SettingsResponse(
        unit_system=curr_settings.unit_system.value,
        locale=curr_settings.locale,
        timezone=curr_settings.timezone,
        notifications_enabled=curr_settings.notifications_enabled,
        created_at=curr_settings.created_at,
        updated_at=curr_settings.updated_at,
    )


# --- User Specific Dynamic Endpoints (/profile/{user_id}) ---

@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Get public profile by user ID."""
    data = await ensure_profile_and_settings(db, user_id)
    return build_profile_response(data)


@router.patch("/{user_id}/coaching")
async def update_coaching_rating(
    user_id: str,
    payload: CoachingRatingUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update coaching rating aggregates (called internally by CRM service)."""
    coaching = await ensure_coaching_profile(db, user_id)

    if payload.average_rating is not None:
        coaching.average_rating = payload.average_rating
    if payload.review_count is not None:
        coaching.review_count = payload.review_count

    await db.commit()
    await db.refresh(coaching)
    COACHING_PROFILES_UPDATED_TOTAL.inc()

    return {"status": "ok"}
