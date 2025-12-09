from __future__ import annotations

import os
from datetime import datetime, timedelta

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..models import CoachAthletePayment
from ..models.relationships import CoachAthleteLink
from ..services.billing_service import create_checkout_session_for_link

router = APIRouter(prefix="/crm/billing", tags=["crm-billing"])

_STRIPE_WEBHOOK_SECRET = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()


@router.post("/links/{link_id}/checkout-session")
async def create_checkout_session(
    link_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await create_checkout_session_for_link(db=db, link_id=link_id, acting_user_id=user_id)


@router.get("/links/{link_id}/subscription")
async def get_subscription_status(
    link_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    res = await db.execute(select(CoachAthleteLink).where(CoachAthleteLink.id == link_id))
    link: CoachAthleteLink | None = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    if user_id not in {link.coach_id, link.athlete_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    latest_stmt = (
        select(CoachAthletePayment)
        .where(
            CoachAthletePayment.link_id == link_id,
            CoachAthletePayment.status == "succeeded",
        )
        .order_by(CoachAthletePayment.created_at.desc())
        .limit(1)
    )
    latest_res = await db.execute(latest_stmt)
    latest_payment: CoachAthletePayment | None = latest_res.scalar_one_or_none()

    active_stmt = (
        select(CoachAthletePayment.id)
        .where(
            CoachAthletePayment.link_id == link_id,
            CoachAthletePayment.status == "succeeded",
            CoachAthletePayment.valid_until.isnot(None),
            CoachAthletePayment.valid_until > func.now(),
        )
        .limit(1)
    )
    active_res = await db.execute(active_stmt)
    has_active = active_res.scalar_one_or_none() is not None

    if latest_payment is None:
        return {
            "active": False,
            "valid_until": None,
            "last_payment_status": None,
            "last_payment_at": None,
            "amount_minor": None,
            "currency": None,
        }

    return {
        "active": has_active,
        "valid_until": latest_payment.valid_until,
        "last_payment_status": latest_payment.status,
        "last_payment_at": latest_payment.created_at,
        "amount_minor": latest_payment.amount_minor,
        "currency": latest_payment.currency,
    }


@router.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    if not _STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe webhook secret not configured",
        )

    payload = await request.body()
    if stripe_signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=_STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        await _handle_checkout_session_completed(db, data_object)

    return {"status": "ok"}


async def _handle_checkout_session_completed(db: AsyncSession, session_obj: dict) -> None:
    session_id = session_obj.get("id")
    payment_intent_id = session_obj.get("payment_intent")
    currency = session_obj.get("currency")
    amount_total = session_obj.get("amount_total")
    metadata = session_obj.get("metadata") or {}

    if not session_id:
        return

    stmt = select(CoachAthletePayment).where(CoachAthletePayment.stripe_checkout_session_id == session_id)
    res = await db.execute(stmt)
    payment: CoachAthletePayment | None = res.scalar_one_or_none()

    if payment is None:
        coach_id = metadata.get("coach_id")
        athlete_id = metadata.get("athlete_id")
        link_id_raw = metadata.get("link_id")
        try:
            link_id = int(link_id_raw) if link_id_raw is not None else None
        except (TypeError, ValueError):
            link_id = None
        if not coach_id or not athlete_id or not currency or amount_total is None:
            return
        payment = CoachAthletePayment(
            stripe_checkout_session_id=str(session_id),
            stripe_payment_intent_id=str(payment_intent_id) if payment_intent_id else None,
            coach_id=str(coach_id),
            athlete_id=str(athlete_id),
            link_id=link_id,
            currency=str(currency),
            amount_minor=int(amount_total),
            status="succeeded",
            valid_until=datetime.utcnow() + timedelta(days=30),
        )
        db.add(payment)
        await db.commit()
        return

    if payment_intent_id and not payment.stripe_payment_intent_id:
        payment.stripe_payment_intent_id = str(payment_intent_id)
    if currency and not payment.currency:
        payment.currency = str(currency)
    if amount_total is not None and not payment.amount_minor:
        payment.amount_minor = int(amount_total)

    payment.status = "succeeded"
    if payment.valid_until is None:
        payment.valid_until = datetime.utcnow() + timedelta(days=30)

    await db.commit()
