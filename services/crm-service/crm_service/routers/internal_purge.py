import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models import CoachAthleteEvent, CoachAthleteLink, CoachAthleteNote, CoachAthletePayment, CoachAthleteTag

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

    tombstone = _deleted_user_id(user_id)
    now = datetime.now(UTC)

    affected_link_ids = select(CoachAthleteLink.id).where(
        (CoachAthleteLink.coach_id == user_id) | (CoachAthleteLink.athlete_id == user_id)
    )

    await db.execute(
        update(CoachAthleteLink)
        .where((CoachAthleteLink.coach_id == user_id) | (CoachAthleteLink.athlete_id == user_id))
        .values(
            status="ended",
            ended_at=now,
            ended_reason="user_purged",
        )
    )

    await db.execute(
        update(CoachAthleteLink)
        .where((CoachAthleteLink.coach_id == user_id) | (CoachAthleteLink.athlete_id == user_id))
        .values(note="[deleted]", channel_id=None)
    )

    await db.execute(update(CoachAthleteNote).where(CoachAthleteNote.link_id.in_(affected_link_ids)).values(text="[deleted]"))
    await db.execute(
        update(CoachAthleteEvent)
        .where(CoachAthleteEvent.link_id.in_(affected_link_ids))
        .values(payload=None)
    )

    await db.execute(
        update(CoachAthleteLink)
        .where(CoachAthleteLink.coach_id == user_id)
        .values(coach_id=tombstone)
    )
    await db.execute(
        update(CoachAthleteLink)
        .where(CoachAthleteLink.athlete_id == user_id)
        .values(athlete_id=tombstone)
    )

    await db.execute(update(CoachAthleteNote).where(CoachAthleteNote.author_id == user_id).values(author_id=tombstone))
    await db.execute(
        update(CoachAthletePayment)
        .where(CoachAthletePayment.coach_id == user_id)
        .values(coach_id=tombstone)
    )
    await db.execute(
        update(CoachAthletePayment)
        .where(CoachAthletePayment.athlete_id == user_id)
        .values(athlete_id=tombstone)
    )
    await db.execute(update(CoachAthleteEvent).where(CoachAthleteEvent.actor_id == user_id).values(actor_id=tombstone))

    await db.execute(delete(CoachAthleteTag).where(CoachAthleteTag.owner_id == user_id))

    await db.commit()

    return {"status": "ok"}
