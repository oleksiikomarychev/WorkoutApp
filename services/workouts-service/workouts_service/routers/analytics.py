import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..database import get_db
from ..dependencies import get_current_user_id
from ..schemas.analytics import PlanAnalyticsItem, PlanAnalyticsResponse
from ..schemas.profile import DayActivity, ProfileAggregatesResponse, SessionLite

router = APIRouter(prefix="/analytics")
logger = logging.getLogger(__name__)


async def _fetch_workout_instances(workout_id: int, user_id: str) -> list[dict[str, Any]]:
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
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
        logger.warning(f"Failed to fetch instances for workout {workout_id}: {e}")
    return []


def _build_set_volume_index(instances: list[dict[str, Any]]) -> tuple[dict[int, float], float]:
    set_volume: dict[int, float] = {}
    total = 0.0
    for inst in instances or []:
        for s in inst.get("sets", []) or []:
            sid = s.get("id")

            reps_raw = s.get("reps")
            weight_raw = s.get("weight")
            volume_raw = s.get("volume")

            reps = 0.0
            weight: float | None = None
            try:
                if reps_raw is not None:
                    reps = float(reps_raw)
            except (TypeError, ValueError):
                reps = 0.0
            try:
                if weight_raw is not None:
                    weight = float(weight_raw)
            except (TypeError, ValueError):
                weight = None

            volume: float | None = None
            if weight is not None and reps > 0:
                volume = round(reps * weight, 2)

            if volume is None:
                try:
                    volume = float(volume_raw)
                except (TypeError, ValueError):
                    volume = None

            if volume is None and reps > 0 and weight is None:
                volume = round(reps, 2)

            v = volume if volume is not None else 0.0

            if isinstance(sid, int):
                set_volume[sid] = v
            total += v
    return set_volume, total


def _compute_actual_metrics(session: models.WorkoutSession, instances: list[dict[str, Any]]) -> dict[str, float]:
    raw_progress = session.progress if isinstance(session.progress, dict) else {}
    raw_completed = raw_progress.get("completed") if isinstance(raw_progress.get("completed"), dict) else {}

    completed_map: dict[int, set[int]] = {}
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

    muscle_volume: dict[str, float] = {}
    muscle_group_volume: dict[str, float] = {}

    for inst in instances:
        iid = inst.get("id")
        if iid is None or iid not in completed_map:
            continue

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
            volume = s.get("volume") or s.get("reps")

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

                    if isinstance(muscle_group, str) and muscle_group:
                        muscle_group_volume[muscle_group] = muscle_group_volume.get(muscle_group, 0.0) + v

                    muscles_weights = []
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
                pass

    metrics: dict[str, float] = {
        "effort_avg": (total_effort / cnt_effort) if cnt_effort > 0 else 0.0,
        "intensity_avg": (total_intensity / cnt_intensity) if cnt_intensity > 0 else 0.0,
        "volume_sum": total_volume,
        "sets_count": float(sets_cnt),
    }

    for mg, v in muscle_group_volume.items():
        metrics[f"muscle_group:{mg}"] = v
    for m, v in muscle_volume.items():
        metrics[f"muscle:{m}"] = v

    return metrics


@router.get("/profile/aggregates", response_model=ProfileAggregatesResponse)
async def get_profile_aggregates(
    weeks: int = Query(48, ge=1, le=104),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    now = datetime.utcnow()
    grid_end = datetime(now.year, now.month, now.day)
    grid_start = grid_end - timedelta(days=weeks * 7 - 1)

    result = await db.execute(
        select(models.WorkoutSession).where(
            models.WorkoutSession.user_id == user_id,
            models.WorkoutSession.finished_at.isnot(None),
        )
    )
    sessions: list[models.WorkoutSession] = list(result.scalars().all())

    if not sessions:
        return ProfileAggregatesResponse(
            generated_at=now,
            weeks=weeks,
            total_workouts=0,
            total_volume=0.0,
            active_days=0,
            max_day_volume=0.0,
            activity_map={},
            completed_sessions=[],
        )

    completed = sorted(
        sessions,
        key=lambda s: s.started_at or datetime.min,
        reverse=True,
    )

    unique_wids: list[int] = []
    seen: set[int] = set()
    for s in completed:
        wid = s.workout_id
        if isinstance(wid, int) and wid not in seen:
            seen.add(wid)
            unique_wids.append(wid)

    wid_to_index: dict[int, dict[int, float]] = {}
    wid_to_total: dict[int, float] = {}

    sem = asyncio.Semaphore(6)

    async def _build_for_wid(wid: int) -> None:
        async with sem:
            instances = await _fetch_workout_instances(wid, user_id)
            set_idx, total = _build_set_volume_index(instances)
            wid_to_index[wid] = set_idx
            wid_to_total[wid] = total

    if unique_wids:
        await asyncio.gather(*[_build_for_wid(wid) for wid in unique_wids])

    activity_map: dict[str, dict[str, float]] = {}
    total_volume = 0.0

    for s in completed:
        started_at = s.started_at
        if not started_at:
            continue
        day_key = started_at.date().isoformat()

        day_date = started_at.date()
        if not (grid_start.date() <= day_date <= grid_end.date()):
            continue

        wid = s.workout_id
        progress = s.progress or {}
        completed_map = progress.get("completed") or {}
        session_volume = 0.0

        if isinstance(wid, int):
            set_lookup = wid_to_index.get(wid) or {}

            if not isinstance(completed_map, dict) or not any(
                isinstance(v, list) and v for v in completed_map.values()
            ):
                session_volume = wid_to_total.get(wid, 0.0)
            else:
                for v in completed_map.values():
                    if isinstance(v, list):
                        for sid in v:
                            if isinstance(sid, int):
                                session_volume += float(set_lookup.get(sid, 0.0))

        total_volume += session_volume
        cur = activity_map.get(day_key)
        if not cur:
            activity_map[day_key] = {"session_count": 1, "volume": session_volume}
        else:
            cur["session_count"] += 1
            cur["volume"] += session_volume

    max_day_volume = 0.0
    for v in activity_map.values():
        vol = float(v.get("volume", 0.0))
        if vol > max_day_volume:
            max_day_volume = vol

    last_sessions: list[SessionLite] = []
    for s in completed[:limit]:
        last_sessions.append(
            SessionLite(
                id=int(s.id),
                workout_id=int(s.workout_id),
                started_at=s.started_at,
                finished_at=s.finished_at,
                status=str(s.status or ""),
            )
        )

    typed_activity: dict[str, DayActivity] = {
        k: DayActivity(
            session_count=int(v.get("session_count", 0)),
            volume=float(v.get("volume", 0.0)),
        )
        for k, v in activity_map.items()
    }

    active_days = len({(s.started_at.date().isoformat()) for s in completed if s.started_at})

    total_workouts = len(seen)

    return ProfileAggregatesResponse(
        generated_at=now,
        weeks=weeks,
        total_workouts=total_workouts,
        total_volume=float(total_volume),
        active_days=active_days,
        max_day_volume=float(max_day_volume),
        activity_map=typed_activity,
        completed_sessions=last_sessions,
    )


@router.get("/completed", response_model=PlanAnalyticsResponse)
async def get_completed_workouts_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    from datetime import timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    q = (
        select(models.Workout)
        .where(models.Workout.user_id == user_id)
        .where(models.Workout.status == "completed")
        .where(models.Workout.completed_at >= cutoff_date)
        .order_by(models.Workout.completed_at.asc())
    )

    result = await db.execute(q)
    workouts: list[models.Workout] = list(result.scalars().all())

    items: list[PlanAnalyticsItem] = []

    if not workouts:
        return PlanAnalyticsResponse(items=[])

    workout_ids = [w.id for w in workouts if w.id is not None]

    ex_q = (
        select(models.WorkoutExercise)
        .where(models.WorkoutExercise.user_id == user_id)
        .where(models.WorkoutExercise.workout_id.in_(workout_ids))
    )
    ex_res = await db.execute(ex_q)
    ex_list: list[models.WorkoutExercise] = list(ex_res.scalars().all())
    ex_by_w: dict[int, list[models.WorkoutExercise]] = {}
    for ex in ex_list:
        ex_by_w.setdefault(ex.workout_id, []).append(ex)

    if ex_list:
        set_q = select(models.WorkoutSet).where(models.WorkoutSet.exercise_id.in_([ex.id for ex in ex_list]))
        set_res = await db.execute(set_q)
        set_list: list[models.WorkoutSet] = list(set_res.scalars().all())
        sets_by_ex: dict[int, list[models.WorkoutSet]] = {}
        for s in set_list:
            sets_by_ex.setdefault(s.exercise_id, []).append(s)
    else:
        sets_by_ex = {}

    for w in workouts:
        wid = int(w.id)

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
    from_dt: str | None = Query(None, alias="from"),
    to_dt: str | None = Query(None, alias="to"),
    group_by: str | None = Query("order", pattern="^(order|date)$"),
    include_actual: bool = Query(
        False,
        description=(
            "If true, include realized per-workout actual_metrics based on completed sessions "
            "and exercises-service instances. When false, only planned metrics computed from "
            "WorkoutExercise/WorkoutSet are returned."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    def parse_iso(s: str | None) -> datetime | None:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None

    frm = parse_iso(from_dt)
    to = parse_iso(to_dt)

    q = (
        select(models.Workout)
        .where(models.Workout.user_id == user_id)
        .where(models.Workout.applied_plan_id == applied_plan_id)
    )
    if frm:
        q = q.where(models.Workout.scheduled_for >= frm)
    if to:
        q = q.where(models.Workout.scheduled_for <= to)

    q = q.order_by(models.Workout.plan_order_index.asc(), models.Workout.id.asc())

    result = await db.execute(q)
    workouts: list[models.Workout] = list(result.scalars().all())

    items: list[PlanAnalyticsItem] = []

    if not workouts:
        return PlanAnalyticsResponse(items=[])

    workout_ids = [w.id for w in workouts if w.id is not None]

    ex_q = (
        select(models.WorkoutExercise)
        .where(models.WorkoutExercise.user_id == user_id)
        .where(models.WorkoutExercise.workout_id.in_(workout_ids))
    )
    ex_res = await db.execute(ex_q)
    ex_list: list[models.WorkoutExercise] = list(ex_res.scalars().all())
    ex_by_w: dict[int, list[models.WorkoutExercise]] = {}
    for ex in ex_list:
        ex_by_w.setdefault(ex.workout_id, []).append(ex)

    set_q = select(models.WorkoutSet).where(models.WorkoutSet.exercise_id.in_([ex.id for ex in ex_list]))
    set_res = await db.execute(set_q)
    set_list: list[models.WorkoutSet] = list(set_res.scalars().all())
    sets_by_ex: dict[int, list[models.WorkoutSet]] = {}
    for s in set_list:
        sets_by_ex.setdefault(s.exercise_id, []).append(s)

    sessions_by_wid: dict[int, models.WorkoutSession] = {}
    instances_by_wid: dict[int, list[dict[str, Any]]] = {}

    if include_actual:
        session_q = select(models.WorkoutSession).where(
            models.WorkoutSession.workout_id.in_(workout_ids),
            models.WorkoutSession.status.in_(["finished", "completed"]),
        )
        session_res = await db.execute(session_q)
        sessions = session_res.scalars().all()
        sessions_by_wid = {s.workout_id: s for s in sessions}

        if sessions_by_wid:
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
