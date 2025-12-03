import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..database import get_db
from ..dependencies import get_current_user_id
from ..schemas.analytics import PlanAnalyticsItem, PlanAnalyticsResponse

router = APIRouter(prefix="/analytics")
logger = logging.getLogger(__name__)


async def _fetch_workout_instances(workout_id: int, user_id: str) -> List[Dict[str, Any]]:
    base_url = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002").rstrip("/")
    url = f"{base_url}/exercises/instances/workouts/{workout_id}/instances"
    headers = {"X-User-Id": user_id}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
    except Exception as e:
        logger.warning(f"Failed to fetch instances for workout {workout_id}: {e}")
    return []


def _compute_actual_metrics(session: models.WorkoutSession, instances: List[Dict[str, Any]]) -> Dict[str, float]:
    raw_progress = session.progress if isinstance(session.progress, dict) else {}
    raw_completed = raw_progress.get("completed") if isinstance(raw_progress.get("completed"), dict) else {}

    # Build map of instance_id -> set_ids
    completed_map: Dict[int, Set[int]] = {}
    for instance_id_raw, set_ids in raw_completed.items():
        try:
            iid = int(instance_id_raw)
            sids = {int(s) for s in set_ids} if isinstance(set_ids, list) else set()
            if sids:
                completed_map[iid] = sids
        except (ValueError, TypeError):
            continue

    total_effort = 0.0
    total_intensity = 0.0
    total_volume = 0.0
    cnt_effort = 0
    cnt_intensity = 0
    sets_cnt = 0

    # Aggregation by muscles and muscle groups (only for completed sets)
    muscle_volume: Dict[str, float] = {}
    muscle_group_volume: Dict[str, float] = {}

    for inst in instances:
        iid = inst.get("id")
        if iid is None or iid not in completed_map:
            continue

        # Static metadata for this exercise instance
        exercise_def = inst.get("exercise_definition") or {}
        raw_target = exercise_def.get("target_muscles") or []
        raw_synergists = exercise_def.get("synergist_muscles") or []
        target_muscles = [m for m in raw_target if isinstance(m, str) and m]
        synergist_muscles = [m for m in raw_synergists if isinstance(m, str) and m]
        muscle_group = exercise_def.get("muscle_group")

        completed_sets = completed_map[iid]
        for s in inst.get("sets") or []:
            sid = s.get("id")
            if sid is None or sid not in completed_sets:
                continue

            effort = s.get("effort") or s.get("rpe")
            intensity = s.get("intensity")
            volume = s.get("volume") or s.get("reps")  # Fallback for display if volume/reps ambiguous

            # Normalize and accumulate base metrics
            try:
                if effort is not None:
                    total_effort += float(effort)
                    cnt_effort += 1
                if intensity is not None:
                    total_intensity += float(intensity)
                    cnt_intensity += 1
                if volume is not None:
                    v = float(volume)
                    total_volume += v
                    # Per-muscle-group aggregation
                    if isinstance(muscle_group, str) and muscle_group:
                        muscle_group_volume[muscle_group] = muscle_group_volume.get(muscle_group, 0.0) + v
                    # Per-muscle aggregation: distribute volume across primary/synergist muscles
                    muscles_weights = []  # list[tuple[str, float]]
                    for m in target_muscles:
                        muscles_weights.append((m, 1.0))
                    for m in synergist_muscles:
                        muscles_weights.append((m, 0.5))
                    if muscles_weights:
                        total_w = sum(w for _, w in muscles_weights if w > 0)
                        if total_w > 0:
                            for m, w in muscles_weights:
                                if w <= 0:
                                    continue
                                share = v * (w / total_w)
                                muscle_volume[m] = muscle_volume.get(m, 0.0) + share
                sets_cnt += 1
            except (ValueError, TypeError):
                # Best-effort only: skip malformed values
                pass

    metrics: Dict[str, float] = {
        "effort_avg": (total_effort / cnt_effort) if cnt_effort > 0 else 0.0,
        "intensity_avg": (total_intensity / cnt_intensity) if cnt_intensity > 0 else 0.0,
        "volume_sum": total_volume,
        "sets_count": float(sets_cnt),
    }

    # Flatten muscle metrics into scalar keys to satisfy Dict[str, float]
    for mg, v in muscle_group_volume.items():
        metrics[f"muscle_group:{mg}"] = v
    for m, v in muscle_volume.items():
        metrics[f"muscle:{m}"] = v

    return metrics


@router.get("/completed", response_model=PlanAnalyticsResponse)
async def get_completed_workouts_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get aggregated metrics (volume, intensity, effort) for completed workouts
    in the last N days.
    """
    from datetime import timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    # Fetch completed workouts in range
    q = (
        select(models.Workout)
        .where(models.Workout.user_id == user_id)
        .where(models.Workout.status == "completed")
        .where(models.Workout.completed_at >= cutoff_date)
        .order_by(models.Workout.completed_at.asc())
    )

    result = await db.execute(q)
    workouts: List[models.Workout] = list(result.scalars().all())

    items: List[PlanAnalyticsItem] = []

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
    if ex_list:
        set_q = select(models.WorkoutSet).where(models.WorkoutSet.exercise_id.in_([ex.id for ex in ex_list]))
        set_res = await db.execute(set_q)
        set_list: List[models.WorkoutSet] = list(set_res.scalars().all())
        sets_by_ex: Dict[int, List[models.WorkoutSet]] = {}
        for s in set_list:
            sets_by_ex.setdefault(s.exercise_id, []).append(s)
    else:
        sets_by_ex = {}

    for w in workouts:
        wid = int(w.id)
        # For history, order_index might not be relevant across different plans, but we keep it if exists
        order_index = w.plan_order_index
        date = w.completed_at or w.scheduled_for

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

    # NEW: Fetch sessions for these workouts to find completed ones
    session_q = select(models.WorkoutSession).where(
        models.WorkoutSession.workout_id.in_(workout_ids), models.WorkoutSession.status.in_(["finished", "completed"])
    )
    session_res = await db.execute(session_q)
    sessions = session_res.scalars().all()
    sessions_by_wid = {s.workout_id: s for s in sessions}

    # NEW: Async fetch actual instances for completed workouts
    fetch_tasks = []
    wids_to_fetch = list(sessions_by_wid.keys())
    for wid in wids_to_fetch:
        fetch_tasks.append(_fetch_workout_instances(wid, user_id))

    fetched_results = await asyncio.gather(*fetch_tasks)
    instances_by_wid = dict(zip(wids_to_fetch, fetched_results))

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

        # NEW: Calculate actual metrics if session exists
        actual_metrics = None
        if wid in sessions_by_wid:
            sess = sessions_by_wid[wid]
            insts = instances_by_wid.get(wid, [])
            actual_metrics = _compute_actual_metrics(sess, insts)

        items.append(
            PlanAnalyticsItem(
                workout_id=wid, order_index=order_index, date=date, metrics=metrics, actual_metrics=actual_metrics
            )
        )

    return PlanAnalyticsResponse(items=items)
