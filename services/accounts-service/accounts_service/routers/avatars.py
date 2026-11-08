from __future__ import annotations

import io
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..metrics import AVATARS_APPLIED_TOTAL
from ..models import UserAvatar

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/avatars", tags=["avatars"])


@router.post("/apply")
async def apply_avatar(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Store raw avatar image bytes for the current user."""
    raw: bytes = await request.body()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty body")
    if len(raw) < 16:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image data")

    content_type = request.headers.get("content-type") or "image/png"

    try:
        result = await db.execute(select(UserAvatar).where(UserAvatar.user_id == user_id))
        existing: UserAvatar | None = result.scalar_one_or_none()
        if existing:
            existing.image = raw
            existing.content_type = content_type
        else:
            existing = UserAvatar(user_id=user_id, image=raw, content_type=content_type)
            db.add(existing)
        await db.commit()
        AVATARS_APPLIED_TOTAL.inc()
    except Exception as exc:
        await db.rollback()
        logger.error("failed_to_save_avatar", user_id=user_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save avatar image",
        ) from exc

    return {"uid": user_id, "ok": True}


@router.get("/{uid}.png")
async def get_avatar(uid: str, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Retrieve avatar binary for the specified user ID."""
    result = await db.execute(select(UserAvatar).where(UserAvatar.user_id == uid))
    row: UserAvatar | None = result.scalar_one_or_none()
    if not row or not row.image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    return StreamingResponse(io.BytesIO(row.image), media_type=row.content_type or "image/png")
