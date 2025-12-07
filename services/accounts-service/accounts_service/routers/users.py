from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..schemas import UserSummaryResponse
from ..services.users_service import list_users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/all", response_model=list[UserSummaryResponse])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> list[UserSummaryResponse]:
    rows = await list_users(db, limit=limit, offset=offset)
    return [
        UserSummaryResponse(
            user_id=u.user_id,
            display_name=u.display_name,
            photo_url=u.photo_url,
            is_public=u.is_public,
            created_at=u.created_at,
            last_active_at=u.last_active_at,
        )
        for u in rows
    ]
