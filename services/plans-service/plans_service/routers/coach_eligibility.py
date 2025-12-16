from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..models.calendar import CalendarPlan, PlanAdopter
from ..schemas.calendar_plan import CoachingEligibilityResponse, PlanAdoptersListResponse, PlanAdoptersStatsResponse

router = APIRouter(prefix="/adoption")

COACHING_ELIGIBILITY_THRESHOLD = 100


@router.get("/root-plans/{root_plan_id}/adopters", response_model=PlanAdoptersListResponse)
async def list_root_plan_adopters(
    root_plan_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> PlanAdoptersListResponse:
    count_stmt = select(func.count()).select_from(PlanAdopter).where(PlanAdopter.root_plan_id == root_plan_id)
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        select(PlanAdopter.adopter_user_id)
        .where(PlanAdopter.root_plan_id == root_plan_id)
        .order_by(PlanAdopter.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    adopters = [str(x) for x in (await db.execute(stmt)).scalars().all()]

    return PlanAdoptersListResponse(
        root_plan_id=root_plan_id,
        total=total,
        limit=limit,
        offset=offset,
        adopters=adopters,
    )


@router.get("/root-plans/{root_plan_id}/stats", response_model=PlanAdoptersStatsResponse)
async def get_root_plan_adopters_stats(
    root_plan_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> PlanAdoptersStatsResponse:
    stmt = select(func.count()).select_from(PlanAdopter).where(PlanAdopter.root_plan_id == root_plan_id)
    unique_adopters = int((await db.execute(stmt)).scalar_one())
    return PlanAdoptersStatsResponse(root_plan_id=root_plan_id, unique_adopters=unique_adopters)


@router.get("/coaching-eligibility/me", response_model=CoachingEligibilityResponse)
async def get_my_coaching_eligibility(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> CoachingEligibilityResponse:
    roots_stmt = select(CalendarPlan.id).where(
        CalendarPlan.user_id == user_id,
        CalendarPlan.id == CalendarPlan.root_plan_id,
    )
    root_ids = [int(x) for x in (await db.execute(roots_stmt)).scalars().all()]

    if not root_ids:
        return CoachingEligibilityResponse(
            eligible=False,
            threshold=COACHING_ELIGIBILITY_THRESHOLD,
            max_unique_adopters=0,
            best_root_plan_id=None,
        )

    stmt = (
        select(PlanAdopter.root_plan_id, func.count().label("c"))
        .where(PlanAdopter.root_plan_id.in_(root_ids), PlanAdopter.adopter_user_id != user_id)
        .group_by(PlanAdopter.root_plan_id)
        .order_by(func.count().desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()

    if not row:
        return CoachingEligibilityResponse(
            eligible=False,
            threshold=COACHING_ELIGIBILITY_THRESHOLD,
            max_unique_adopters=0,
            best_root_plan_id=None,
        )

    best_root_plan_id, max_unique_adopters = int(row[0]), int(row[1])
    return CoachingEligibilityResponse(
        eligible=max_unique_adopters > COACHING_ELIGIBILITY_THRESHOLD,
        threshold=COACHING_ELIGIBILITY_THRESHOLD,
        max_unique_adopters=max_unique_adopters,
        best_root_plan_id=best_root_plan_id,
    )
