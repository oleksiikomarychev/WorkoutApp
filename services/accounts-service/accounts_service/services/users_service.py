from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..models import UserCoachingProfile, UserProfile


async def list_users(
    db: AsyncSession,
    *,
    coach: bool = False,
    limit: int = 100,
    offset: int = 0,
    specializations: list[str] | None = None,
    languages: list[str] | None = None,
    min_rate: int | None = None,
    max_rate: int | None = None,
    sort_by: str | None = None,
) -> list[UserProfile]:
    stmt = select(UserProfile).options(joinedload(UserProfile.coaching))
    
    # Build coaching profile conditions
    coaching_conditions = []
    
    if coach:
        coaching_conditions.append(UserCoachingProfile.enabled == True)
    
    if specializations:
        coaching_conditions.append(UserCoachingProfile.specializations.contains(specializations))
    
    if languages:
        coaching_conditions.append(UserCoachingProfile.languages.contains(languages))
    
    if min_rate is not None:
        coaching_conditions.append(UserCoachingProfile.rate_amount_minor >= min_rate)
    
    if max_rate is not None:
        coaching_conditions.append(UserCoachingProfile.rate_amount_minor <= max_rate)
    
    # Apply coaching profile filter if any conditions exist
    if coaching_conditions:
        stmt = stmt.join(UserCoachingProfile).where(and_(*coaching_conditions))
    
    # Sorting
    if sort_by == "rating":
        stmt = stmt.join(UserCoachingProfile).order_by(
            UserCoachingProfile.average_rating.desc().nulls_last()
        )
    elif sort_by == "last_active":
        stmt = stmt.order_by(UserProfile.last_active_at.desc().nulls_last())
    else:  # default: created_at
        stmt = stmt.order_by(UserProfile.created_at.desc())
    
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def get_users_by_ids(db: AsyncSession, user_ids: list[str]) -> list[UserProfile]:
    """Get users by their IDs (firebase UIDs or UUIDs)."""
    # Use Firebase UIDs as strings directly - don't convert to UUID
    stmt = select(UserProfile).options(joinedload(UserProfile.coaching)).where(UserProfile.user_id.in_(user_ids))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
