from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..schemas.analytics import (
    AthleteDetailedAnalyticsResponse,
    CoachAthletesAnalyticsResponse,
    CoachSummaryAnalyticsResponse,
)
from ..services.analytics_service import (
    get_athlete_detailed_analytics,
    get_coach_athletes_analytics,
    get_coach_summary_analytics,
)

router = APIRouter(prefix="/crm/analytics", tags=["crm-analytics"])


@router.get("/coaches/my/athletes", response_model=CoachAthletesAnalyticsResponse)
async def get_my_athletes_analytics(
    weeks: int = Query(12, ge=1, le=104),
    inactive_after_days: int = Query(14, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachAthletesAnalyticsResponse:
    return await get_coach_athletes_analytics(
        db=db,
        coach_id=user_id,
        weeks=weeks,
        inactive_after_days=inactive_after_days,
        limit=limit,
        offset=offset,
    )


@router.get("/coaches/my/summary", response_model=CoachSummaryAnalyticsResponse)
async def get_my_summary_analytics(
    weeks: int = Query(12, ge=1, le=104),
    inactive_after_days: int = Query(14, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CoachSummaryAnalyticsResponse:
    return await get_coach_summary_analytics(
        db=db,
        coach_id=user_id,
        weeks=weeks,
        inactive_after_days=inactive_after_days,
        limit=limit,
        offset=offset,
    )


@router.get("/athletes/{athlete_id}", response_model=AthleteDetailedAnalyticsResponse)
async def get_athlete_detailed(
    athlete_id: str,
    weeks: int = Query(12, ge=1, le=104),
    inactive_after_days: int = Query(14, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AthleteDetailedAnalyticsResponse:
    return await get_athlete_detailed_analytics(
        db=db,
        current_user_id=user_id,
        athlete_id=athlete_id,
        weeks=weeks,
        inactive_after_days=inactive_after_days,
    )
