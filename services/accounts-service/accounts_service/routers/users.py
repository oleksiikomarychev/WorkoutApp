from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models import UserProfile
from ..schemas import UserSummaryResponse
from ..services.users_service import get_users_by_ids, list_users

router = APIRouter(prefix="/users", tags=["users"])


def _build_user_summary_response(u: UserProfile) -> UserSummaryResponse:
    """Map UserProfile model instance to UserSummaryResponse schema."""
    return UserSummaryResponse(
        user_id=str(u.user_id),
        display_name=u.display_name,
        photo_url=u.photo_url,
        is_public=u.is_public,
        created_at=u.created_at,
        last_active_at=u.last_active_at,
        coaching_enabled=u.coaching.enabled if u.coaching else None,
        average_rating=u.coaching.average_rating if u.coaching else None,
        review_count=u.coaching.review_count if u.coaching else None,
        specializations=list(u.coaching.specializations or []) if u.coaching else [],
        languages=list(u.coaching.languages or []) if u.coaching else [],
        rate_amount_minor=u.coaching.rate_amount_minor if u.coaching else None,
    )


@router.get("/all", response_model=list[UserSummaryResponse])
async def get_all_users(
    coach: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    specializations: list[str] | None = Query(default=None),
    languages: list[str] | None = Query(default=None),
    min_rate: int | None = Query(default=None, ge=0),
    max_rate: int | None = Query(default=None, ge=0),
    sort_by: str | None = Query(default=None),
) -> list[UserSummaryResponse]:
    """Retrieve public user profiles with optional coach filtering and pagination."""
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
    return [_build_user_summary_response(u) for u in rows]


@router.get("", response_model=list[UserSummaryResponse])
async def get_users_by_id_list(
    user_ids: str = Query(..., description="Comma-separated list of user IDs"),
    db: AsyncSession = Depends(get_db),
) -> list[UserSummaryResponse]:
    """Get users by a comma-separated list of user IDs."""
    ids_list = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
    if not ids_list:
        return []
    rows = await get_users_by_ids(db, user_ids=ids_list)
    return [_build_user_summary_response(u) for u in rows]
