from __future__ import annotations

import os

import httpx
import structlog
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.relationships import (
    CoachAthleteEvent,
    CoachAthleteLink,
    CoachAthleteLinkTag,
    CoachAthleteNote,
    CoachAthleteTag,
)
from ..schemas.relationships import (
    CoachAthleteLinkCreate,
    CoachAthleteLinkResponse,
    CoachAthleteLinkStatusUpdate,
    CoachAthleteNoteCreate,
    CoachAthleteNoteResponse,
    CoachAthleteNoteUpdate,
    CoachAthleteStatus,
    CoachAthleteTagAssignRequest,
    CoachAthleteTagCreate,
    CoachAthleteTagResponse,
    CoachAthleteTagUpdate,
)

logger = structlog.get_logger(__name__)
MESSAGING_GATEWAY_URL = (os.getenv("MESSAGING_GATEWAY_URL") or "http://gateway:8000/api/v1/messaging").rstrip("/")
INTERNAL_GATEWAY_SECRET = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()


def _log_coach_athlete_event(
    db: AsyncSession,
    link_id: int,
    actor_id: str | None,
    event_type: str,
    payload: dict | None = None,
) -> None:
    event = CoachAthleteEvent(
        link_id=link_id,
        actor_id=actor_id,
        type=event_type,
        payload=payload or {},
    )
    db.add(event)


async def _get_link_or_404(db: AsyncSession, link_id: int) -> CoachAthleteLink:
    res = await db.execute(select(CoachAthleteLink).where(CoachAthleteLink.id == link_id))
    link: CoachAthleteLink | None = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return link


async def _get_tag_or_404(db: AsyncSession, tag_id: int) -> CoachAthleteTag:
    res = await db.execute(select(CoachAthleteTag).where(CoachAthleteTag.id == tag_id))
    tag: CoachAthleteTag | None = res.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag


async def _fetch_coach_profile(coach_id: str) -> dict:
    base_url = settings.accounts_service_url.rstrip("/")
    url = f"{base_url}/profile/{coach_id}"
    timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(url)
        except httpx.RequestError as exc:  # pragma: no cover - network errors
            logger.warning("relationships_fetch_coach_profile_failed", coach_id=coach_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch coach profile",
            ) from exc
    if resp.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach profile not found")
    if resp.status_code >= 400:
        logger.warning(
            "relationships_fetch_coach_profile_bad_status",
            coach_id=coach_id,
            status_code=resp.status_code,
            body=resp.text[:200],
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch coach profile")
    try:
        return resp.json()
    except Exception as exc:
        logger.warning("relationships_fetch_coach_profile_invalid_json", coach_id=coach_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid coach profile response",
        ) from exc


async def create_link(
    db: AsyncSession,
    coach_id: str,
    payload: CoachAthleteLinkCreate,
) -> CoachAthleteLinkResponse:
    acting_user_id = coach_id

    resolved_coach_id: str | None = None
    resolved_athlete_id: str | None = None

    if payload.athlete_id and payload.coach_id:
        if acting_user_id == payload.coach_id:
            resolved_coach_id = payload.coach_id
            resolved_athlete_id = payload.athlete_id
        elif acting_user_id == payload.athlete_id:
            resolved_coach_id = payload.coach_id
            resolved_athlete_id = payload.athlete_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ambiguous coach/athlete assignment",
            )
    elif payload.athlete_id:
        resolved_coach_id = acting_user_id
        resolved_athlete_id = payload.athlete_id
    elif payload.coach_id:
        resolved_coach_id = payload.coach_id
        resolved_athlete_id = acting_user_id
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either athlete_id or coach_id must be provided",
        )

    if resolved_coach_id is not None and resolved_coach_id == resolved_athlete_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coach and athlete must be different users",
        )

    stmt = select(CoachAthleteLink).where(
        CoachAthleteLink.coach_id == resolved_coach_id,
        CoachAthleteLink.athlete_id == resolved_athlete_id,
    )
    res = await db.execute(stmt)
    existing: CoachAthleteLink | None = res.scalar_one_or_none()
    if existing and existing.status != CoachAthleteStatus.ended.value:
        logger.info(
            "crm_link_existing_returned",
            link_id=existing.id,
            coach_id=existing.coach_id,
            athlete_id=existing.athlete_id,
            status=existing.status,
        )
        return CoachAthleteLinkResponse.model_validate(existing)

    initiated_by_coach = acting_user_id == resolved_coach_id
    initiated_by_athlete = acting_user_id == resolved_athlete_id

    if not initiated_by_coach and not initiated_by_athlete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current user must match either coach or athlete",
        )

    if initiated_by_athlete:
        if not resolved_coach_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coach id is required",
            )
        profile = await _fetch_coach_profile(resolved_coach_id)
        coaching = profile.get("coaching") or {}
        if not coaching.get("enabled"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Coach is not available for coaching",
            )
        if not coaching.get("accepting_clients"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Coach is not accepting new clients",
            )
        rate_plan = coaching.get("rate_plan") or {}
        currency = rate_plan.get("currency")
        amount_minor = rate_plan.get("amount_minor")
        connect_account_id = coaching.get("stripe_connect_account_id")
        if not connect_account_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Coach Stripe Connect account is not configured",
            )
        if not currency or amount_minor is None or amount_minor <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coach rate plan is not configured",
            )

    initial_status = CoachAthleteStatus.active if initiated_by_coach else CoachAthleteStatus.pending

    note_value = payload.note.strip() if payload.note and payload.note.strip() else None

    link = CoachAthleteLink(
        coach_id=resolved_coach_id,
        athlete_id=resolved_athlete_id,
        status=initial_status.value,
        note=note_value,
    )
    db.add(link)
    await db.flush()

    event_payload = {
        "status": initial_status.value,
        "initiated_by": "coach" if initiated_by_coach else "athlete",
    }
    _log_coach_athlete_event(
        db=db,
        link_id=link.id,
        actor_id=acting_user_id,
        event_type="link_created",
        payload=event_payload,
    )

    await db.commit()
    await db.refresh(link)
    logger.info(
        "crm_link_created",
        link_id=link.id,
        coach_id=link.coach_id,
        athlete_id=link.athlete_id,
        actor_id=acting_user_id,
        status=link.status,
    )
    try:
        if link.status == CoachAthleteStatus.active.value:
            await _ensure_messaging_channel_for_link(db, link)
    except Exception:
        logger.exception(
            "create_link: failed to create messaging channel | link_id=%s coach_id=%s athlete_id=%s",
            link.id,
            link.coach_id,
            link.athlete_id,
        )
    return CoachAthleteLinkResponse.model_validate(link)


async def create_note_for_link(
    db: AsyncSession,
    link_id: int,
    acting_user_id: str,
    payload: CoachAthleteNoteCreate,
) -> CoachAthleteNoteResponse:
    link = await _get_link_or_404(db, link_id)
    if acting_user_id not in {link.coach_id, link.athlete_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    text_value = payload.text.strip()
    if not text_value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Note text is required")

    note = CoachAthleteNote(
        link_id=link.id,
        author_id=acting_user_id,
        text=text_value,
        note_type=payload.note_type,
        pinned=payload.pinned,
    )
    db.add(note)
    await db.flush()

    event_payload = {
        "note_id": note.id,
        "note_type": note.note_type,
        "pinned": note.pinned,
    }
    _log_coach_athlete_event(
        db=db,
        link_id=link.id,
        actor_id=acting_user_id,
        event_type="note_created",
        payload=event_payload,
    )

    await db.commit()
    await db.refresh(note)
    logger.info(
        "crm_note_created",
        link_id=link.id,
        note_id=note.id,
        actor_id=acting_user_id,
        note_type=note.note_type,
        pinned=note.pinned,
    )
    return CoachAthleteNoteResponse.model_validate(note)


async def list_notes_for_link(
    db: AsyncSession,
    link_id: int,
    acting_user_id: str,
    limit: int = 100,
    offset: int = 0,
) -> list[CoachAthleteNoteResponse]:
    link = await _get_link_or_404(db, link_id)
    if acting_user_id not in {link.coach_id, link.athlete_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    stmt = (
        select(CoachAthleteNote)
        .where(CoachAthleteNote.link_id == link_id)
        .order_by(CoachAthleteNote.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    notes = res.scalars().all()
    return [CoachAthleteNoteResponse.model_validate(n) for n in notes]


async def update_note(
    db: AsyncSession,
    note_id: int,
    acting_user_id: str,
    payload: CoachAthleteNoteUpdate,
) -> CoachAthleteNoteResponse:
    stmt = (
        select(CoachAthleteNote, CoachAthleteLink)
        .join(CoachAthleteLink, CoachAthleteLink.id == CoachAthleteNote.link_id)
        .where(CoachAthleteNote.id == note_id)
    )
    res = await db.execute(stmt)
    row = res.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    note, link = row
    if acting_user_id not in {link.coach_id, link.athlete_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if note.author_id != acting_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only author can update note")

    updated = False
    if payload.text is not None:
        text_value = payload.text.strip()
        if not text_value:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Note text is required")
        note.text = text_value
        updated = True
    if payload.note_type is not None:
        note.note_type = payload.note_type
        updated = True
    if payload.pinned is not None:
        note.pinned = payload.pinned
        updated = True

    if not updated:
        return CoachAthleteNoteResponse.model_validate(note)

    event_payload = {
        "note_id": note.id,
        "note_type": note.note_type,
        "pinned": note.pinned,
    }
    _log_coach_athlete_event(
        db=db,
        link_id=link.id,
        actor_id=acting_user_id,
        event_type="note_updated",
        payload=event_payload,
    )

    await db.commit()
    await db.refresh(note)
    logger.info(
        "crm_note_updated",
        link_id=link.id,
        note_id=note.id,
        actor_id=acting_user_id,
        note_type=note.note_type,
        pinned=note.pinned,
    )
    return CoachAthleteNoteResponse.model_validate(note)


async def list_athletes_for_coach(
    db: AsyncSession,
    coach_id: str,
    status_filter: CoachAthleteStatus | None = None,
    tag_ids: list[int] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CoachAthleteLinkResponse]:
    stmt = select(CoachAthleteLink).where(CoachAthleteLink.coach_id == coach_id)
    if status_filter is not None:
        stmt = stmt.where(CoachAthleteLink.status == status_filter.value)
    if tag_ids:
        stmt = (
            stmt.join(CoachAthleteLinkTag, CoachAthleteLinkTag.link_id == CoachAthleteLink.id)
            .where(CoachAthleteLinkTag.tag_id.in_(tag_ids))
            .distinct()
        )
    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    links = res.scalars().all()
    return [CoachAthleteLinkResponse.model_validate(link) for link in links]


async def list_coaches_for_athlete(
    db: AsyncSession,
    athlete_id: str,
    status_filter: CoachAthleteStatus | None = None,
    tag_ids: list[int] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CoachAthleteLinkResponse]:
    stmt = select(CoachAthleteLink).where(CoachAthleteLink.athlete_id == athlete_id)
    if status_filter is not None:
        stmt = stmt.where(CoachAthleteLink.status == status_filter.value)
    if tag_ids:
        stmt = (
            stmt.join(CoachAthleteLinkTag, CoachAthleteLinkTag.link_id == CoachAthleteLink.id)
            .where(CoachAthleteLinkTag.tag_id.in_(tag_ids))
            .distinct()
        )
    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    links = res.scalars().all()
    return [CoachAthleteLinkResponse.model_validate(link) for link in links]


async def create_tag(
    db: AsyncSession,
    acting_user_id: str,
    payload: CoachAthleteTagCreate,
) -> CoachAthleteTagResponse:
    name_value = payload.name.strip()
    if not name_value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tag name is required")

    color_value = payload.color.strip() if payload.color else None
    owner_id = None if payload.is_global else acting_user_id

    tag = CoachAthleteTag(
        name=name_value,
        color=color_value,
        is_global=payload.is_global,
        owner_id=owner_id,
    )
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag with same name already exists")
    await db.refresh(tag)
    logger.info(
        "crm_tag_created",
        tag_id=tag.id,
        actor_id=acting_user_id,
        is_global=tag.is_global,
        is_active=tag.is_active,
    )
    return CoachAthleteTagResponse.model_validate(tag)


async def list_tags(
    db: AsyncSession,
    acting_user_id: str,
    include_inactive: bool = False,
) -> list[CoachAthleteTagResponse]:
    stmt = select(CoachAthleteTag).where(
        or_(
            CoachAthleteTag.is_global.is_(True),
            CoachAthleteTag.owner_id == acting_user_id,
        )
    )
    if not include_inactive:
        stmt = stmt.where(CoachAthleteTag.is_active.is_(True))
    stmt = stmt.order_by(CoachAthleteTag.name.asc())
    res = await db.execute(stmt)
    tags = res.scalars().all()
    return [CoachAthleteTagResponse.model_validate(t) for t in tags]


async def update_tag(
    db: AsyncSession,
    tag_id: int,
    acting_user_id: str,
    payload: CoachAthleteTagUpdate,
) -> CoachAthleteTagResponse:
    tag = await _get_tag_or_404(db, tag_id)
    if not tag.owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Global tags cannot be modified")
    if tag.owner_id != acting_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    updated = False
    if payload.name is not None:
        name_value = payload.name.strip()
        if not name_value:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tag name is required")
        tag.name = name_value
        updated = True
    if payload.color is not None:
        tag.color = payload.color.strip() if payload.color else None
        updated = True
    if payload.is_active is not None:
        tag.is_active = payload.is_active
        updated = True
    if payload.is_global is not None:
        tag.is_global = payload.is_global
        tag.owner_id = None if payload.is_global else acting_user_id
        updated = True

    if not updated:
        return CoachAthleteTagResponse.model_validate(tag)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag with same name already exists")
    await db.refresh(tag)
    return CoachAthleteTagResponse.model_validate(tag)


async def assign_tag_to_link(
    db: AsyncSession,
    link_id: int,
    acting_user_id: str,
    payload: CoachAthleteTagAssignRequest,
) -> CoachAthleteLinkResponse:
    link = await _get_link_or_404(db, link_id)
    if acting_user_id != link.coach_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only coach can manage tags")

    tag = await _get_tag_or_404(db, payload.tag_id)
    if not (tag.is_global or tag.owner_id == link.coach_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tag not accessible")
    if not tag.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag is inactive")

    link_tag = CoachAthleteLinkTag(link_id=link.id, tag_id=tag.id)
    db.add(link_tag)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already assigned")

    event_payload = {
        "tag_id": tag.id,
        "tag_name": tag.name,
    }
    _log_coach_athlete_event(
        db=db,
        link_id=link.id,
        actor_id=acting_user_id,
        event_type="tag_added",
        payload=event_payload,
    )

    await db.commit()
    await db.refresh(link)
    logger.info(
        "crm_tag_assigned_to_link",
        link_id=link.id,
        tag_id=tag.id,
        actor_id=acting_user_id,
    )
    return CoachAthleteLinkResponse.model_validate(link)


async def remove_tag_from_link(
    db: AsyncSession,
    link_id: int,
    tag_id: int,
    acting_user_id: str,
) -> CoachAthleteLinkResponse:
    link = await _get_link_or_404(db, link_id)
    if acting_user_id != link.coach_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only coach can manage tags")

    stmt = select(CoachAthleteLinkTag).where(
        CoachAthleteLinkTag.link_id == link.id,
        CoachAthleteLinkTag.tag_id == tag_id,
    )
    res = await db.execute(stmt)
    link_tag: CoachAthleteLinkTag | None = res.scalar_one_or_none()
    if not link_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag assignment not found")

    tag = await _get_tag_or_404(db, tag_id)

    await db.delete(link_tag)

    event_payload = {
        "tag_id": tag.id,
        "tag_name": tag.name,
    }
    _log_coach_athlete_event(
        db=db,
        link_id=link.id,
        actor_id=acting_user_id,
        event_type="tag_removed",
        payload=event_payload,
    )

    await db.commit()
    await db.refresh(link)
    logger.info(
        "crm_tag_removed_from_link",
        link_id=link.id,
        tag_id=tag.id,
        actor_id=acting_user_id,
    )
    return CoachAthleteLinkResponse.model_validate(link)


async def update_link_status(
    db: AsyncSession,
    link_id: int,
    acting_user_id: str,
    payload: CoachAthleteLinkStatusUpdate,
) -> CoachAthleteLinkResponse:
    res = await db.execute(select(CoachAthleteLink).where(CoachAthleteLink.id == link_id))
    link: CoachAthleteLink | None = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    if acting_user_id not in {link.coach_id, link.athlete_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    old_status = link.status
    link.status = payload.status.value
    if payload.status == CoachAthleteStatus.ended:
        from datetime import datetime

        link.ended_at = datetime.utcnow()
        link.ended_reason = payload.ended_reason

    event_payload = {
        "from_status": old_status,
        "to_status": link.status,
    }
    if payload.ended_reason:
        event_payload["ended_reason"] = payload.ended_reason
    _log_coach_athlete_event(
        db=db,
        link_id=link.id,
        actor_id=acting_user_id,
        event_type="status_changed",
        payload=event_payload,
    )

    await db.commit()
    await db.refresh(link)
    try:
        if link.status == CoachAthleteStatus.active.value:
            await _ensure_messaging_channel_for_link(db, link)
    except Exception:
        logger.exception(
            "update_link_status: failed to ensure messaging channel | link_id=%s coach_id=%s athlete_id=%s",
            link.id,
            link.coach_id,
            link.athlete_id,
        )
    return CoachAthleteLinkResponse.model_validate(link)


async def _ensure_messaging_channel_for_link(db: AsyncSession, link: CoachAthleteLink) -> None:
    if not MESSAGING_GATEWAY_URL:
        return
    if link.channel_id:
        return

    coach_id = link.coach_id
    athlete_id = link.athlete_id
    if not coach_id or not athlete_id:
        return

    url = f"{MESSAGING_GATEWAY_URL}/channels"
    headers: dict[str, str] = {"X-User-Id": str(coach_id)}
    if INTERNAL_GATEWAY_SECRET:
        headers["X-Internal-Secret"] = INTERNAL_GATEWAY_SECRET

    payload = {
        "type": "direct",
        "name": "Coach–athlete chat",
        "members": [str(coach_id), str(athlete_id)],
        "context_resource": {
            "type": "coach_athlete_link",
            "id": link.id,
            "owner_id": str(coach_id),
        },
        "metadata": {
            "link_id": link.id,
            "coach_id": str(coach_id),
            "athlete_id": str(athlete_id),
            "status": link.status,
        },
    }

    timeout = httpx.Timeout(3.0, connect=1.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except Exception:
            logger.warning(
                "_ensure_messaging_channel_for_link: request failed | link_id=%s coach_id=%s athlete_id=%s",
                link.id,
                coach_id,
                athlete_id,
            )
            return

    if response.status_code not in (200, 201):
        logger.warning(
            "_ensure_messaging_channel_for_link: non-2xx response | link_id=%s status=%s body=%s",
            link.id,
            response.status_code,
            response.text[:200],
        )
        return

    try:
        data = response.json()
    except Exception:
        data = None
    channel_id = data.get("id") if isinstance(data, dict) else None
    if not channel_id:
        return

    link.channel_id = str(channel_id)
    db.add(link)
    await db.commit()
    await db.refresh(link)
