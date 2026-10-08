from __future__ import annotations

import httpx
import structlog
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.relationships import CoachAthleteLink
from ..models.reviews import CoachReview
from ..schemas.reviews import CoachReviewCreate, CoachReviewListResponse, CoachReviewResponse

logger = structlog.get_logger(__name__)


async def _get_link_or_404(db: AsyncSession, link_id: int) -> CoachAthleteLink:
    res = await db.execute(select(CoachAthleteLink).where(CoachAthleteLink.id == link_id))
    link: CoachAthleteLink | None = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return link


async def _can_user_review_link(db: AsyncSession, link_id: int, user_id: str) -> bool:
    """Check if user is the athlete in an active or paused link and can leave a review."""
    res = await db.execute(
        select(CoachAthleteLink).where(
            CoachAthleteLink.id == link_id,
            CoachAthleteLink.athlete_id == user_id,
            CoachAthleteLink.status.in_(["active", "paused"]),
        )
    )
    link = res.scalar_one_or_none()
    return link is not None


async def _update_coaching_rating_aggregates(db: AsyncSession, coach_id: str) -> None:
    """Recalculate average_rating and review_count for a coach."""
    # Calculate average rating and count
    res = await db.execute(
        select(
            func.count(CoachReview.id).label("count"),
            func.avg(CoachReview.rating).label("avg_rating"),
        ).where(CoachReview.coach_id == coach_id)
    )
    result = res.one()
    
    review_count = result.count or 0
    average_rating = float(result.avg_rating) if result.avg_rating else None
    
    # Update accounts service
    try:
        base_url = settings.accounts_service_url.rstrip("/")
        url = f"{base_url}/profile/{coach_id}/coaching"
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
        
        payload = {
            "average_rating": average_rating,
            "review_count": review_count,
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.patch(url, json=payload)
            
        if resp.status_code >= 400:
            logger.warning(
                "reviews_update_coaching_profile_failed",
                coach_id=coach_id,
                status_code=resp.status_code,
                body=resp.text[:200],
            )
    except httpx.RequestError as exc:
        logger.warning("reviews_update_coaching_profile_request_failed", coach_id=coach_id, error=str(exc))
    except Exception as exc:
        logger.warning("reviews_update_coaching_profile_error", coach_id=coach_id, error=str(exc))


async def create_review_for_link(
    db: AsyncSession,
    link_id: int,
    acting_user_id: str,
    payload: CoachReviewCreate,
) -> CoachReview:
    """Create a review for a coach-athlete link. Only the athlete can review."""
    # Check if user can review this link
    can_review = await _can_user_review_link(db, link_id, acting_user_id)
    if not can_review:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only review coaches for active or paused coaching relationships",
        )
    
    # Get the link to find coach_id
    link = await _get_link_or_404(db, link_id)
    coach_id = link.coach_id
    
    # Check if user already reviewed this link
    existing_res = await db.execute(
        select(CoachReview).where(
            CoachReview.link_id == link_id,
            CoachReview.reviewer_id == acting_user_id,
        )
    )
    existing = existing_res.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this coaching relationship",
        )
    
    # Create the review
    review = CoachReview(
        link_id=link_id,
        reviewer_id=acting_user_id,
        coach_id=coach_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    
    try:
        db.add(review)
        await db.commit()
        await db.refresh(review)
        
        # Update rating aggregates
        await _update_coaching_rating_aggregates(db, coach_id)
        await db.commit()
        
        logger.info(
            "review_created",
            review_id=review.id,
            link_id=link_id,
            reviewer_id=acting_user_id,
            coach_id=coach_id,
            rating=payload.rating,
        )
        
        return review
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("review_creation_integrity_error", link_id=link_id, user_id=acting_user_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this coaching relationship",
        ) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("review_creation_failed", link_id=link_id, user_id=acting_user_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create review",
        ) from exc


async def get_reviews_for_coach(
    db: AsyncSession,
    coach_id: str,
    limit: int = 100,
    offset: int = 0,
) -> CoachReviewListResponse:
    """Get paginated reviews for a coach."""
    # Get total count
    count_res = await db.execute(
        select(func.count(CoachReview.id)).where(CoachReview.coach_id == coach_id)
    )
    total = count_res.scalar() or 0
    
    # Get reviews with pagination
    res = await db.execute(
        select(CoachReview)
        .where(CoachReview.coach_id == coach_id)
        .order_by(CoachReview.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    reviews = res.scalars().all()
    
    # Fetch reviewer names from accounts service
    reviewer_ids = [r.reviewer_id for r in reviews]
    reviewer_names = {}
    
    if reviewer_ids:
        try:
            base_url = settings.accounts_service_url.rstrip("/")
            timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
            
            # Build query for multiple users
            ids_query = ",".join(reviewer_ids)
            url = f"{base_url}/users?user_ids={ids_query}"
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                
            if resp.status_code == 200:
                users_data = resp.json()
                for user in users_data:
                    reviewer_names[user['user_id']] = user.get('display_name')
        except Exception as exc:
            logger.warning("reviews_fetch_reviewer_names_failed", coach_id=coach_id, error=str(exc))
    
    # Add reviewer names to reviews
    reviews_with_names = []
    for review in reviews:
        review_dict = {
            'id': review.id,
            'link_id': review.link_id,
            'reviewer_id': review.reviewer_id,
            'reviewer_name': reviewer_names.get(review.reviewer_id),
            'coach_id': review.coach_id,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at,
            'updated_at': review.updated_at,
        }
        reviews_with_names.append(CoachReviewResponse(**review_dict))
    
    return CoachReviewListResponse(
        reviews=reviews_with_names,
        total=total,
        limit=limit,
        offset=offset,
    )
