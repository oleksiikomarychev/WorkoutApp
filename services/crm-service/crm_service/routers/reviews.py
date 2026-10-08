from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..schemas.reviews import CoachReviewCreate, CoachReviewListResponse, CoachReviewResponse
from ..services.reviews_service import create_review_for_link, get_reviews_for_coach

router = APIRouter(prefix="/crm/reviews", tags=["crm-reviews"])


@router.post("/links/{link_id}/reviews", response_model=CoachReviewResponse)
async def create_review(
    link_id: int,
    payload: CoachReviewCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachReviewResponse:
    review = await create_review_for_link(
        db=db,
        link_id=link_id,
        acting_user_id=user_id,
        payload=payload,
    )
    return review


@router.get("/coaches/{coach_id}/reviews", response_model=CoachReviewListResponse)
async def list_coach_reviews(
    coach_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> CoachReviewListResponse:
    return await get_reviews_for_coach(
        db=db,
        coach_id=coach_id,
        limit=limit,
        offset=offset,
    )
