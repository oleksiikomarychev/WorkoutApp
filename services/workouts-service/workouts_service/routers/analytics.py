import asyncio
import logging
import math
import os
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models
from ..database import get_db
from ..dependencies import get_current_user_id
from ..schemas.analytics import PlanAnalyticsItem, PlanAnalyticsResponse
from ..schemas.profile import DayActivity, ProfileAggregatesResponse, SessionLite

router = APIRouter(prefix="/analytics")
logger = logging.getLogger(__name__)

_RPE_TABLE_CACHE: dict[int, dict[int, int]] | None = None


def _normalize_int_keys(d: Any) -> Any:
    if isinstance(d, dict):
        out: dict[Any, Any] = {}
        for k, v in d.items():
            try:
                ik = int(k)
            except (TypeError, ValueError):
                ik = k
            out[ik] = _normalize_int_keys(v)
        return out
    return d


async def _get_rpe_table(user_id: str) -> dict[int, dict[int, int]] | None:
    global _RPE_TABLE_CACHE
    if _RPE_TABLE_CACHE is not None:
        return _RPE_TABLE_CACHE
    base = os.getenv("RPE_TABLE_URL", "http://rpe-service:8001/rpe/table").rstrip("/")
    headers = {"X-User-Id": user_id}
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(base, headers=headers)
            if resp.status_code != 200:
                return None

            data = resp.json()
            norm = _normalize_int_keys(data)
            if not isinstance(norm, dict):
                return None
            table: dict[int, dict[int, int]] = {}
            for intensity, efforts in norm.items():
                if not isinstance(intensity, int) or not isinstance(efforts, dict):
                    continue
                inner: dict[int, int] = {}
                for effort, reps in efforts.items():
                    if isinstance(effort, int) and isinstance(reps, int):
                        inner[effort] = reps
                if inner:
                    table[intensity] = inner
            if table:
                _RPE_TABLE_CACHE = table
                return _RPE_TABLE_CACHE
    except Exception:
        return None
    return None


def _iter_effective_sets(s: Any) -> list[dict[str, Any]]:
    if not isinstance(s, dict):
        return []
    subsets = s.get("subsets")
    if isinstance(subsets, list) and subsets:
        return [child for child in subsets if isinstance(child, dict)]
    return [s]


def _intensity_for_reps_rpe(table: dict[int, dict[int, int]], reps: int, rpe: int) -> int | None:
    if reps <= 0:
        return None
    rpe_key = int(rpe)
    for intensity in range(100, 39, -1):
        reps_at = (table.get(intensity) or {}).get(rpe_key)
        if isinstance(reps_at, int) and reps_at >= reps:
            return intensity
    return None


def _effective_intensity_for_e1rm(
    *,
    table: dict[int, dict[int, int]] | None,
    reps: int | None,
    rpe: int | None,
    fallback_intensity: float | None,
) -> float | None:
    if table is not None and reps is not None and reps > 0 and rpe is not None:
        i10 = _intensity_for_reps_rpe(table, reps, 10)
        if i10 is not None:
            return float(i10)
    if fallback_intensity is None:
        return None
    try:
        inten = float(fallback_intensity)
        return inten if inten > 0 else None
    except (TypeError, ValueError):
        return None


def _layer_metric_key(layer: str, metric: str) -> str:
    return f"layer:{layer}:{metric}"


def _parse_layers(raw_layers: list[str] | None) -> list[str]:
    if not raw_layers:
        return []
    out: list[str] = []
    for raw in raw_layers:
        if not raw:
            continue
        s = str(raw).strip()
        if not s:
            continue
        if ":" not in s:
            continue
        t, rest = s.split(":", 1)
        t = t.strip()
        rest = rest.strip()
        if t not in {"exercise", "muscle", "muscle_group"}:
            continue
        if not rest:
            continue
        if t == "exercise":
            try:
                int(rest)
            except (TypeError, ValueError):
                continue
        out.append(f"{t}:{rest}")
    return out


async def _fetch_exercise_definitions(exercise_ids: set[int], user_id: str) -> dict[int, dict[str, Any]]:
    if not exercise_ids:
        return {}
    base_url = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002").rstrip("/")
    ids_str = ",".join(str(i) for i in sorted(exercise_ids))
    url = f"{base_url}/exercises/definitions"
    headers = {"X-User-Id": user_id}
    params = {"ids": ids_str}
    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return {}
            data = resp.json()
            if not isinstance(data, list):
                return {}
            out: dict[int, dict[str, Any]] = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                rid = item.get("id")
                try:
                    iid = int(rid)
                except (TypeError, ValueError):
                    continue
                out[iid] = item
            return out
    except Exception:
        return {}


async def _fetch_workout_instances_from_db(
    db: AsyncSession,
    workout_id: int,
    user_id: str,
) -> list[dict[str, Any]]:
    stmt = (
        select(models.WorkoutExercise)
        .options(selectinload(models.WorkoutExercise.sets))
        .where(
            models.WorkoutExercise.workout_id == workout_id,
            models.WorkoutExercise.user_id == user_id,
        )
        .order_by(models.WorkoutExercise.order.asc().nulls_last(), models.WorkoutExercise.id.asc())
    )
    res = await db.execute(stmt)
    exercises = res.scalars().all()
    out: list[dict[str, Any]] = []
    for ex in exercises or []:
        sets_payload: list[dict[str, Any]] = []
        for s in getattr(ex, "sets", []) or []:
            sets_payload.append(
                {
                    "id": getattr(s, "id", None),
                    "order_index": getattr(s, "order_index", None),
                    "intensity": getattr(s, "intensity", None),
                    "effort": getattr(s, "effort", None),
                    "volume": getattr(s, "volume", None),
                    "working_weight": getattr(s, "working_weight", None),
                    "set_type": getattr(s, "set_type", None),
                    "subsets": getattr(s, "subsets", None),
                }
            )
        out.append(
            {
                "id": getattr(ex, "id", None),
                "exercise_list_id": getattr(ex, "exercise_id", None),
                "order": getattr(ex, "order", None),
                "notes": getattr(ex, "notes", None),
                "rest_seconds": getattr(ex, "rest_seconds", None),
                "sets": sets_payload,
            }
        )
    return out


def _build_set_volume_index(instances: list[dict[str, Any]]) -> tuple[dict[int, float], float]:
    set_volume: dict[int, float] = {}
    total = 0.0
    for inst in instances or []:
        for s in inst.get("sets", []) or []:
            sid = s.get("id")

            reps_raw = s.get("volume")
            weight_raw = s.get("working_weight")

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

            if volume is None and reps > 0:
                volume = round(reps, 2)

            v = volume if volume is not None else 0.0

            if isinstance(sid, int):
                set_volume[sid] = v
            total += v
    return set_volume, total


def _compute_actual_metrics(
    session: models.WorkoutSession,
    instances: list[dict[str, Any]],
    rpe_table: dict[int, dict[int, int]] | None,
) -> dict[str, float]:
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

    total_volume = 0.0
    total_effort = 0.0
    cnt_effort = 0
    total_intensity = 0.0
    cnt_intensity = 0
    total_weight = 0.0
    cnt_weight = 0
    total_tonnage = 0.0
    total_e1rm = 0.0
    cnt_e1rm = 0
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
        for top in inst.get("sets") or []:
            sid = top.get("id") if isinstance(top, dict) else None
            if sid is None or sid not in completed_sets:
                continue
            for s in _iter_effective_sets(top):
                effort = s.get("effort") or s.get("rpe")
                intensity = s.get("intensity")
                reps_raw = s.get("volume")
                weight_raw = s.get("working_weight")
                volume_raw = s.get("volume")

                weight: float | None = None
                try:
                    if weight_raw is not None:
                        weight = float(weight_raw)
                except (TypeError, ValueError):
                    weight = None

                v = 0.0
                try:
                    if volume_raw is not None:
                        v = float(volume_raw)
                except (TypeError, ValueError):
                    v = 0.0

                try:
                    if effort is not None:
                        total_effort += float(effort)
                        cnt_effort += 1
                    if intensity is not None:
                        total_intensity += float(intensity)
                        cnt_intensity += 1
                    total_volume += v

                    if weight is not None:
                        total_tonnage += v * weight
                        total_weight += weight
                        cnt_weight += 1

                    reps_i: int | None = None
                    try:
                        if reps_raw is not None:
                            reps_i = int(round(float(reps_raw)))
                    except (TypeError, ValueError):
                        reps_i = None
                    rpe_i: int | None = None
                    try:
                        if effort is not None:
                            rpe_i = int(math.floor(float(effort)))
                    except (TypeError, ValueError):
                        rpe_i = None

                    if weight is not None:
                        inten_eff = _effective_intensity_for_e1rm(
                            table=rpe_table,
                            reps=reps_i,
                            rpe=rpe_i,
                            fallback_intensity=intensity,
                        )
                        if inten_eff is not None and inten_eff > 0:
                            total_e1rm += float(weight) / (inten_eff / 100.0)
                            cnt_e1rm += 1

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
        "reps_per_set_avg": (total_volume / sets_cnt) if sets_cnt > 0 else 0.0,
        "kilograms_avg": (total_weight / cnt_weight) if cnt_weight > 0 else 0.0,
        "tonnage_sum": total_tonnage,
        "one_rm_est_avg": (total_e1rm / cnt_e1rm) if cnt_e1rm > 0 else 0.0,
    }

    for mg, v in muscle_group_volume.items():
        metrics[f"muscle_group:{mg}"] = v
    for m, v in muscle_volume.items():
        metrics[f"muscle:{m}"] = v

    return metrics


def _compute_actual_layer_metrics(
    session: models.WorkoutSession,
    instances: list[dict[str, Any]],
    layers: list[str],
    rpe_table: dict[int, dict[int, int]] | None,
) -> dict[str, float]:
    if not layers:
        return {}

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

    ex_aggs: dict[int, dict[str, float]] = {}
    muscle_volume: dict[str, float] = {}
    muscle_sets: dict[str, float] = {}
    muscle_eff_sum: dict[str, float] = {}
    muscle_eff_den: dict[str, float] = {}
    muscle_int_sum: dict[str, float] = {}
    muscle_int_den: dict[str, float] = {}
    muscle_weight_sum: dict[str, float] = {}
    muscle_weight_den: dict[str, float] = {}
    muscle_tonnage: dict[str, float] = {}
    muscle_e1rm_sum: dict[str, float] = {}
    muscle_e1rm_den: dict[str, float] = {}

    muscle_group_volume: dict[str, float] = {}
    muscle_group_sets: dict[str, float] = {}
    muscle_group_eff_sum: dict[str, float] = {}
    muscle_group_eff_cnt: dict[str, float] = {}
    muscle_group_int_sum: dict[str, float] = {}
    muscle_group_int_cnt: dict[str, float] = {}
    muscle_group_weight_sum: dict[str, float] = {}
    muscle_group_weight_den: dict[str, float] = {}
    muscle_group_tonnage: dict[str, float] = {}
    muscle_group_e1rm_sum: dict[str, float] = {}
    muscle_group_e1rm_cnt: dict[str, float] = {}

    for inst in instances:
        iid = inst.get("id")
        if iid is None or iid not in completed_map:
            continue

        ex_id_raw = inst.get("exercise_list_id")
        try:
            ex_id = int(ex_id_raw) if ex_id_raw is not None else None
        except (TypeError, ValueError):
            ex_id = None

        exercise_def = inst.get("exercise_definition") or {}
        raw_target = exercise_def.get("target_muscles") or []
        raw_synergists = exercise_def.get("synergist_muscles") or []
        target_muscles = [m for m in raw_target if isinstance(m, str) and m]
        synergist_muscles = [m for m in raw_synergists if isinstance(m, str) and m]
        muscle_group = exercise_def.get("muscle_group")

        completed_sets = completed_map[iid]
        for top in inst.get("sets") or []:
            sid = top.get("id") if isinstance(top, dict) else None
            if sid is None or sid not in completed_sets:
                continue
            for s in _iter_effective_sets(top):
                effort = s.get("effort") or s.get("rpe")
                intensity = s.get("intensity")
                reps_raw = s.get("volume")
                weight_raw = s.get("working_weight")
                volume_raw = s.get("volume")

                v = 0.0
                try:
                    if volume_raw is not None:
                        v = float(volume_raw)
                except (TypeError, ValueError):
                    v = 0.0

                w: float | None = None
                try:
                    if weight_raw is not None:
                        w = float(weight_raw)
                except (TypeError, ValueError):
                    w = None

                ton = v * w if (w is not None and v > 0) else 0.0
                e1rm: float | None = None
                reps_i: int | None = None
                try:
                    if reps_raw is not None:
                        reps_i = int(round(float(reps_raw)))
                except (TypeError, ValueError):
                    reps_i = None
                rpe_i: int | None = None
                try:
                    if effort is not None:
                        rpe_i = int(math.floor(float(effort)))
                except (TypeError, ValueError):
                    rpe_i = None
                if w is not None:
                    inten_eff = _effective_intensity_for_e1rm(
                        table=rpe_table,
                        reps=reps_i,
                        rpe=rpe_i,
                        fallback_intensity=intensity,
                    )
                    if inten_eff is not None and inten_eff > 0:
                        e1rm = float(w) / (inten_eff / 100.0)

                if ex_id is not None:
                    agg = ex_aggs.setdefault(
                        ex_id,
                        {
                            "volume_sum": 0.0,
                            "sets_count": 0.0,
                            "effort_sum": 0.0,
                            "effort_cnt": 0.0,
                            "intensity_sum": 0.0,
                            "intensity_cnt": 0.0,
                            "weight_sum": 0.0,
                            "weight_cnt": 0.0,
                            "tonnage_sum": 0.0,
                            "e1rm_sum": 0.0,
                            "e1rm_cnt": 0.0,
                        },
                    )
                    agg["volume_sum"] += v
                    agg["sets_count"] += 1.0
                    if w is not None:
                        agg["weight_sum"] += w
                        agg["weight_cnt"] += 1.0
                    if ton > 0:
                        agg["tonnage_sum"] += ton
                    if effort is not None:
                        try:
                            agg["effort_sum"] += float(effort)
                            agg["effort_cnt"] += 1.0
                        except (TypeError, ValueError):
                            pass
                    if intensity is not None:
                        try:
                            agg["intensity_sum"] += float(intensity)
                            agg["intensity_cnt"] += 1.0
                        except (TypeError, ValueError):
                            pass

                    if e1rm is not None:
                        agg["e1rm_sum"] += e1rm
                        agg["e1rm_cnt"] += 1.0

                if isinstance(muscle_group, str) and muscle_group:
                    muscle_group_volume[muscle_group] = muscle_group_volume.get(muscle_group, 0.0) + v
                    muscle_group_sets[muscle_group] = muscle_group_sets.get(muscle_group, 0.0) + 1.0
                    if w is not None:
                        muscle_group_weight_sum[muscle_group] = muscle_group_weight_sum.get(muscle_group, 0.0) + w
                        muscle_group_weight_den[muscle_group] = muscle_group_weight_den.get(muscle_group, 0.0) + 1.0
                    if ton > 0:
                        muscle_group_tonnage[muscle_group] = muscle_group_tonnage.get(muscle_group, 0.0) + ton
                    if effort is not None:
                        try:
                            muscle_group_eff_sum[muscle_group] = muscle_group_eff_sum.get(muscle_group, 0.0) + float(effort)
                            muscle_group_eff_cnt[muscle_group] = muscle_group_eff_cnt.get(muscle_group, 0.0) + 1.0
                        except (TypeError, ValueError):
                            pass
                    if intensity is not None:
                        try:
                            muscle_group_int_sum[muscle_group] = muscle_group_int_sum.get(muscle_group, 0.0) + float(intensity)
                            muscle_group_int_cnt[muscle_group] = muscle_group_int_cnt.get(muscle_group, 0.0) + 1.0
                        except (TypeError, ValueError):
                            pass

                    if e1rm is not None:
                        muscle_group_e1rm_sum[muscle_group] = muscle_group_e1rm_sum.get(muscle_group, 0.0) + e1rm
                        muscle_group_e1rm_cnt[muscle_group] = muscle_group_e1rm_cnt.get(muscle_group, 0.0) + 1.0

            muscles_weights: list[tuple[str, float]] = []
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
                        frac = w / total_w
                        muscle_sets[m] = muscle_sets.get(m, 0.0) + frac
                        if effort is not None:
                            try:
                                muscle_eff_sum[m] = muscle_eff_sum.get(m, 0.0) + float(effort) * frac
                                muscle_eff_den[m] = muscle_eff_den.get(m, 0.0) + frac
                            except (TypeError, ValueError):
                                pass
                        if intensity is not None:
                            try:
                                muscle_int_sum[m] = muscle_int_sum.get(m, 0.0) + float(intensity) * frac
                                muscle_int_den[m] = muscle_int_den.get(m, 0.0) + frac
                            except (TypeError, ValueError):
                                pass
                        share = v * frac
                        muscle_volume[m] = muscle_volume.get(m, 0.0) + share
                        if w is not None:
                            muscle_weight_sum[m] = muscle_weight_sum.get(m, 0.0) + w * frac
                            muscle_weight_den[m] = muscle_weight_den.get(m, 0.0) + frac
                        if ton > 0:
                            muscle_tonnage[m] = muscle_tonnage.get(m, 0.0) + ton * frac
                        if e1rm is not None:
                            muscle_e1rm_sum[m] = muscle_e1rm_sum.get(m, 0.0) + e1rm * frac
                            muscle_e1rm_den[m] = muscle_e1rm_den.get(m, 0.0) + frac

    layer_metrics: dict[str, float] = {}
    for layer in layers:
        if layer.startswith("exercise:"):
            try:
                ex_id = int(layer.split(":", 1)[1])
            except (TypeError, ValueError):
                continue
            agg = ex_aggs.get(ex_id)
            if not agg:
                continue
            layer_metrics[_layer_metric_key(layer, "volume_sum")] = float(agg.get("volume_sum", 0.0))
            layer_metrics[_layer_metric_key(layer, "sets_count")] = float(agg.get("sets_count", 0.0))
            sets = float(agg.get("sets_count", 0.0))
            layer_metrics[_layer_metric_key(layer, "reps_per_set_avg")] = (
                float(agg.get("volume_sum", 0.0)) / sets if sets > 0 else 0.0
            )
            wcnt = float(agg.get("weight_cnt", 0.0))
            layer_metrics[_layer_metric_key(layer, "kilograms_avg")] = (
                float(agg.get("weight_sum", 0.0)) / wcnt if wcnt > 0 else 0.0
            )
            layer_metrics[_layer_metric_key(layer, "tonnage_sum")] = float(agg.get("tonnage_sum", 0.0))
            e1cnt = float(agg.get("e1rm_cnt", 0.0))
            layer_metrics[_layer_metric_key(layer, "one_rm_est_avg")] = (
                float(agg.get("e1rm_sum", 0.0)) / e1cnt if e1cnt > 0 else 0.0
            )
            eff_cnt = float(agg.get("effort_cnt", 0.0))
            int_cnt = float(agg.get("intensity_cnt", 0.0))
            layer_metrics[_layer_metric_key(layer, "effort_avg")] = (
                float(agg.get("effort_sum", 0.0)) / eff_cnt if eff_cnt > 0 else 0.0
            )
            layer_metrics[_layer_metric_key(layer, "intensity_avg")] = (
                float(agg.get("intensity_sum", 0.0)) / int_cnt if int_cnt > 0 else 0.0
            )
        elif layer.startswith("muscle:"):
            name = layer.split(":", 1)[1]
            layer_metrics[_layer_metric_key(layer, "volume_sum")] = float(muscle_volume.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "sets_count")] = float(muscle_sets.get(name, 0.0))
            sets = float(muscle_sets.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "reps_per_set_avg")] = (
                float(muscle_volume.get(name, 0.0)) / sets if sets > 0 else 0.0
            )
            wden = float(muscle_weight_den.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "kilograms_avg")] = (
                float(muscle_weight_sum.get(name, 0.0)) / wden if wden > 0 else 0.0
            )
            layer_metrics[_layer_metric_key(layer, "tonnage_sum")] = float(muscle_tonnage.get(name, 0.0))
            e1den = float(muscle_e1rm_den.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "one_rm_est_avg")] = (
                float(muscle_e1rm_sum.get(name, 0.0)) / e1den if e1den > 0 else 0.0
            )
            eff_den = float(muscle_eff_den.get(name, 0.0))
            int_den = float(muscle_int_den.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "effort_avg")] = (
                float(muscle_eff_sum.get(name, 0.0)) / eff_den if eff_den > 0 else 0.0
            )
            layer_metrics[_layer_metric_key(layer, "intensity_avg")] = (
                float(muscle_int_sum.get(name, 0.0)) / int_den if int_den > 0 else 0.0
            )
        elif layer.startswith("muscle_group:"):
            name = layer.split(":", 1)[1]
            layer_metrics[_layer_metric_key(layer, "volume_sum")] = float(muscle_group_volume.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "sets_count")] = float(muscle_group_sets.get(name, 0.0))
            sets = float(muscle_group_sets.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "reps_per_set_avg")] = (
                float(muscle_group_volume.get(name, 0.0)) / sets if sets > 0 else 0.0
            )
            wden = float(muscle_group_weight_den.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "kilograms_avg")] = (
                float(muscle_group_weight_sum.get(name, 0.0)) / wden if wden > 0 else 0.0
            )
            layer_metrics[_layer_metric_key(layer, "tonnage_sum")] = float(muscle_group_tonnage.get(name, 0.0))
            e1cnt = float(muscle_group_e1rm_cnt.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "one_rm_est_avg")] = (
                float(muscle_group_e1rm_sum.get(name, 0.0)) / e1cnt if e1cnt > 0 else 0.0
            )
            eff_cnt = float(muscle_group_eff_cnt.get(name, 0.0))
            int_cnt = float(muscle_group_int_cnt.get(name, 0.0))
            layer_metrics[_layer_metric_key(layer, "effort_avg")] = (
                float(muscle_group_eff_sum.get(name, 0.0)) / eff_cnt if eff_cnt > 0 else 0.0
            )
            layer_metrics[_layer_metric_key(layer, "intensity_avg")] = (
                float(muscle_group_int_sum.get(name, 0.0)) / int_cnt if int_cnt > 0 else 0.0
            )

    return layer_metrics


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
            instances = await _fetch_workout_instances_from_db(db, wid, user_id)
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

    rpe_table = await _get_rpe_table(user_id)

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
        total_weight = 0.0
        cnt_weight = 0
        total_tonnage = 0.0
        total_e1rm = 0.0
        cnt_e1rm = 0
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
                    if s.working_weight is not None:
                        total_tonnage += float(s.volume) * float(s.working_weight)
                sets_cnt += 1
                if s.working_weight is not None:
                    total_weight += float(s.working_weight)
                    cnt_weight += 1

                reps_i: int | None = None
                try:
                    if s.volume is not None:
                        reps_i = int(round(float(s.volume)))
                except (TypeError, ValueError):
                    reps_i = None
                rpe_i: int | None = None
                try:
                    if s.effort is not None:
                        rpe_i = int(math.floor(float(s.effort)))
                except (TypeError, ValueError):
                    rpe_i = None
                if s.working_weight is not None:
                    inten_eff = None
                    try:
                        if s.intensity is not None:
                            inten_eff = float(s.intensity)
                    except (TypeError, ValueError):
                        inten_eff = None
                    if inten_eff is not None and inten_eff > 0:
                        total_e1rm += float(s.working_weight) / (inten_eff / 100.0)
                        cnt_e1rm += 1

        metrics = {
            "effort_avg": (total_effort / cnt_effort) if cnt_effort > 0 else 0.0,
            "intensity_avg": (total_intensity / cnt_intensity) if cnt_intensity > 0 else 0.0,
            "volume_sum": total_volume,
            "sets_count": float(sets_cnt),
            "reps_per_set_avg": (total_volume / sets_cnt) if sets_cnt > 0 else 0.0,
            "kilograms_avg": (total_weight / cnt_weight) if cnt_weight > 0 else 0.0,
            "tonnage_sum": total_tonnage,
            "one_rm_est_avg": (total_e1rm / cnt_e1rm) if cnt_e1rm > 0 else 0.0,
        }
        items.append(PlanAnalyticsItem(workout_id=wid, order_index=order_index, date=date, metrics=metrics))

    return PlanAnalyticsResponse(items=items)


@router.get("/history", response_model=PlanAnalyticsResponse)
async def get_workout_history_analytics(
    days: int = Query(365, ge=1, le=3650),
    layers: list[str] | None = Query(
        None,
        description="Optional multilayer series keys. Example: layers=exercise:10&layers=muscle:chest",
    ),
    include_meta: bool = Query(
        False,
        description="If true, include meta with available layer options/labels for UI",
    ),
    top_layers_limit: int = Query(
        20,
        ge=1,
        le=200,
        description="Limit for meta.available_layers lists",
    ),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    session_q = (
        select(models.WorkoutSession)
        .where(
            models.WorkoutSession.user_id == user_id,
            models.WorkoutSession.finished_at.isnot(None),
            models.WorkoutSession.finished_at >= cutoff_date,
        )
        .order_by(models.WorkoutSession.finished_at.asc(), models.WorkoutSession.id.asc())
    )

    result = await db.execute(session_q)
    sessions: list[models.WorkoutSession] = list(result.scalars().all())

    parsed_layers = _parse_layers(layers)

    if not sessions:
        meta: dict[str, Any] | None = None
        if include_meta:
            meta = {
                "group_by": "date",
                "available_metrics": [
                    "sets_count",
                    "volume_sum",
                    "reps_per_set_avg",
                    "kilograms_avg",
                    "tonnage_sum",
                    "one_rm_est_avg",
                    "intensity_avg",
                    "effort_avg",
                ],
                "available_muscles": [],
                "available_muscle_groups": [],
                "requested_layers": parsed_layers,
                "actual_layers": [],
                "exercise_labels": {},
            }
        return PlanAnalyticsResponse(items=[], meta=meta)

    rpe_table = await _get_rpe_table(user_id)

    unique_wids: list[int] = []
    seen_wids: set[int] = set()
    for s in sessions:
        wid = s.workout_id
        if isinstance(wid, int) and wid not in seen_wids:
            seen_wids.add(wid)
            unique_wids.append(wid)

    instances_by_wid: dict[int, list[dict[str, Any]]] = {}
    sem = asyncio.Semaphore(6)

    async def _fetch_for_wid(wid: int) -> None:
        async with sem:
            instances_by_wid[wid] = await _fetch_workout_instances_from_db(db, wid, user_id)

    if unique_wids:
        await asyncio.gather(*[_fetch_for_wid(wid) for wid in unique_wids])

    exercise_labels: dict[str, str] = {}
    available_muscles: set[str] = set()
    available_muscle_groups: set[str] = set()

    if include_meta:
        for insts in instances_by_wid.values():
            for inst in insts:
                ex_id_raw = inst.get("exercise_list_id")
                try:
                    ex_id = int(ex_id_raw) if ex_id_raw is not None else None
                except (TypeError, ValueError):
                    ex_id = None
                if ex_id is None:
                    continue

                ex_def = inst.get("exercise_definition") or {}
                nm = ex_def.get("name")
                if isinstance(nm, str) and nm:
                    exercise_labels[str(ex_id)] = nm

                mg = ex_def.get("muscle_group")
                if isinstance(mg, str) and mg:
                    available_muscle_groups.add(mg)

                for m in (ex_def.get("target_muscles") or []):
                    if isinstance(m, str) and m:
                        available_muscles.add(m)
                for m in (ex_def.get("synergist_muscles") or []):
                    if isinstance(m, str) and m:
                        available_muscles.add(m)

    actual_layer_totals: dict[str, float] = {}

    items: list[PlanAnalyticsItem] = []
    for s in sessions:
        wid = s.workout_id
        if not isinstance(wid, int):
            continue

        insts = instances_by_wid.get(wid, [])
        metrics = _compute_actual_metrics(s, insts, rpe_table) or {}
        if parsed_layers:
            layer_actuals = _compute_actual_layer_metrics(s, insts, parsed_layers, rpe_table)
            if layer_actuals:
                metrics = {**metrics, **layer_actuals}

        if include_meta:
            for k, v in metrics.items():
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue

                if k.startswith("muscle:"):
                    actual_layer_totals[k] = actual_layer_totals.get(k, 0.0) + fv
                elif k.startswith("muscle_group:"):
                    actual_layer_totals[k] = actual_layer_totals.get(k, 0.0) + fv
                elif k.startswith("layer:") and k.endswith(":volume_sum"):
                    layer = k.split(":", 1)[1].rsplit(":", 1)[0]
                    actual_layer_totals[layer] = actual_layer_totals.get(layer, 0.0) + fv

        items.append(
            PlanAnalyticsItem(
                workout_id=wid,
                order_index=None,
                date=s.finished_at or s.started_at,
                metrics=metrics,
                actual_metrics=None,
            )
        )

    meta: dict[str, Any] | None = None
    if include_meta:
        def _sorted_layers(src: dict[str, float]) -> list[tuple[str, float]]:
            pairs = list(src.items())
            pairs.sort(key=lambda x: x[1], reverse=True)
            return pairs[:top_layers_limit]

        meta = {
            "group_by": "date",
            "available_metrics": [
                "sets_count",
                "volume_sum",
                "reps_per_set_avg",
                "kilograms_avg",
                "tonnage_sum",
                "one_rm_est_avg",
                "intensity_avg",
                "effort_avg",
            ],
            "available_muscles": sorted(available_muscles),
            "available_muscle_groups": sorted(available_muscle_groups),
            "requested_layers": parsed_layers,
            "actual_layers": [
                {"layer": k, "volume_sum": float(v)}
                for k, v in _sorted_layers(actual_layer_totals)
            ],
            "exercise_labels": exercise_labels,
        }

    return PlanAnalyticsResponse(items=items, meta=meta)


@router.get("/in-plan", response_model=PlanAnalyticsResponse)
async def get_plan_analytics(
    applied_plan_id: int = Query(..., ge=1),
    from_dt: str | None = Query(None, alias="from"),
    to_dt: str | None = Query(None, alias="to"),
    group_by: str | None = Query("order", pattern="^(order|date)$"),
    layers: list[str] | None = Query(
        None,
        description="Optional multilayer series keys. Example: layers=exercise:10&layers=muscle:chest",
    ),
    include_meta: bool = Query(
        False,
        description="If true, include meta with available layer options/labels for UI",
    ),
    top_layers_limit: int = Query(
        20,
        ge=1,
        le=200,
        description="Limit for meta.available_layers lists",
    ),
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

    parsed_layers = _parse_layers(layers)

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

    exercise_ids: set[int] = set()
    for ex in ex_list:
        try:
            exercise_ids.add(int(ex.exercise_id))
        except (TypeError, ValueError):
            continue

    need_defs = include_meta or any(
        l.startswith("muscle:") or l.startswith("muscle_group:") for l in parsed_layers
    )
    exercise_defs: dict[int, dict[str, Any]] = {}
    if need_defs:
        exercise_defs = await _fetch_exercise_definitions(exercise_ids, user_id)

    rpe_table = await _get_rpe_table(user_id)

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
                fetch_tasks.append(_fetch_workout_instances_from_db(db, wid, user_id))

            fetched_results = await asyncio.gather(*fetch_tasks)
            instances_by_wid = dict(zip(wids_to_fetch, fetched_results))

    planned_layer_totals: dict[str, float] = {}
    actual_layer_totals: dict[str, float] = {}

    for w in workouts:
        wid = int(w.id)
        order_index = w.plan_order_index
        date = w.scheduled_for
        total_effort = 0.0
        total_intensity = 0.0
        total_volume = 0.0
        total_weight = 0.0
        cnt_weight = 0
        total_tonnage = 0.0
        total_e1rm = 0.0
        cnt_e1rm = 0
        cnt_effort = 0
        cnt_intensity = 0
        sets_cnt = 0

        per_exercise: dict[int, dict[str, float]] = {}
        planned_muscle_volume: dict[str, float] = {}
        planned_muscle_sets: dict[str, float] = {}
        planned_muscle_eff_sum: dict[str, float] = {}
        planned_muscle_eff_den: dict[str, float] = {}
        planned_muscle_int_sum: dict[str, float] = {}
        planned_muscle_int_den: dict[str, float] = {}
        planned_muscle_weight_sum: dict[str, float] = {}
        planned_muscle_weight_den: dict[str, float] = {}
        planned_muscle_tonnage: dict[str, float] = {}
        planned_muscle_e1rm_sum: dict[str, float] = {}
        planned_muscle_e1rm_den: dict[str, float] = {}

        planned_muscle_group_volume: dict[str, float] = {}
        planned_muscle_group_sets: dict[str, float] = {}
        planned_muscle_group_eff_sum: dict[str, float] = {}
        planned_muscle_group_eff_cnt: dict[str, float] = {}
        planned_muscle_group_int_sum: dict[str, float] = {}
        planned_muscle_group_int_cnt: dict[str, float] = {}
        planned_muscle_group_weight_sum: dict[str, float] = {}
        planned_muscle_group_weight_den: dict[str, float] = {}
        planned_muscle_group_tonnage: dict[str, float] = {}
        planned_muscle_group_e1rm_sum: dict[str, float] = {}
        planned_muscle_group_e1rm_cnt: dict[str, float] = {}
        for ex in ex_by_w.get(wid, []):
            for s in sets_by_ex.get(ex.id, []):
                try:
                    ex_def_id = int(ex.exercise_id)
                except (TypeError, ValueError):
                    ex_def_id = None

                if s.effort is not None:
                    total_effort += float(s.effort)
                    cnt_effort += 1
                if s.intensity is not None:
                    total_intensity += float(s.intensity)
                    cnt_intensity += 1
                if s.volume is not None:
                    total_volume += float(s.volume)
                sets_cnt += 1

                if s.working_weight is not None:
                    total_weight += float(s.working_weight)
                    cnt_weight += 1
                    if s.volume is not None:
                        total_tonnage += float(s.volume) * float(s.working_weight)

                reps_i: int | None = None
                try:
                    if s.volume is not None:
                        reps_i = int(round(float(s.volume)))
                except (TypeError, ValueError):
                    reps_i = None
                rpe_i: int | None = None
                try:
                    if s.effort is not None:
                        rpe_i = int(math.floor(float(s.effort)))
                except (TypeError, ValueError):
                    rpe_i = None
                if s.working_weight is not None:
                    inten_eff = _effective_intensity_for_e1rm(
                        table=rpe_table,
                        reps=reps_i,
                        rpe=rpe_i,
                        fallback_intensity=s.intensity,
                    )
                    if inten_eff is not None and inten_eff > 0:
                        total_e1rm += float(s.working_weight) / (inten_eff / 100.0)
                        cnt_e1rm += 1

                if ex_def_id is not None:
                    agg = per_exercise.setdefault(
                        ex_def_id,
                        {
                            "volume_sum": 0.0,
                            "sets_count": 0.0,
                            "effort_sum": 0.0,
                            "effort_cnt": 0.0,
                            "intensity_sum": 0.0,
                            "intensity_cnt": 0.0,
                            "weight_sum": 0.0,
                            "weight_cnt": 0.0,
                            "tonnage_sum": 0.0,
                            "e1rm_sum": 0.0,
                            "e1rm_cnt": 0.0,
                        },
                    )
                    if s.volume is not None:
                        agg["volume_sum"] += float(s.volume)
                    agg["sets_count"] += 1.0
                    if s.working_weight is not None:
                        agg["weight_sum"] += float(s.working_weight)
                        agg["weight_cnt"] += 1.0
                    if s.volume is not None and s.working_weight is not None:
                        agg["tonnage_sum"] += float(s.volume) * float(s.working_weight)
                    if s.effort is not None:
                        agg["effort_sum"] += float(s.effort)
                        agg["effort_cnt"] += 1.0
                    if s.intensity is not None:
                        agg["intensity_sum"] += float(s.intensity)
                        agg["intensity_cnt"] += 1.0

                    if s.working_weight is not None:
                        inten_eff = None
                        try:
                            if s.intensity is not None:
                                inten_eff = float(s.intensity)
                        except (TypeError, ValueError):
                            inten_eff = None
                        if inten_eff is not None and inten_eff > 0:
                            agg["e1rm_sum"] += float(s.working_weight) / (inten_eff / 100.0)
                            agg["e1rm_cnt"] += 1.0

                    if need_defs:
                        d = exercise_defs.get(ex_def_id) or {}
                        mg = d.get("muscle_group")
                        if isinstance(mg, str) and mg:
                            planned_muscle_group_sets[mg] = planned_muscle_group_sets.get(mg, 0.0) + 1.0
                            if s.volume is not None:
                                planned_muscle_group_volume[mg] = planned_muscle_group_volume.get(mg, 0.0) + float(
                                    s.volume
                                )
                            if s.working_weight is not None:
                                planned_muscle_group_weight_sum[mg] = planned_muscle_group_weight_sum.get(mg, 0.0) + float(
                                    s.working_weight
                                )
                                planned_muscle_group_weight_den[mg] = planned_muscle_group_weight_den.get(mg, 0.0) + 1.0
                            if s.volume is not None and s.working_weight is not None:
                                planned_muscle_group_tonnage[mg] = planned_muscle_group_tonnage.get(mg, 0.0) + float(
                                    s.volume
                                ) * float(s.working_weight)
                            if s.effort is not None:
                                planned_muscle_group_eff_sum[mg] = planned_muscle_group_eff_sum.get(mg, 0.0) + float(
                                    s.effort
                                )
                                planned_muscle_group_eff_cnt[mg] = planned_muscle_group_eff_cnt.get(mg, 0.0) + 1.0
                            if s.intensity is not None:
                                planned_muscle_group_int_sum[mg] = planned_muscle_group_int_sum.get(mg, 0.0) + float(
                                    s.intensity
                                )
                                planned_muscle_group_int_cnt[mg] = planned_muscle_group_int_cnt.get(mg, 0.0) + 1.0

                            if s.working_weight is not None:
                                inten_eff = None
                                try:
                                    if s.intensity is not None:
                                        inten_eff = float(s.intensity)
                                except (TypeError, ValueError):
                                    inten_eff = None
                                if inten_eff is not None and inten_eff > 0:
                                    planned_muscle_group_e1rm_sum[mg] = planned_muscle_group_e1rm_sum.get(mg, 0.0) + (
                                        float(s.working_weight) / (inten_eff / 100.0)
                                    )
                                    planned_muscle_group_e1rm_cnt[mg] = planned_muscle_group_e1rm_cnt.get(mg, 0.0) + 1.0

                        raw_target = d.get("target_muscles") or []
                        raw_synergists = d.get("synergist_muscles") or []
                        target_muscles = [m for m in raw_target if isinstance(m, str) and m]
                        synergist_muscles = [m for m in raw_synergists if isinstance(m, str) and m]
                        if (target_muscles or synergist_muscles):
                            muscles_weights: list[tuple[str, float]] = []
                            for m in target_muscles:
                                muscles_weights.append((m, 1.0))
                            for m in synergist_muscles:
                                muscles_weights.append((m, 0.5))
                            total_w = sum(w for _, w in muscles_weights if w > 0)
                            if total_w > 0:
                                for m, wgt in muscles_weights:
                                    if wgt <= 0:
                                        continue
                                    frac = wgt / total_w
                                    planned_muscle_sets[m] = planned_muscle_sets.get(m, 0.0) + frac
                                    if s.effort is not None:
                                        planned_muscle_eff_sum[m] = planned_muscle_eff_sum.get(m, 0.0) + float(s.effort) * frac
                                        planned_muscle_eff_den[m] = planned_muscle_eff_den.get(m, 0.0) + frac
                                    if s.intensity is not None:
                                        planned_muscle_int_sum[m] = planned_muscle_int_sum.get(m, 0.0) + float(s.intensity) * frac
                                        planned_muscle_int_den[m] = planned_muscle_int_den.get(m, 0.0) + frac
                                    if s.volume is not None:
                                        share = float(s.volume) * frac
                                        planned_muscle_volume[m] = planned_muscle_volume.get(m, 0.0) + share
                                        if s.working_weight is not None:
                                            planned_muscle_weight_sum[m] = planned_muscle_weight_sum.get(m, 0.0) + float(s.working_weight) * frac
                                            planned_muscle_weight_den[m] = planned_muscle_weight_den.get(m, 0.0) + frac
                                        if s.working_weight is not None:
                                            planned_muscle_tonnage[m] = planned_muscle_tonnage.get(m, 0.0) + share * float(s.working_weight)

                                    if s.working_weight is not None:
                                        inten_eff = None
                                        try:
                                            if s.intensity is not None:
                                                inten_eff = float(s.intensity)
                                        except (TypeError, ValueError):
                                            inten_eff = None
                                        if inten_eff is not None and inten_eff > 0:
                                            planned_muscle_e1rm_sum[m] = planned_muscle_e1rm_sum.get(m, 0.0) + (
                                                float(s.working_weight) / (inten_eff / 100.0)
                                            ) * frac
                                            planned_muscle_e1rm_den[m] = planned_muscle_e1rm_den.get(m, 0.0) + frac

        metrics = {
            "effort_avg": (total_effort / cnt_effort) if cnt_effort > 0 else 0.0,
            "intensity_avg": (total_intensity / cnt_intensity) if cnt_intensity > 0 else 0.0,
            "volume_sum": total_volume,
            "sets_count": float(sets_cnt),
            "reps_per_set_avg": (total_volume / sets_cnt) if sets_cnt > 0 else 0.0,
            "kilograms_avg": (total_weight / cnt_weight) if cnt_weight > 0 else 0.0,
            "tonnage_sum": total_tonnage,
            "one_rm_est_avg": (total_e1rm / cnt_e1rm) if cnt_e1rm > 0 else 0.0,
        }

        if parsed_layers:
            for layer in parsed_layers:
                if layer.startswith("exercise:"):
                    try:
                        ex_id = int(layer.split(":", 1)[1])
                    except (TypeError, ValueError):
                        continue
                    agg = per_exercise.get(ex_id)
                    if not agg:
                        continue
                    metrics[_layer_metric_key(layer, "volume_sum")] = float(agg.get("volume_sum", 0.0))
                    metrics[_layer_metric_key(layer, "sets_count")] = float(agg.get("sets_count", 0.0))
                    sets = float(agg.get("sets_count", 0.0))
                    metrics[_layer_metric_key(layer, "reps_per_set_avg")] = (
                        float(agg.get("volume_sum", 0.0)) / sets if sets > 0 else 0.0
                    )
                    wcnt = float(agg.get("weight_cnt", 0.0))
                    metrics[_layer_metric_key(layer, "kilograms_avg")] = (
                        float(agg.get("weight_sum", 0.0)) / wcnt if wcnt > 0 else 0.0
                    )
                    metrics[_layer_metric_key(layer, "tonnage_sum")] = float(agg.get("tonnage_sum", 0.0))
                    e1cnt = float(agg.get("e1rm_cnt", 0.0))
                    metrics[_layer_metric_key(layer, "one_rm_est_avg")] = (
                        float(agg.get("e1rm_sum", 0.0)) / e1cnt if e1cnt > 0 else 0.0
                    )
                    eff_cnt = float(agg.get("effort_cnt", 0.0))
                    int_cnt = float(agg.get("intensity_cnt", 0.0))
                    metrics[_layer_metric_key(layer, "effort_avg")] = (
                        float(agg.get("effort_sum", 0.0)) / eff_cnt if eff_cnt > 0 else 0.0
                    )
                    metrics[_layer_metric_key(layer, "intensity_avg")] = (
                        float(agg.get("intensity_sum", 0.0)) / int_cnt if int_cnt > 0 else 0.0
                    )
                elif layer.startswith("muscle:"):
                    name = layer.split(":", 1)[1]
                    metrics[_layer_metric_key(layer, "volume_sum")] = float(planned_muscle_volume.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "sets_count")] = float(planned_muscle_sets.get(name, 0.0))
                    sets = float(planned_muscle_sets.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "reps_per_set_avg")] = (
                        float(planned_muscle_volume.get(name, 0.0)) / sets if sets > 0 else 0.0
                    )
                    wden = float(planned_muscle_weight_den.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "kilograms_avg")] = (
                        float(planned_muscle_weight_sum.get(name, 0.0)) / wden if wden > 0 else 0.0
                    )
                    metrics[_layer_metric_key(layer, "tonnage_sum")] = float(planned_muscle_tonnage.get(name, 0.0))
                    e1den = float(planned_muscle_e1rm_den.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "one_rm_est_avg")] = (
                        float(planned_muscle_e1rm_sum.get(name, 0.0)) / e1den if e1den > 0 else 0.0
                    )
                    eff_den = float(planned_muscle_eff_den.get(name, 0.0))
                    int_den = float(planned_muscle_int_den.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "effort_avg")] = (
                        float(planned_muscle_eff_sum.get(name, 0.0)) / eff_den if eff_den > 0 else 0.0
                    )
                    metrics[_layer_metric_key(layer, "intensity_avg")] = (
                        float(planned_muscle_int_sum.get(name, 0.0)) / int_den if int_den > 0 else 0.0
                    )
                elif layer.startswith("muscle_group:"):
                    name = layer.split(":", 1)[1]
                    metrics[_layer_metric_key(layer, "volume_sum")] = float(
                        planned_muscle_group_volume.get(name, 0.0)
                    )
                    metrics[_layer_metric_key(layer, "sets_count")] = float(planned_muscle_group_sets.get(name, 0.0))
                    sets = float(planned_muscle_group_sets.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "reps_per_set_avg")] = (
                        float(planned_muscle_group_volume.get(name, 0.0)) / sets if sets > 0 else 0.0
                    )
                    wden = float(planned_muscle_group_weight_den.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "kilograms_avg")] = (
                        float(planned_muscle_group_weight_sum.get(name, 0.0)) / wden if wden > 0 else 0.0
                    )
                    metrics[_layer_metric_key(layer, "tonnage_sum")] = float(planned_muscle_group_tonnage.get(name, 0.0))
                    e1cnt = float(planned_muscle_group_e1rm_cnt.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "one_rm_est_avg")] = (
                        float(planned_muscle_group_e1rm_sum.get(name, 0.0)) / e1cnt if e1cnt > 0 else 0.0
                    )
                    eff_cnt = float(planned_muscle_group_eff_cnt.get(name, 0.0))
                    int_cnt = float(planned_muscle_group_int_cnt.get(name, 0.0))
                    metrics[_layer_metric_key(layer, "effort_avg")] = (
                        float(planned_muscle_group_eff_sum.get(name, 0.0)) / eff_cnt if eff_cnt > 0 else 0.0
                    )
                    metrics[_layer_metric_key(layer, "intensity_avg")] = (
                        float(planned_muscle_group_int_sum.get(name, 0.0)) / int_cnt if int_cnt > 0 else 0.0
                    )

        if include_meta:
            for ex_id, agg in per_exercise.items():
                layer = f"exercise:{ex_id}"
                planned_layer_totals[layer] = planned_layer_totals.get(layer, 0.0) + float(agg.get("volume_sum", 0.0))
            for name, v in planned_muscle_volume.items():
                layer = f"muscle:{name}"
                planned_layer_totals[layer] = planned_layer_totals.get(layer, 0.0) + float(v)
            for name, v in planned_muscle_group_volume.items():
                layer = f"muscle_group:{name}"
                planned_layer_totals[layer] = planned_layer_totals.get(layer, 0.0) + float(v)

        actual_metrics = None
        if wid in sessions_by_wid:
            sess = sessions_by_wid[wid]
            insts = instances_by_wid.get(wid, [])
            actual_metrics = _compute_actual_metrics(sess, insts, rpe_table)
            if parsed_layers:
                layer_actuals = _compute_actual_layer_metrics(sess, insts, parsed_layers, rpe_table)
                if layer_actuals:
                    actual_metrics = {**(actual_metrics or {}), **layer_actuals}

            if include_meta and actual_metrics:
                for k, v in actual_metrics.items():
                    if k.startswith("layer:") and k.endswith(":volume_sum"):
                        layer = k.split(":", 1)[1].rsplit(":", 1)[0]
                        actual_layer_totals[layer] = actual_layer_totals.get(layer, 0.0) + float(v)

        items.append(
            PlanAnalyticsItem(
                workout_id=wid, order_index=order_index, date=date, metrics=metrics, actual_metrics=actual_metrics
            )
        )

    meta: dict[str, Any] | None = None
    if include_meta:
        def _sorted_layers(src: dict[str, float]) -> list[tuple[str, float]]:
            pairs = list(src.items())
            pairs.sort(key=lambda x: x[1], reverse=True)
            return pairs[:top_layers_limit]

        exercise_label_map: dict[str, str] = {}
        for ex_id, payload in exercise_defs.items():
            nm = payload.get("name")
            if isinstance(nm, str) and nm:
                exercise_label_map[str(ex_id)] = nm

        available_muscles: set[str] = set()
        available_muscle_groups: set[str] = set()
        for payload in exercise_defs.values():
            if not isinstance(payload, dict):
                continue
            mg = payload.get("muscle_group")
            if isinstance(mg, str) and mg:
                available_muscle_groups.add(mg)
            for m in (payload.get("target_muscles") or []):
                if isinstance(m, str) and m:
                    available_muscles.add(m)
            for m in (payload.get("synergist_muscles") or []):
                if isinstance(m, str) and m:
                    available_muscles.add(m)

        meta = {
            "group_by": group_by,
            "available_metrics": [
                "sets_count",
                "volume_sum",
                "reps_per_set_avg",
                "kilograms_avg",
                "tonnage_sum",
                "one_rm_est_avg",
                "intensity_avg",
                "effort_avg",
            ],
            "available_muscles": sorted(available_muscles),
            "available_muscle_groups": sorted(available_muscle_groups),
            "requested_layers": parsed_layers,
            "planned_layers": [
                {"layer": k, "volume_sum": float(v)}
                for k, v in _sorted_layers(planned_layer_totals)[:top_layers_limit]
            ],
            "actual_layers": [
                {"layer": k, "volume_sum": float(v)}
                for k, v in _sorted_layers(actual_layer_totals)
            ],
            "exercise_labels": exercise_label_map,
        }

    return PlanAnalyticsResponse(items=items, meta=meta)
