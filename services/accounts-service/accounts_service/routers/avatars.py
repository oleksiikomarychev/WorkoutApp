import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..metrics import AVATARS_APPLIED_TOTAL
from ..models import UserAvatar

router = APIRouter(prefix="/avatars", tags=["avatars"])


@router.post("/apply")
async def apply_avatar(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    raw: bytes = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty body")
    if len(raw) < 16:
        raise HTTPException(status_code=400, detail="Invalid image data")

    content_type = request.headers.get("content-type") or "image/png"

    try:
        result = await db.execute(select(UserAvatar).where(UserAvatar.user_id == user_id))
        existing: Optional[UserAvatar] = result.scalar_one_or_none()
        if existing:
            existing.image = raw
            existing.content_type = content_type
        else:
            existing = UserAvatar(user_id=user_id, image=raw, content_type=content_type)
            db.add(existing)
        await db.commit()
        AVATARS_APPLIED_TOTAL.inc()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save avatar: {e}")

    return {"uid": user_id, "ok": True}


@router.get("/{uid}.png")
async def get_avatar(uid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserAvatar).where(UserAvatar.user_id == uid))
    row: Optional[UserAvatar] = result.scalar_one_or_none()
    if not row or not row.image:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return StreamingResponse(io.BytesIO(row.image), media_type=row.content_type or "image/png")
