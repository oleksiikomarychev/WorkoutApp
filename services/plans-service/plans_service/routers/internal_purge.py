import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models.calendar import (
    AppliedCalendarPlan,
    AppliedMesocycle,
    AppliedMicrocycle,
    AppliedPlanWorkout,
    AppliedWorkout,
    CalendarPlan,
    PlanAdopter,
)
from ..models.templates import MesocycleTemplate

router = APIRouter(prefix="/internal/users", tags=["internal"])


def _deleted_user_id(user_id: str) -> str:
    import hashlib

    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
    return f"deleted:{digest}"


@router.post("/{user_id}/purge")
async def purge_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> dict[str, str]:
    expected_secret = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    tombstone = _deleted_user_id(user_id)

    applied_plan_ids = select(AppliedCalendarPlan.id).where(AppliedCalendarPlan.user_id == user_id)
    applied_mesocycle_ids = select(AppliedMesocycle.id).where(AppliedMesocycle.applied_plan_id.in_(applied_plan_ids))
    applied_microcycle_ids = select(AppliedMicrocycle.id).where(
        AppliedMicrocycle.applied_mesocycle_id.in_(applied_mesocycle_ids)
    )

    await db.execute(delete(AppliedWorkout).where(AppliedWorkout.applied_microcycle_id.in_(applied_microcycle_ids)))
    await db.execute(delete(AppliedMicrocycle).where(AppliedMicrocycle.id.in_(applied_microcycle_ids)))
    await db.execute(delete(AppliedMesocycle).where(AppliedMesocycle.id.in_(applied_mesocycle_ids)))
    await db.execute(delete(AppliedPlanWorkout).where(AppliedPlanWorkout.applied_plan_id.in_(applied_plan_ids)))
    await db.execute(delete(AppliedCalendarPlan).where(AppliedCalendarPlan.id.in_(applied_plan_ids)))

    await db.execute(delete(PlanAdopter).where(PlanAdopter.adopter_user_id == user_id))
    await db.execute(delete(MesocycleTemplate).where(MesocycleTemplate.user_id == user_id))

    await db.execute(
        delete(CalendarPlan).where(
            CalendarPlan.user_id == user_id,
            CalendarPlan.is_public.is_(False),
            CalendarPlan.root_plan_id != CalendarPlan.id,
        )
    )
    await db.execute(
        delete(CalendarPlan).where(
            CalendarPlan.user_id == user_id,
            CalendarPlan.is_public.is_(False),
            CalendarPlan.root_plan_id == CalendarPlan.id,
        )
    )

    await db.execute(
        update(CalendarPlan)
        .where(CalendarPlan.user_id == user_id, CalendarPlan.is_public.is_(True))
        .values(user_id=tombstone)
    )

    await db.commit()

    return {"status": "ok"}
