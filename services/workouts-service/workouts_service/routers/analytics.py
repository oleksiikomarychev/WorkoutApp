from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..database import get_db
from ..dependencies import get_current_user_id
from ..schemas.analytics import PlanAnalyticsItem, PlanAnalyticsResponse

router = APIRouter(prefix="/analytics")


@router.get("/in-plan", response_model=PlanAnalyticsResponse)
async def get_plan_analytics(
    applied_plan_id: int = Query(..., ge=1),
    from_dt: Optional[str] = Query(None, alias="from"),
    to_dt: Optional[str] = Query(None, alias="to"),
    group_by: Optional[str] = Query("order", pattern="^(order|date)$"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    # Parse dates
    def parse_iso(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    frm = parse_iso(from_dt)
    to = parse_iso(to_dt)

    # Fetch workouts for the plan
    q = (
        select(models.Workout)
        .where(models.Workout.user_id == user_id)
        .where(models.Workout.applied_plan_id == applied_plan_id)
    )
    if frm:
        q = q.where(models.Workout.scheduled_for >= frm)
    if to:
        q = q.where(models.Workout.scheduled_for <= to)
    # Order deterministically by plan_order_index then id
    q = q.order_by(models.Workout.plan_order_index.asc(), models.Workout.id.asc())

    result = await db.execute(q)
    workouts: List[models.Workout] = list(result.scalars().all())

    items: List[PlanAnalyticsItem] = []

    # Aggregate per workout using WorkoutExercises/Sets
    # We rely on relationships but we avoid lazy IO by separate fetch of exercises/sets
    if not workouts:
        return PlanAnalyticsResponse(items=[])

    workout_ids = [w.id for w in workouts if w.id is not None]
    # Fetch exercises
    ex_q = (
        select(models.WorkoutExercise)
        .where(models.WorkoutExercise.user_id == user_id)
        .where(models.WorkoutExercise.workout_id.in_(workout_ids))
    )
    ex_res = await db.execute(ex_q)
    ex_list: List[models.WorkoutExercise] = list(ex_res.scalars().all())
    ex_by_w: Dict[int, List[models.WorkoutExercise]] = {}
    for ex in ex_list:
        ex_by_w.setdefault(ex.workout_id, []).append(ex)

    # Fetch sets
    set_q = select(models.WorkoutSet).where(models.WorkoutSet.exercise_id.in_([ex.id for ex in ex_list]))
    set_res = await db.execute(set_q)
    set_list: List[models.WorkoutSet] = list(set_res.scalars().all())
    sets_by_ex: Dict[int, List[models.WorkoutSet]] = {}
    for s in set_list:
        sets_by_ex.setdefault(s.exercise_id, []).append(s)

    for w in workouts:
        wid = int(w.id)
        order_index = w.plan_order_index
        date = w.scheduled_for
        total_effort = 0.0
        total_intensity = 0.0
        total_volume = 0.0
        cnt_effort = 0
        cnt_intensity = 0
        sets_cnt = 0
        for ex in ex_by_w.get(wid, []):
            for s in sets_by_ex.get(ex.id, []):
                if s.effort is not None:
                    total_effort += float(s.effort)
                    cnt_effort += 1
                if s.intensity is not None:
                    total_intensity += float(s.intensity)
                    cnt_intensity += 1
                if s.volume is not None:
                    total_volume += float(s.volume)
                sets_cnt += 1
        metrics = {
            "effort_avg": (total_effort / cnt_effort) if cnt_effort > 0 else 0.0,
            "intensity_avg": (total_intensity / cnt_intensity) if cnt_intensity > 0 else 0.0,
            "volume_sum": total_volume,
            "sets_count": float(sets_cnt),
        }
        items.append(PlanAnalyticsItem(workout_id=wid, order_index=order_index, date=date, metrics=metrics))

    return PlanAnalyticsResponse(items=items)
