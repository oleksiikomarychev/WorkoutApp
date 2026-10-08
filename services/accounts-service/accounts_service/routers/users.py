from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..schemas import UserSummaryResponse
from ..services.users_service import get_users_by_ids, list_users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/all", response_model=list[UserSummaryResponse])
async def get_all_users(
    coach: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
    specializations: list[str] = Query(None),
    languages: list[str] = Query(None),
    min_rate: int | None = Query(None),
    max_rate: int | None = Query(None),
    sort_by: str | None = Query(None),
) -> list[UserSummaryResponse]:
    rows = await list_users(
        db,
        coach=coach,
        limit=limit,
        offset=offset,
        specializations=specializations,
        languages=languages,
        min_rate=min_rate,
        max_rate=max_rate,
        sort_by=sort_by,
    )
    return [
        UserSummaryResponse(
            user_id=u.user_id,
            display_name=u.display_name,
            photo_url=u.photo_url,
            is_public=u.is_public,
            created_at=u.created_at,
            last_active_at=u.last_active_at,
            coaching_enabled=u.coaching.enabled if u.coaching else None,
            average_rating=u.coaching.average_rating if u.coaching else None,
            review_count=u.coaching.review_count if u.coaching else None,
            specializations=u.coaching.specializations if u.coaching else [],
            languages=u.coaching.languages if u.coaching else [],
            rate_amount_minor=u.coaching.rate_amount_minor if u.coaching else None,
        )
        for u in rows
    ]


@router.get("", response_model=list[UserSummaryResponse])
async def get_users_by_id_list(
    user_ids: str = Query(..., description="Comma-separated list of user IDs"),
    db: AsyncSession = Depends(get_db),
) -> list[UserSummaryResponse]:
    """Get users by a list of IDs."""
    ids_list = [uid.strip() for uid in user_ids.split(",")]
    rows = await get_users_by_ids(db, user_ids=ids_list)
    return [
        UserSummaryResponse(
            user_id=str(u.user_id),
            display_name=u.display_name,
            photo_url=u.photo_url,
            is_public=u.is_public,
            created_at=u.created_at,
            last_active_at=u.last_active_at,
            coaching_enabled=u.coaching.enabled if u.coaching else None,
            average_rating=u.coaching.average_rating if u.coaching else None,
            review_count=u.coaching.review_count if u.coaching else None,
        )
        for u in rows
    ]
