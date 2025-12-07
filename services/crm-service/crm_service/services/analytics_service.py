from __future__ import annotations

from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.relationships import CoachAthleteLink
from ..schemas.analytics import (
    AthleteDetailedAnalyticsResponse,
    AthleteTrainingSummary,
    AthleteTrendPoint,
    CoachAthletesAnalyticsResponse,
    CoachSummaryAnalyticsResponse,
)


async def _fetch_sessions_for_athlete(athlete_id: str, weeks: int) -> list[dict]:
    base_url = settings.workouts_service_url.rstrip("/")
    url = f"{base_url}/workouts/sessions/history/all"
    headers = {"X-User-Id": athlete_id}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            return []
        data = resp.json() or []
        if not isinstance(data, list):
            return []
    cutoff = datetime.utcnow() - timedelta(weeks=weeks)
    sessions: list[dict] = []
    for s in data:
        started_at = s.get("started_at")
        if not started_at:
            continue
        try:
            dt = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        except Exception:
            continue
        if dt >= cutoff:
            sessions.append({**s, "_parsed_started_at": dt})
    return sessions


async def _fetch_active_plan_for_athlete(athlete_id: str) -> tuple[int | None, str | None]:
    base_url = settings.plans_service_url.rstrip("/")
    url = f"{base_url}/plans/applied-plans/active"
    headers = {"X-User-Id": athlete_id}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            return None, None
        data = resp.json() or None
        if not isinstance(data, dict):
            return None, None
    plan_id = data.get("id") if isinstance(data.get("id"), int) else None
    plan_name = data.get("calendar_plan", {}).get("name") if isinstance(data.get("calendar_plan"), dict) else None
    return plan_id, plan_name


async def _fetch_plan_items_for_athlete(
    athlete_id: str,
    applied_plan_id: int,
    weeks: int,
    now: datetime | None = None,
) -> list[dict]:
    base_url = settings.workouts_service_url.rstrip("/")
    url = f"{base_url}/workouts/analytics/in-plan"
    headers = {"X-User-Id": athlete_id}

    if now is None:
        now = datetime.utcnow()
    cutoff = now - timedelta(weeks=weeks)

    params = {
        "applied_plan_id": applied_plan_id,
        "from": cutoff.isoformat(),
        "to": now.isoformat(),
        "include_actual": "true",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers, params=params, follow_redirects=True)
        if resp.status_code != 200:
            return []
        data = resp.json() or {}
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
    return items


async def _fetch_plan_volume_for_athlete(athlete_id: str, applied_plan_id: int, weeks: int) -> float | None:
    items = await _fetch_plan_items_for_athlete(athlete_id, applied_plan_id=applied_plan_id, weeks=weeks)
    if not items:
        return None
    _, _, _, total_volume = _aggregate_plan_metrics(items)
    return total_volume


def _aggregate_plan_metrics(
    plan_items: list[dict],
) -> tuple[float | None, float | None, dict[str, float] | None, float | None]:
    total_intensity = 0.0
    total_intensity_weight = 0.0
    total_effort = 0.0
    total_effort_weight = 0.0
    total_volume = 0.0
    rpe_bins: dict[int, float] = {i: 0.0 for i in range(1, 11)}
    total_rpe_weight = 0.0

    for it in plan_items:
        metrics = it.get("metrics") or {}
        intensity = metrics.get("intensity_avg")
        effort = metrics.get("effort_avg")
        volume = metrics.get("volume_sum")
        sets_count = metrics.get("sets_count")

        try:
            v = float(volume)
        except Exception:
            v = 0.0
        total_volume += v

        weight = 0.0
        try:
            weight = float(sets_count)
        except Exception:
            pass

        if intensity is not None and weight > 0.0:
            try:
                x = float(intensity)
            except Exception:
                x = None
            if x is not None:
                total_intensity += x * weight
                total_intensity_weight += weight

        if effort is not None and weight > 0.0:
            try:
                e = float(effort)
            except Exception:
                e = None
            if e is not None:
                total_effort += e * weight
                total_effort_weight += weight
                rpe_int = int(round(e))
                if rpe_int < 1:
                    rpe_int = 1
                elif rpe_int > 10:
                    rpe_int = 10
                rpe_bins[rpe_int] += weight
                total_rpe_weight += weight

    avg_intensity = total_intensity / total_intensity_weight if total_intensity_weight > 0.0 else None
    avg_effort = total_effort / total_effort_weight if total_effort_weight > 0.0 else None

    if total_rpe_weight > 0.0:
        rpe_distribution = {str(i): (rpe_bins[i] / total_rpe_weight) for i in range(1, 11)}
    else:
        rpe_distribution = None

    return avg_intensity, avg_effort, rpe_distribution, total_volume


def _aggregate_muscle_metrics_from_actual(
    plan_items: list[dict],
) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    group_totals: dict[str, float] = {}
    muscle_totals: dict[str, float] = {}
    for it in plan_items:
        actual = it.get("actual_metrics")
        if not isinstance(actual, dict):
            continue

        for key, value in actual.items():
            try:
                v = float(value)
            except Exception:
                continue

            if key.startswith("muscle_group:"):
                mg = key.split(":", 1)[1]
                if not mg:
                    continue
                group_totals[mg] = group_totals.get(mg, 0.0) + v
            elif key.startswith("muscle:"):
                m = key.split(":", 1)[1]
                if not m:
                    continue
                muscle_totals[m] = muscle_totals.get(m, 0.0) + v

    return (group_totals or None, muscle_totals or None)


def _classify_athlete_segment(
    sessions_per_week: float | None,
    plan_adherence: float | None,
    days_since_last_workout: int | None,
    inactive_after_days: int,
    has_plan: bool,
    sessions_count: int,
) -> str:
    if sessions_count < 2 and not has_plan:
        return "new"

    s = float(sessions_per_week or 0.0)
    adh = float(plan_adherence) if plan_adherence is not None else 0.0
    d = days_since_last_workout

    if s >= 3.0 and adh >= 0.8 and (d is None or d <= 3):
        return "top_performer"

    if s < 1.0:
        return "at_risk"

    if plan_adherence is not None and plan_adherence < 0.3:
        return "at_risk"

    if d is not None and d >= inactive_after_days:
        return "at_risk"

    return "on_track"


async def get_coach_athletes_analytics(
    db: AsyncSession,
    coach_id: str,
    weeks: int,
    inactive_after_days: int,
    limit: int,
    offset: int,
) -> CoachAthletesAnalyticsResponse:
    stmt = select(CoachAthleteLink).where(CoachAthleteLink.coach_id == coach_id)
    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    links: list[CoachAthleteLink] = list(res.scalars().all())

    generated_at = datetime.utcnow()
    summaries: list[AthleteTrainingSummary] = []

    for link in links:
        athlete_id = link.athlete_id
        sessions = await _fetch_sessions_for_athlete(athlete_id, weeks=weeks)
        sessions_count = len(sessions)
        last_dt: datetime | None = None
        total_volume: float | None = None
        avg_intensity: float | None = None
        avg_effort: float | None = None
        rpe_distribution: dict[str, float] | None = None
        plan_adherence: float | None = None

        if sessions:
            sessions.sort(key=lambda x: x.get("_parsed_started_at") or datetime.min, reverse=True)
            last_dt = sessions[0].get("_parsed_started_at")

        days_since_last: int | None = None
        if last_dt is not None:
            days_since_last = (generated_at.date() - last_dt.date()).days

        sessions_per_week: float | None = None
        if weeks > 0:
            sessions_per_week = float(sessions_count) / float(weeks)

        plan_id, plan_name = await _fetch_active_plan_for_athlete(athlete_id)

        plan_items: list[dict] = []
        if plan_id is not None:
            plan_items = await _fetch_plan_items_for_athlete(
                athlete_id,
                applied_plan_id=plan_id,
                weeks=weeks,
                now=generated_at,
            )
            avg_intensity, avg_effort, rpe_distribution, total_volume = _aggregate_plan_metrics(plan_items)

            planned_workout_ids = {int(it.get("workout_id")) for it in plan_items if it.get("workout_id") is not None}
            finished_workout_ids: set[int] = set()
            for s in sessions:
                status = s.get("status")
                if isinstance(status, str) and status.lower() != "finished":
                    continue
                wid = s.get("workout_id")
                try:
                    wid_int = int(wid)
                except Exception:
                    continue
                finished_workout_ids.add(wid_int)
            if planned_workout_ids:
                completed_in_plan = len(planned_workout_ids & finished_workout_ids)
                plan_adherence = float(completed_in_plan) / float(len(planned_workout_ids))

        segment = _classify_athlete_segment(
            sessions_per_week=sessions_per_week,
            plan_adherence=plan_adherence,
            days_since_last_workout=days_since_last,
            inactive_after_days=inactive_after_days,
            has_plan=plan_id is not None,
            sessions_count=sessions_count,
        )

        summaries.append(
            AthleteTrainingSummary(
                athlete_id=athlete_id,
                last_workout_at=last_dt,
                sessions_count=sessions_count,
                total_volume=total_volume,
                active_plan_id=plan_id,
                active_plan_name=plan_name,
                days_since_last_workout=days_since_last,
                sessions_per_week=sessions_per_week,
                plan_adherence=plan_adherence,
                avg_intensity=avg_intensity,
                avg_effort=avg_effort,
                rpe_distribution=rpe_distribution,
                segment=segment,
            )
        )

    active_links = sum(1 for link in links if (link.status or "").lower() == "active")

    return CoachAthletesAnalyticsResponse(
        coach_id=coach_id,
        generated_at=generated_at,
        weeks=weeks,
        total_athletes=len(links),
        active_links=active_links,
        athletes=summaries,
    )


async def get_coach_summary_analytics(
    db: AsyncSession,
    coach_id: str,
    weeks: int,
    inactive_after_days: int,
    limit: int,
    offset: int,
) -> CoachSummaryAnalyticsResponse:
    detailed = await get_coach_athletes_analytics(
        db=db,
        coach_id=coach_id,
        weeks=weeks,
        inactive_after_days=inactive_after_days,
        limit=limit,
        offset=offset,
    )

    inactive_threshold = inactive_after_days
    total_sessions = sum(a.sessions_count for a in detailed.athletes)
    total_weeks = max(weeks, 1)
    avg_sessions_per_week = float(total_sessions) / float(total_weeks) if total_sessions > 0 else 0.0

    inactive_athletes_count = 0
    total_plan_adherence = 0.0
    count_plan_adherence = 0
    total_intensity = 0.0
    count_intensity = 0
    total_effort = 0.0
    count_effort = 0
    segment_counts: dict[str, int] = {}

    for a in detailed.athletes:
        if a.sessions_count == 0:
            inactive_athletes_count += 1
        elif a.days_since_last_workout is not None and a.days_since_last_workout >= inactive_threshold:
            inactive_athletes_count += 1

        if a.plan_adherence is not None:
            total_plan_adherence += a.plan_adherence
            count_plan_adherence += 1

        if a.avg_intensity is not None:
            total_intensity += a.avg_intensity
            count_intensity += 1

        if a.avg_effort is not None:
            total_effort += a.avg_effort
            count_effort += 1

        if a.segment:
            segment_counts[a.segment] = segment_counts.get(a.segment, 0) + 1

    avg_plan_adherence = total_plan_adherence / count_plan_adherence if count_plan_adherence > 0 else 0.0
    avg_intensity = total_intensity / count_intensity if count_intensity > 0 else 0.0
    avg_effort = total_effort / count_effort if count_effort > 0 else 0.0

    return CoachSummaryAnalyticsResponse(
        coach_id=coach_id,
        generated_at=detailed.generated_at,
        weeks=detailed.weeks,
        total_athletes=detailed.total_athletes,
        active_links=detailed.active_links,
        avg_sessions_per_week=avg_sessions_per_week,
        inactive_athletes_count=inactive_athletes_count,
        avg_plan_adherence=avg_plan_adherence,
        avg_intensity=avg_intensity,
        avg_effort=avg_effort,
        segment_counts=segment_counts,
    )


async def get_athlete_detailed_analytics(
    db: AsyncSession,
    current_user_id: str,
    athlete_id: str,
    weeks: int,
    inactive_after_days: int,
) -> AthleteDetailedAnalyticsResponse:
    if current_user_id != athlete_id:
        stmt = select(CoachAthleteLink).where(
            CoachAthleteLink.coach_id == current_user_id,
            CoachAthleteLink.athlete_id == athlete_id,
            CoachAthleteLink.status == "active",
        )
        res = await db.execute(stmt)
        link = res.scalar_one_or_none()
        if not link:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to view athlete analytics",
            )

    generated_at = datetime.utcnow()

    sessions = await _fetch_sessions_for_athlete(athlete_id, weeks=weeks)
    sessions_count = len(sessions)

    last_dt: datetime | None = None
    if sessions:
        sessions.sort(key=lambda x: x.get("_parsed_started_at") or datetime.min, reverse=True)
        last_dt = sessions[0].get("_parsed_started_at")

    days_since_last: int | None = None
    if last_dt is not None:
        days_since_last = (generated_at.date() - last_dt.date()).days

    plan_id, plan_name = await _fetch_active_plan_for_athlete(athlete_id)
    total_volume: float | None = None
    plan_items: list[dict] = []
    avg_intensity: float | None = None
    avg_effort: float | None = None
    rpe_distribution: dict[str, float] | None = None
    plan_adherence: float | None = None
    muscle_volume_by_group: dict[str, float] | None = None
    muscle_volume_by_muscle: dict[str, float] | None = None

    if plan_id is not None:
        plan_items = await _fetch_plan_items_for_athlete(
            athlete_id,
            applied_plan_id=plan_id,
            weeks=weeks,
            now=generated_at,
        )
        avg_intensity, avg_effort, rpe_distribution, total_volume = _aggregate_plan_metrics(plan_items)
        muscle_volume_by_group, muscle_volume_by_muscle = _aggregate_muscle_metrics_from_actual(plan_items)

        planned_workout_ids = {int(it.get("workout_id")) for it in plan_items if it.get("workout_id") is not None}
        finished_workout_ids: set[int] = set()
        for s in sessions:
            status = s.get("status")
            if isinstance(status, str) and status.lower() != "finished":
                continue
            wid = s.get("workout_id")
            try:
                wid_int = int(wid)
            except Exception:
                continue
            finished_workout_ids.add(wid_int)
        if planned_workout_ids:
            completed_in_plan = len(planned_workout_ids & finished_workout_ids)
            plan_adherence = float(completed_in_plan) / float(len(planned_workout_ids))

    trends: dict[datetime, AthleteTrendPoint] = {}
    cutoff = generated_at - timedelta(weeks=weeks)

    for s in sessions:
        dt = s.get("_parsed_started_at")
        if not isinstance(dt, datetime):
            continue
        if dt < cutoff or dt > generated_at:
            continue
        week_start = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        existing = trends.get(week_start)
        if not existing:
            trends[week_start] = AthleteTrendPoint(period_start=week_start, sessions_count=1, total_volume=0.0)
        else:
            existing.sessions_count += 1

    for it in plan_items:
        date_raw = it.get("date")
        if not date_raw:
            continue
        try:
            dt = datetime.fromisoformat(str(date_raw).replace("Z", "+00:00"))
        except Exception:
            continue
        if dt < cutoff or dt > generated_at:
            continue
        week_start = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        metrics = it.get("metrics") or {}
        try:
            v = float(metrics.get("volume_sum", 0.0))
        except Exception:
            v = 0.0
        existing = trends.get(week_start)
        if not existing:
            trends[week_start] = AthleteTrendPoint(period_start=week_start, sessions_count=0, total_volume=v)
        else:
            existing.total_volume += v

    trend_list = [trends[k] for k in sorted(trends.keys())]

    sessions_per_week: float | None = None
    if weeks > 0:
        sessions_per_week = float(sessions_count) / float(weeks)

    return AthleteDetailedAnalyticsResponse(
        athlete_id=athlete_id,
        generated_at=generated_at,
        weeks=weeks,
        sessions_count=sessions_count,
        total_volume=total_volume,
        active_plan_id=plan_id,
        active_plan_name=plan_name,
        last_workout_at=last_dt,
        days_since_last_workout=days_since_last,
        trend=trend_list,
        sessions_per_week=sessions_per_week,
        plan_adherence=plan_adherence,
        avg_intensity=avg_intensity,
        avg_effort=avg_effort,
        rpe_distribution=rpe_distribution,
        muscle_volume_by_group=muscle_volume_by_group,
        muscle_volume_by_muscle=muscle_volume_by_muscle,
    )
