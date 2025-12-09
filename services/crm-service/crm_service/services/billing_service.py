from __future__ import annotations

import os

import httpx
import stripe
import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import CoachAthletePayment
from ..models.relationships import CoachAthleteLink

logger = structlog.get_logger(__name__)

_STRIPE_SECRET_KEY = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
_STRIPE_PLATFORM_FEE_PERCENT = float(os.getenv("STRIPE_PLATFORM_FEE_PERCENT", "5.0"))
_STRIPE_CHECKOUT_SUCCESS_URL = (os.getenv("STRIPE_CHECKOUT_SUCCESS_URL") or "").strip()
_STRIPE_CHECKOUT_CANCEL_URL = (os.getenv("STRIPE_CHECKOUT_CANCEL_URL") or "").strip()

if _STRIPE_SECRET_KEY:
    stripe.api_key = _STRIPE_SECRET_KEY


async def _get_link_or_404(db: AsyncSession, link_id: int) -> CoachAthleteLink:
    res = await db.execute(select(CoachAthleteLink).where(CoachAthleteLink.id == link_id))
    link: CoachAthleteLink | None = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return link


async def _fetch_coach_billing_profile(coach_id: str) -> dict:
    base_url = settings.accounts_service_url.rstrip("/")
    url = f"{base_url}/profile/{coach_id}"
    timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(url)
        except httpx.RequestError as exc:  # pragma: no cover - network errors
            logger.warning("billing_fetch_coach_profile_failed", coach_id=coach_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch coach profile",
            ) from exc
    if resp.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach profile not found")
    if resp.status_code >= 400:
        logger.warning(
            "billing_fetch_coach_profile_bad_status",
            coach_id=coach_id,
            status_code=resp.status_code,
            body=resp.text[:200],
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch coach profile")
    try:
        return resp.json()
    except Exception as exc:  # pragma: no cover - invalid JSON
        logger.warning("billing_fetch_coach_profile_invalid_json", coach_id=coach_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid coach profile response",
        ) from exc


async def create_checkout_session_for_link(
    db: AsyncSession,
    link_id: int,
    acting_user_id: str,
) -> dict[str, object]:
    if not _STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe secret key not configured",
        )
    if not _STRIPE_CHECKOUT_SUCCESS_URL or not _STRIPE_CHECKOUT_CANCEL_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe Checkout URLs not configured",
        )

    link = await _get_link_or_404(db, link_id)
    if acting_user_id not in {link.coach_id, link.athlete_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    if getattr(link, "status", None) != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Coach-athlete link must be active to start checkout",
        )

    coach_id = link.coach_id
    athlete_id = link.athlete_id
    if not coach_id or not athlete_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid coach-athlete link")

    profile = await _fetch_coach_billing_profile(coach_id)
    coaching = profile.get("coaching") or {}
    rate_plan = coaching.get("rate_plan") or {}

    currency = rate_plan.get("currency")
    amount_minor = rate_plan.get("amount_minor")
    connect_account_id = coaching.get("stripe_connect_account_id")

    if not currency or amount_minor is None or amount_minor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coach rate plan is not configured",
        )
    if not connect_account_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Coach Stripe Connect account is not configured",
        )

    platform_fee = int(round(float(amount_minor) * _STRIPE_PLATFORM_FEE_PERCENT / 100.0))
    if platform_fee < 0:
        platform_fee = 0
    if platform_fee > amount_minor:
        platform_fee = amount_minor

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "unit_amount": amount_minor,
                        "product_data": {
                            "name": "Coaching subscription",
                            "description": "Access to coach workouts for one month",
                        },
                    },
                    "quantity": 1,
                }
            ],
            success_url=_STRIPE_CHECKOUT_SUCCESS_URL,
            cancel_url=_STRIPE_CHECKOUT_CANCEL_URL,
            payment_intent_data={
                "application_fee_amount": platform_fee,
                "transfer_data": {"destination": connect_account_id},
                "metadata": {
                    "coach_id": coach_id,
                    "athlete_id": athlete_id,
                    "link_id": link.id,
                },
            },
            metadata={
                "coach_id": coach_id,
                "athlete_id": athlete_id,
                "link_id": link.id,
            },
        )
    except Exception as exc:
        logger.error("billing_create_checkout_session_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create checkout session",
        ) from exc

    url = getattr(session, "url", None) or session.get("url")  # type: ignore[attr-defined]
    session_id = getattr(session, "id", None) or session.get("id")  # type: ignore[attr-defined]
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return checkout url",
        )

    payment = CoachAthletePayment(
        stripe_checkout_session_id=str(session_id) if session_id else str(url),
        stripe_payment_intent_id=None,
        coach_id=str(coach_id),
        athlete_id=str(athlete_id),
        link_id=link.id,
        currency=str(currency),
        amount_minor=int(amount_minor),
        status="pending",
    )
    db.add(payment)
    await db.commit()

    return {
        "checkout_url": str(url),
        "session_id": str(session_id) if session_id else "",
        "currency": currency,
        "amount_minor": amount_minor,
    }
