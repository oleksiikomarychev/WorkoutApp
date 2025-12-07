from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserProfile


async def list_users(db: AsyncSession, *, limit: int = 100, offset: int = 0) -> list[UserProfile]:
    stmt = select(UserProfile).order_by(UserProfile.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
