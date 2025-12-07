from __future__ import annotations

import json
import os
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.calendar import AppliedCalendarPlan, AppliedPlanWorkout
from ..models.macro import PlanMacro

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

logger = structlog.get_logger(__name__)

try:
    from ..rpc import get_intensity as rpc_get_intensity
    from ..rpc import get_volume as rpc_get_volume
except ImportError:  # pragma: no cover
    rpc_get_intensity = None
    rpc_get_volume = None


def _get_dict(obj: dict[str, Any] | None, key: str) -> dict[str, Any]:
    """Safely get a dict value, returning empty dict if missing or wrong type."""
    if obj is None:
        return {}
    val = obj.get(key)
    return val if isinstance(val, dict) else {}


class MacroEngine:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    async def run_for_applied_plan(
        self, applied_plan_id: int, anchor: str = "current", index_offset: int | None = None
    ) -> dict[str, Any]:
        logger.info(
            "MacroEngine.run_for_applied_plan start",
            applied_plan_id=applied_plan_id,
            user_id=self.user_id,
        )
        plan = await self._load_applied_plan(applied_plan_id)
        if not plan:
            return {
                "applied_plan_id": applied_plan_id,
                "macros_evaluated": 0,
                "actions_applied": 0,
                "preview": [],
            }

        macros = await self._load_plan_macros(plan.calendar_plan_id)
        ordered_workouts = await self._load_applied_workouts(applied_plan_id)
        current_idx = int(getattr(plan, "current_workout_index", 0) or 0)
        if anchor and str(anchor).lower().strip() == "previous":
            current_idx = max(0, current_idx - 1)
        if index_offset is not None:
            current_idx = max(0, current_idx + index_offset)

        preview: list[dict[str, Any]] = []
        for m in macros:
            rule = self._safe_parse_rule(m.rule_json)
            duration = _get_dict(rule, "duration")
            duration_scope = duration.get("scope") or "Next_N_Workouts"
            count = int(duration.get("count") or 1)

            target_workouts = self._select_next_n_workouts(ordered_workouts, current_idx, count)
            matched_workouts = await self._filter_by_trigger(
                rule,
                target_workouts,
                {"ordered_workouts": ordered_workouts, "current_index": current_idx},
            )
            patches = await self._build_patches(rule, matched_workouts)
            try:
                trig = _get_dict(rule, "trigger")
                cond = _get_dict(rule, "condition")
                metric = str(trig.get("metric") or "").strip()
                op = str(cond.get("op") or "").strip()
                value = cond.get("value")
                rng = cond.get("range") or cond.get("values")
                if matched_workouts:
                    logger.info(
                        "Macro trigger fired | macro_id=%s name=%s metric=%s op=%s "
                        "value=%s range=%s matched_count=%d matched_workouts=%s",
                        m.id,
                        m.name,
                        metric,
                        op,
                        value,
                        rng,
                        len(matched_workouts),
                        matched_workouts,
                    )
                logger.info(
                    "Macro patches built | macro_id=%s name=%s patches_count=%d",
                    m.id,
                    m.name,
                    len(patches) if isinstance(patches, list) else 0,
                )
            except Exception:
                logger.exception("MacroEngine.run_for_applied_plan_logging_failed", macro_id=m.id)

            plan_changes: list[dict[str, Any]] = []
            try:
                action = _get_dict(rule, "action")
                a_type = str(action.get("type") or "").strip()
                params = _get_dict(action, "params")
                mode = str(params.get("mode") or "").strip()
                if a_type == "Inject_Mesocycle":
                    placement = _get_dict(params, "placement")
                    on_conflict = params.get("on_conflict") or "Shift_Forward"

                    if matched_workouts:
                        if mode == "by_Template":
                            tpl_id = params.get("template_id")
                            if tpl_id is not None:
                                plan_changes.append(
                                    {
                                        "type": "Inject_Mesocycle",
                                        "params": {
                                            "template_id": tpl_id,
                                            "placement": placement,
                                            "on_conflict": on_conflict,
                                        },
                                    }
                                )
                        elif mode == "by_Existing":
                            src_id = params.get("source_mesocycle_id") or params.get("mesocycle_id")
                            if src_id is not None:
                                plan_changes.append(
                                    {
                                        "type": "Inject_Mesocycle",
                                        "params": {
                                            "source_mesocycle_id": src_id,
                                            "placement": placement,
                                            "on_conflict": on_conflict,
                                        },
                                    }
                                )
            except Exception:
                logger.exception("MacroEngine.plan_changes_build_failed", macro_id=m.id)
                plan_changes = []
            preview.append(
                {
                    "macro_id": m.id,
                    "name": m.name,
                    "is_active": m.is_active,
                    "priority": m.priority,
                    "duration": {"scope": duration_scope, "count": count},
                    "target_workouts": target_workouts,
                    "matched_workouts": matched_workouts,
                    "patches": patches,
                    "plan_changes": plan_changes,
                }
            )

        summary = {
            "applied_plan_id": applied_plan_id,
            "calendar_plan_id": plan.calendar_plan_id,
            "macros_evaluated": len(macros),
            "actions_applied": 0,
            "preview": preview,
        }
        return summary

    async def _load_applied_plan(self, applied_plan_id: int) -> AppliedCalendarPlan | None:
        stmt = (
            select(AppliedCalendarPlan)
            .where(AppliedCalendarPlan.id == applied_plan_id)
            .where(AppliedCalendarPlan.user_id == self.user_id)
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def _load_plan_macros(self, calendar_plan_id: int) -> list[PlanMacro]:
        stmt = (
            select(PlanMacro)
            .where(PlanMacro.calendar_plan_id == calendar_plan_id)
            .where(PlanMacro.is_active.is_(True))
            .order_by(PlanMacro.priority.asc(), PlanMacro.id.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def _load_applied_workouts(self, applied_plan_id: int) -> list[dict[str, int]]:
        stmt = (
            select(AppliedPlanWorkout)
            .where(AppliedPlanWorkout.applied_plan_id == applied_plan_id)
            .order_by(AppliedPlanWorkout.order_index.asc())
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        return [{"workout_id": i.workout_id, "order_index": i.order_index} for i in items]

    def _select_next_n_workouts(self, ordered_workouts: list[dict[str, int]], current_index: int, n: int) -> list[int]:
        if not ordered_workouts:
            return []

        pipeline = [w for w in ordered_workouts if int(w.get("order_index", 0)) >= current_index]
        return [w.get("workout_id") for w in pipeline[: max(0, int(n))]]

    def _safe_parse_rule(self, s: str | None) -> dict[str, Any]:
        if not s:
            return {}
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            return {}

    async def _filter_by_trigger(
        self, rule: dict[str, Any], workout_ids: list[int], ctx: dict[str, Any] | None = None
    ) -> list[int]:
        if not workout_ids:
            return []
        trigger = _get_dict(rule, "trigger")
        condition = _get_dict(rule, "condition")

        try:
            self._last_ctx = ctx or {}
        except Exception:
            logger.exception("MacroEngine._filter_by_trigger_ctx_failed", exc_info=True)
            self._last_ctx = {}

        metric = str(trigger.get("metric") or "").strip()
        if not metric:
            return []

        supported_metrics = {
            "e1RM",
            "Performance_Trend",
            "Readiness_Score",
            "RPE_Session",
            "Total_Reps",
            "RPE_Delta_From_Plan",
            "Reps_Delta_From_Plan",
        }
        if metric not in supported_metrics:
            logger.info("MacroEngine._filter_by_trigger unsupported metric=%s", metric)
            return []

        op = str(condition.get("op") or "").strip()
        value = condition.get("value")
        rng = condition.get("range") or condition.get("values")

        matched: list[int] = []

        if metric in {"Readiness_Score", "RPE_Session"}:
            metrics = await self._fetch_workout_metrics(workout_ids)
            for wid in workout_ids:
                data = metrics.get(wid) or {}
                v = data.get("readiness_score") if metric == "Readiness_Score" else data.get("rpe_session")

                if op == "holds_for":
                    rel = str(condition.get("relation") or "<=").strip()
                    n = int(condition.get("n") or 3)
                    rng_param: list[float] | None = None
                    thr: float | None = None
                    cond_range = condition.get("range")
                    cond_range = cond_range if isinstance(cond_range, list) else None
                    if rel in {"in_range", "not_in_range"}:
                        if cond_range and len(cond_range) >= 2:
                            try:
                                a = float(cond_range[0])
                                b = float(cond_range[1])
                                rng_param = [a, b]
                            except (TypeError, ValueError):
                                rng_param = None
                    else:
                        try:
                            thr = float(value)
                        except (TypeError, ValueError):
                            thr = None

                    if metric == "Readiness_Score" and thr is None and rng_param is None:
                        try:
                            thr = float(os.getenv("READINESS_SCORE_HOLDS_FOR_THRESHOLD", 8))
                        except (TypeError, ValueError):
                            thr = 8.0

                    if await self._holds_for_metric(metric, rel, thr, n, ctx, rng=rng_param):
                        return workout_ids
                    return []
                else:
                    try:
                        if self._compare(op, v, value, rng):
                            matched.append(wid)
                    except (TypeError, ValueError):
                        continue
            return matched

        if metric == "e1RM":
            ex_id = trigger.get("exercise_id")
            ex_ids = trigger.get("exercise_ids") if isinstance(trigger.get("exercise_ids"), list) else None
            if ex_id is not None and not ex_ids:
                ex_ids = [ex_id]

            if not ex_ids:
                logger.info("MacroEngine._filter_by_trigger e1RM requires exercise_id(s)")
                return []
            for wid in workout_ids:
                v = await self._e1rm_for_wid(wid, ex_ids)
                try:
                    if self._compare(op, v, value, rng):
                        matched.append(wid)
                except (TypeError, ValueError):
                    continue
            return matched

        if metric == "Performance_Trend":
            relation_op = str(condition.get("op") or "").strip()
            n = int(condition.get("n") or 5)
            if relation_op not in {"stagnates_for", "deviates_from_avg"}:
                return []
            ex_id = trigger.get("exercise_id")
            ex_ids = trigger.get("exercise_ids") if isinstance(trigger.get("exercise_ids"), list) else None
            if ex_id is not None and not ex_ids:
                ex_ids = [ex_id]
            if not ex_ids:
                logger.info("MacroEngine.Performance_Trend requires exercise_id(s)")
                return []

            series = await self._trend_series_e1rm_prev_windows(ex_ids, n)
            if not series or len(series) < n:
                return []
            values = [v for (_, v) in series[-n:]]
            if relation_op == "stagnates_for":
                eps = float(condition.get("epsilon_percent") or 1.0)
                ok = self._trend_stagnates(values, eps)
                logger.info("Trend.stagnates_for | n=%d eps=%.4f series=%s result=%s", n, eps, values, ok)
                return workout_ids if ok else []
            else:
                val_pct = float(condition.get("value_percent") or 1.0)
                direction = (condition.get("direction") or "").strip() or None
                ok = self._trend_deviates(values, val_pct, direction)
                logger.info(
                    "Trend.deviates_from_avg | n=%d value_percent=%.4f dir=%s result=%s", n, val_pct, direction, ok
                )
                return workout_ids if ok else []

        if metric == "Total_Reps":
            ex_id = trigger.get("exercise_id")
            ex_ids = trigger.get("exercise_ids") if isinstance(trigger.get("exercise_ids"), list) else None
            if ex_id is not None and not ex_ids:
                ex_ids = [ex_id]
            details = await self._fetch_workout_details(workout_ids)
            for wid in workout_ids:
                payload = details.get(wid) or {}
                total = 0
                for ex in payload.get("exercises", []) or []:
                    eid = ex.get("exercise_id")
                    if ex_ids and eid not in ex_ids:
                        continue
                    for s in ex.get("sets", []) or []:
                        try:
                            reps = int(s.get("volume")) if s.get("volume") is not None else None
                        except (TypeError, ValueError):
                            reps = None
                        if reps:
                            total += reps
                if op == "holds_for":
                    rel = str(condition.get("relation") or ">=").strip()
                    n = int(condition.get("n") or 3)

                    if await self._holds_for_series(
                        lambda widx: self._total_reps_for_workout(widx, ex_ids),
                        rel,
                        float(value),
                        n,
                        ctx,
                    ):
                        return workout_ids
                    return []
                else:
                    try:
                        if self._compare(op, total, value, rng):
                            matched.append(wid)
                    except (TypeError, ValueError):
                        continue
            return matched

        if metric in {"RPE_Delta_From_Plan", "Reps_Delta_From_Plan"}:
            ex_id = trigger.get("exercise_id")
            ex_ids = trigger.get("exercise_ids") if isinstance(trigger.get("exercise_ids"), list) else None
            if ex_id is not None and not ex_ids:
                ex_ids = [ex_id]

            if op == "holds_for":
                relation = str(condition.get("relation") or ">=").strip()
                n = int(condition.get("n") or 1)
                try:
                    thr = float(value)
                except (TypeError, ValueError):
                    thr = 0.0

                async def _delta_value_for_wid(wid: int) -> float | None:
                    details = await self._fetch_workout_details([wid])
                    instances = await self._fetch_exercise_instances([wid])
                    pd = (details.get(wid) or {}).get("exercises") or []
                    inst_list = instances.get(wid) or []
                    inst_by_eid: dict[int, dict] = {}
                    for inst in inst_list:
                        try:
                            eid = int(inst.get("exercise_list_id"))
                            inst_by_eid[eid] = inst
                        except (TypeError, ValueError):
                            continue
                    deltas: list[float] = []
                    for ex in pd:
                        eid = ex.get("exercise_id")
                        if ex_ids and eid not in ex_ids:
                            continue
                        sets_plan = list(ex.get("sets") or [])
                        inst = inst_by_eid.get(eid)
                        if not inst:
                            continue
                        sets_actual = list(inst.get("sets") or [])
                        k = min(len(sets_plan), len(sets_actual))
                        for i in range(k):
                            sp = sets_plan[i] or {}
                            sa = sets_actual[i] or {}
                            try:
                                if metric == "RPE_Delta_From_Plan":
                                    p = sp.get("effort")
                                    a = sa.get("rpe") if sa.get("rpe") is not None else sa.get("effort")
                                    if p is None or a is None:
                                        continue
                                    deltas.append(float(a) - float(p))
                                else:
                                    p = sp.get("volume")
                                    a = sa.get("reps") or sa.get("volume")
                                    if p is None or a is None:
                                        continue
                                    deltas.append(float(a) - float(p))
                            except (TypeError, ValueError):
                                continue
                    if not deltas:
                        return None
                    return sum(deltas) / len(deltas)

                if await self._holds_for_series(_delta_value_for_wid, relation, thr, n, ctx):
                    return workout_ids
                return []

            if op == "holds_for_sets":
                relation = str(condition.get("relation") or "<=").strip()
                n_sets = int(condition.get("n_sets") or condition.get("n") or 1)

                try:
                    thr = float(value)
                except (TypeError, ValueError):
                    thr = 0.0
                plan_details = await self._fetch_workout_details(workout_ids)
                instances = await self._fetch_exercise_instances(workout_ids)
                for wid in workout_ids:
                    if await self._reps_delta_consecutive_sets(
                        wid, ex_ids, relation, thr, n_sets, plan_details, instances, metric
                    ):
                        matched.append(wid)
                return matched

            plan_details = await self._fetch_workout_details(workout_ids)
            instances = await self._fetch_exercise_instances(workout_ids)

            def _delta_for_wid(wid: int) -> float | None:
                pd = (plan_details.get(wid) or {}).get("exercises") or []
                inst_list = instances.get(wid) or []

                inst_by_eid: dict[int, dict] = {}
                for inst in inst_list:
                    try:
                        eid = int(inst.get("exercise_list_id"))
                        inst_by_eid[eid] = inst
                    except (TypeError, ValueError):
                        continue
                deltas: list[float] = []
                for ex in pd:
                    eid = ex.get("exercise_id")
                    if ex_ids and eid not in ex_ids:
                        continue
                    sets_plan = list(ex.get("sets") or [])
                    inst = inst_by_eid.get(eid)
                    if not inst:
                        continue
                    sets_actual = list(inst.get("sets") or [])
                    k = min(len(sets_plan), len(sets_actual))
                    for i in range(k):
                        sp = sets_plan[i] or {}
                        sa = sets_actual[i] or {}
                        try:
                            if metric == "RPE_Delta_From_Plan":
                                p = sp.get("effort")
                                a = sa.get("rpe") if sa.get("rpe") is not None else sa.get("effort")
                                if p is None or a is None:
                                    continue
                                deltas.append(float(a) - float(p))
                            else:
                                p = sp.get("volume")
                                a = sa.get("reps") or sa.get("volume")
                                if p is None or a is None:
                                    continue
                                deltas.append(float(a) - float(p))
                        except Exception:
                            continue
                if not deltas:
                    return None
                return sum(deltas) / len(deltas)

            for wid in workout_ids:
                v = _delta_for_wid(wid)
                try:
                    if self._compare(op, v, value, rng):
                        matched.append(wid)
                except (TypeError, ValueError):
                    continue
            return matched

        return workout_ids

    def _compare(self, op: str, v: Any, target: Any, rng: Any) -> bool:
        if v is None:
            return False
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return False
        if op in (">", "gt"):
            return fv > float(target)
        if op in ("<", "lt"):
            return fv < float(target)
        if op in (">=", "ge"):
            return fv >= float(target)
        if op in ("<=", "le"):
            return fv <= float(target)
        if op in ("=", "==", "eq"):
            return abs(fv - float(target)) < 1e-6
        if op in ("!=", "ne"):
            return abs(fv - float(target)) >= 1e-6
        if op in ("in_range", "in"):
            if isinstance(rng, list | tuple) and len(rng) >= 2:
                a, b = float(rng[0]), float(rng[1])
                lo, hi = (a, b) if a <= b else (b, a)
                return (fv >= lo) and (fv <= hi)
            return False
        if op in ("not_in_range", "not_in"):
            if isinstance(rng, list | tuple) and len(rng) >= 2:
                a, b = float(rng[0]), float(rng[1])
                lo, hi = (a, b) if a <= b else (b, a)
                return not ((fv >= lo) and (fv <= hi))
            return True

    async def _holds_for_metric(
        self,
        metric: str,
        relation: str,
        threshold: float | None,
        n: int,
        ctx: dict[str, Any] | None,
        rng: list[float] | None = None,
    ) -> bool:
        if not ctx:
            return False
        ordered = ctx.get("ordered_workouts") or []
        current_index = int(ctx.get("current_index") or 0)
        prev = [w.get("workout_id") for w in ordered if int(w.get("order_index", 0)) < current_index]
        if not prev:
            return False
        window = prev[-n:]
        if len(window) < n:
            return False
        metrics = await self._fetch_workout_metrics(window)

        def _val(wid: int) -> float | None:
            d = metrics.get(wid) or {}
            if metric == "Readiness_Score":
                return d.get("readiness_score")
            if metric == "RPE_Session":
                return d.get("rpe_session")
            return None

        for wid in window:
            v = _val(wid)
            if v is None:
                return False
            target = threshold
            if relation in {"in_range", "not_in_range"}:
                target = threshold if threshold is not None else (rng[0] if rng else None)
            if target is None and relation not in {"in_range", "not_in_range"}:
                return False
            if not self._compare(relation, v, target, rng):
                return False
        return True

    async def _holds_for_series(
        self,
        get_value_for_wid,
        relation: str,
        threshold: float,
        n: int,
        ctx: dict[str, Any] | None,
    ) -> bool:
        if not ctx:
            return False
        ordered = ctx.get("ordered_workouts") or []
        current_index = int(ctx.get("current_index") or 0)
        prev = [w.get("workout_id") for w in ordered if int(w.get("order_index", 0)) < current_index]
        window = prev[-n:] if prev else []
        if len(window) < n:
            return False

        for wid in window:
            v = await get_value_for_wid(wid) if callable(get_value_for_wid) else get_value_for_wid(wid)
            if v is None:
                return False
            if not self._compare(relation, v, threshold, None):
                return False
        return True

    async def _total_reps_for_workout(self, wid: int, filter_ex_ids: list[int] | None) -> float | None:
        details = await self._fetch_workout_details([wid])
        payload = details.get(wid) or {}
        total = 0
        for ex in payload.get("exercises", []) or []:
            eid = ex.get("exercise_id")
            if filter_ex_ids and eid not in filter_ex_ids:
                continue
            for s in ex.get("sets", []) or []:
                try:
                    reps = int(s.get("volume")) if s.get("volume") is not None else None
                except (TypeError, ValueError):
                    reps = None
                if reps:
                    total += reps
        return float(total)

    async def _reps_delta_consecutive_sets(
        self,
        wid: int,
        filter_ex_ids: list[int] | None,
        relation: str,
        threshold: float,
        n_sets: int,
        plan_details_cache: dict[int, dict[str, Any]] | None,
        instances_cache: dict[int, list[dict[str, Any]]] | None,
        metric: str,
    ) -> bool:
        plan_details = plan_details_cache or await self._fetch_workout_details([wid])
        instances = instances_cache or await self._fetch_exercise_instances([wid])
        pd = (plan_details.get(wid) or {}).get("exercises") or []
        inst_list = instances.get(wid) or []
        inst_by_eid: dict[int, dict] = {}
        for inst in inst_list:
            try:
                eid = int(inst.get("exercise_list_id"))
                inst_by_eid[eid] = inst
            except (TypeError, ValueError):
                continue
        for ex in pd:
            eid = ex.get("exercise_id")
            if filter_ex_ids and eid not in filter_ex_ids:
                continue
            inst = inst_by_eid.get(eid)
            if not inst:
                continue
            sets_plan = list(ex.get("sets") or [])
            sets_actual = list(inst.get("sets") or [])
            k = min(len(sets_plan), len(sets_actual))
            if k == 0:
                continue

            deltas: list[float] = []
            for i in range(k):
                sp = sets_plan[i] or {}
                sa = sets_actual[i] or {}
                try:
                    if metric == "RPE_Delta_From_Plan":
                        p = sp.get("effort")

                        a = sa.get("rpe") if sa.get("rpe") is not None else sa.get("effort")
                        if p is None or a is None:
                            deltas.append(float("nan"))
                        else:
                            deltas.append(float(a) - float(p))
                    else:
                        p = sp.get("volume")
                        a = sa.get("reps") or sa.get("volume")
                        if p is None or a is None:
                            deltas.append(float("nan"))
                        else:
                            deltas.append(float(a) - float(p))
                except (TypeError, ValueError):
                    deltas.append(float("nan"))

            run = 0
            for d in deltas:
                if d != d:
                    run = 0
                    continue
                if self._compare(relation, d, threshold, None):
                    run += 1
                    if run >= n_sets:
                        return True
                else:
                    run = 0
        return False

    async def _fetch_exercise_instances(self, workout_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
        out: dict[int, list[dict[str, Any]]] = {}
        if not workout_ids or not httpx:
            return out
        base = os.getenv("EXERCISES_SERVICE_URL")
        if not base:
            return out
        base = base.rstrip("/")
        async with httpx.AsyncClient(timeout=6.0) as client:
            for wid in workout_ids:
                try:
                    url = f"{base}/exercises/instances/workouts/{wid}/instances"
                    headers = {"X-User-Id": self.user_id}
                    res = await client.get(url, headers=headers)
                    if res.status_code == 200:
                        try:
                            data = res.json()
                        except ValueError:
                            logger.warning(
                                "MacroEngine._fetch_exercise_instances_json_failed",
                                workout_id=wid,
                                exc_info=True,
                            )
                            continue
                        if isinstance(data, list):
                            out[wid] = data
                except httpx.RequestError:
                    logger.warning(
                        "MacroEngine._fetch_exercise_instances_failed",
                        workout_id=wid,
                        exc_info=True,
                    )
        return out

    async def _fetch_user_max_histories(self, exercise_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
        histories: dict[int, list[dict[str, Any]]] = {eid: [] for eid in (exercise_ids or [])}

        try:
            ordered = getattr(self, "_last_ctx", {}).get("ordered_workouts") or []
            current_index = int(getattr(self, "_last_ctx", {}).get("current_index") or 0)
            prev_wids = [w.get("workout_id") for w in ordered if int(w.get("order_index", 0)) < current_index]
        except (AttributeError, TypeError, ValueError):
            logger.warning("MacroEngine._fetch_user_max_histories_ctx_invalid", exc_info=True)
            prev_wids = []
        if not prev_wids or not exercise_ids:
            return histories

        details = await self._fetch_workout_details(prev_wids)
        instances = await self._fetch_exercise_instances(prev_wids)
        for wid in prev_wids:
            payload = details.get(wid) or {}
            ex_list = payload.get("exercises") or []
            date = payload.get("date")
            inst_list = instances.get(wid) or []
            inst_by_eid: dict[int, dict] = {}
            for inst in inst_list:
                try:
                    eid = int(inst.get("exercise_list_id"))
                    inst_by_eid[eid] = inst
                except (TypeError, ValueError):
                    continue
            for ex in ex_list:
                eid = ex.get("exercise_id")
                if eid not in histories:
                    continue
                inst = inst_by_eid.get(eid)
                if not inst:
                    continue
                best_e1rm = None
                best_weight = None
                best_reps = None
                for s in inst.get("sets") or []:
                    try:
                        w = s.get("weight") if s.get("weight") is not None else s.get("working_weight")
                        r = s.get("reps") or s.get("volume")
                        if w is None or r is None:
                            continue
                        w = float(w)
                        r = int(r)
                        if r <= 0 or w <= 0:
                            continue
                        e = self._e1rm_from_weight_reps(w, r)
                        if best_e1rm is None or e > best_e1rm:
                            best_e1rm = e
                            best_weight = w
                            best_reps = r
                    except (TypeError, ValueError):
                        continue
                if best_e1rm is not None and date is not None:
                    histories[eid].append(
                        {
                            "date": date,
                            "max_weight": best_weight,
                            "rep_max": best_reps,
                            "e1rm": best_e1rm,
                        }
                    )

        for eid, items in histories.items():
            try:
                items.sort(key=lambda x: x.get("date") or "")
            except (TypeError, ValueError):
                logger.warning(
                    "MacroEngine._fetch_user_max_histories_sort_failed",
                    exercise_id=eid,
                    exc_info=True,
                )
        return histories

    async def _e1rm_for_wid(self, wid: int, filter_ex_ids: list[int]) -> float | None:
        details = await self._fetch_workout_details([wid])
        instances = await self._fetch_exercise_instances([wid])
        ex_list = (details.get(wid) or {}).get("exercises") or []
        inst_list = instances.get(wid) or []
        inst_by_eid: dict[int, dict] = {}
        for inst in inst_list:
            try:
                eid = int(inst.get("exercise_list_id"))
                inst_by_eid[eid] = inst
            except (TypeError, ValueError):
                continue
        best = None
        for ex in ex_list:
            eid = ex.get("exercise_id")
            if filter_ex_ids and eid not in filter_ex_ids:
                continue
            inst = inst_by_eid.get(eid)
            if not inst:
                continue
            for s in inst.get("sets") or []:
                try:
                    w = s.get("weight") if s.get("weight") is not None else s.get("working_weight")
                    r = s.get("reps") or s.get("volume")
                    if w is None or r is None:
                        continue
                    w = float(w)
                    r = int(r)
                    if r <= 0 or w <= 0:
                        continue
                    e = self._e1rm_from_weight_reps(w, r)
                    best = e if (best is None or e > best) else best
                except (TypeError, ValueError):
                    continue
        return best

    async def _trend_series_e1rm_prev_windows(self, filter_ex_ids: list[int], window_n: int) -> list[tuple[str, float]]:
        try:
            ordered = getattr(self, "_last_ctx", {}).get("ordered_workouts") or []
            current_index = int(getattr(self, "_last_ctx", {}).get("current_index") or 0)
            prev = [w.get("workout_id") for w in ordered if int(w.get("order_index", 0)) < current_index]
        except (AttributeError, TypeError, ValueError):
            logger.warning("MacroEngine._trend_series_ctx_invalid", exc_info=True)
            prev = []
        if not prev:
            return []
        details = await self._fetch_workout_details(prev)
        await self._fetch_exercise_instances(prev)
        series: list[tuple[str, float]] = []
        for wid in prev:
            date = (details.get(wid) or {}).get("date")
            val = await self._e1rm_for_wid(wid, filter_ex_ids)
            if date is not None and val is not None:
                series.append((date, float(val)))
        series.sort(key=lambda x: x[0])
        return series[-max(1, int(window_n * 2)) :]

    @staticmethod
    def _e1rm_from_weight_reps(weight: float, reps: int) -> float:
        if reps <= 1:
            return float(weight)
        return float(weight) * (1.0 + (float(reps) / 30.0))

    @staticmethod
    def _trend_stagnates(values: list[float], epsilon_percent: float) -> bool:
        if not values or len(values) < 2:
            return False
        vals = [float(v) for v in values if v is not None]
        if len(vals) < 2:
            return False
        lo = min(vals)
        hi = max(vals)
        mu = sum(vals) / len(vals)
        if mu <= 0:
            return False
        width_pct = (hi - lo) / mu * 100.0
        return width_pct <= float(epsilon_percent)

    @staticmethod
    def _trend_deviates(values: list[float], value_percent: float, direction: str | None) -> bool:
        if not values or len(values) < 2:
            return False
        vals = [float(v) for v in values if v is not None]
        if len(vals) < 2:
            return False
        last = vals[-1]
        prior = vals[:-1]
        mu = sum(prior) / len(prior)
        if mu == 0:
            return False
        delta_pct = (last - mu) / abs(mu) * 100.0
        thr = float(value_percent)
        if direction == "positive":
            return delta_pct >= thr
        if direction == "negative":
            return (-delta_pct) >= thr
        return abs(delta_pct) >= thr

    async def _fetch_workout_metrics(self, workout_ids: list[int]) -> dict[int, dict[str, Any]]:
        out: dict[int, dict[str, Any]] = {}
        if not workout_ids:
            return out
        base = os.getenv("WORKOUTS_SERVICE_URL")
        if not base:
            return out
        base = base.rstrip("/")
        if not httpx:
            return out

        async with httpx.AsyncClient(timeout=5.0) as client:
            for wid in workout_ids:
                try:
                    url = f"{base}/workouts/{wid}"
                    headers = {"X-User-Id": self.user_id}
                    res = await client.get(url, headers=headers)
                    if res.status_code == 200:
                        try:
                            data = res.json() or {}
                        except ValueError:
                            logger.warning(
                                "MacroEngine._fetch_workout_metrics_json_failed",
                                workout_id=wid,
                                exc_info=True,
                            )
                            continue
                        out[wid] = {
                            "readiness_score": data.get("readiness_score"),
                            "rpe_session": data.get("rpe_session"),
                        }
                except httpx.RequestError:
                    logger.warning(
                        "MacroEngine._fetch_workout_metrics_failed",
                        workout_id=wid,
                        exc_info=True,
                    )
        return out

    async def _build_patches(self, rule: dict[str, Any], workout_ids: list[int]) -> list[dict[str, Any]]:
        if not workout_ids:
            return []
        action = _get_dict(rule, "action")
        a_type = str(action.get("type") or "").strip()
        params = _get_dict(action, "params")
        mode = str(params.get("mode") or "").strip()

        if a_type not in {"Adjust_Load", "Adjust_Reps", "Adjust_Sets"}:
            return []
        if a_type == "Adjust_Load" and mode not in {"by_Percent", "to_Target"}:
            return []
        if a_type == "Adjust_Reps" and mode not in {"by_Value", "to_Target"}:
            return []
        if a_type == "Adjust_Sets" and mode != "by_Value":
            return []

        w_details = await self._fetch_workout_details(workout_ids)

        target = _get_dict(action, "target")
        allowed_ex_ids = await self._resolve_target_exercise_ids(target)
        patches: list[dict[str, Any]] = []

        if a_type == "Adjust_Load":
            try:
                delta = float(params.get("value")) if mode == "by_Percent" else None
            except Exception:
                delta = None
            factor = (1.0 + (delta / 100.0)) if (delta is not None) else None
            target_rpe = None
            if mode == "to_Target":
                try:
                    target_rpe = float(params.get("value"))
                except Exception:
                    target_rpe = None
            for wid, payload in w_details.items():
                for ex in payload.get("exercises", []):
                    exercise_id = ex.get("exercise_id")
                    if allowed_ex_ids is not None and exercise_id not in allowed_ex_ids:
                        continue
                    for s in ex.get("sets", []):
                        set_id = s.get("id")
                        intensity = s.get("intensity")
                        weight = s.get("working_weight") if s.get("working_weight") is not None else s.get("weight")
                        volume = s.get("volume")

                        new_intensity = None
                        new_weight = None
                        if mode == "by_Percent" and factor is not None:
                            try:
                                if intensity is not None:
                                    new_intensity = max(0, min(110, float(intensity) * factor))
                            except Exception:
                                new_intensity = None
                            try:
                                if weight is not None:
                                    new_weight = float(weight) * factor
                            except Exception:
                                new_weight = None
                        elif mode == "to_Target" and target_rpe is not None and rpc_get_intensity:
                            try:
                                reps_int = int(volume) if volume is not None else None
                            except Exception:
                                reps_int = None
                            if reps_int is not None:
                                try:
                                    new_intensity = await rpc_get_intensity(
                                        volume=reps_int, effort=target_rpe, headers=None
                                    )
                                except Exception:
                                    new_intensity = None

                        if new_intensity is None and new_weight is None:
                            continue
                        patch = {
                            "workout_id": wid,
                            "exercise_id": exercise_id,
                            "set_id": set_id,
                            "changes": {},
                        }
                        if new_intensity is not None:
                            patch["changes"]["intensity"] = round(new_intensity, 1)
                        if new_weight is not None:
                            patch["changes"]["working_weight"] = round(new_weight, 2)
                            patch["changes"]["weight"] = round(new_weight, 2)
                        patches.append(patch)

        elif a_type == "Adjust_Reps":
            try:
                offset = int(params.get("value")) if mode == "by_Value" else None
            except Exception:
                offset = None
            target_rpe = None
            if mode == "to_Target":
                try:
                    target_rpe = float(params.get("value"))
                except Exception:
                    target_rpe = None
            for wid, payload in w_details.items():
                for ex in payload.get("exercises", []):
                    exercise_id = ex.get("exercise_id")
                    for s in ex.get("sets", []):
                        set_id = s.get("id")
                        volume = s.get("volume")
                        intensity = s.get("intensity")

                        try:
                            base_reps = int(volume) if volume is not None else None
                        except Exception:
                            base_reps = None
                        if base_reps is None and not (mode == "to_Target" and intensity is not None):
                            continue
                        new_reps = None
                        if mode == "by_Value" and base_reps is not None and offset is not None:
                            new_reps = max(1, base_reps + offset)
                        elif (
                            mode == "to_Target" and target_rpe is not None and rpc_get_volume and intensity is not None
                        ):
                            try:
                                ii = float(intensity)
                                vol = await rpc_get_volume(intensity=int(ii), effort=target_rpe, headers=None)
                                if vol is not None:
                                    new_reps = max(1, int(vol))
                            except Exception:
                                new_reps = None
                        if new_reps is None or (base_reps is not None and new_reps == base_reps):
                            continue
                        patches.append(
                            {
                                "workout_id": wid,
                                "exercise_id": exercise_id,
                                "set_id": set_id,
                                "changes": {"volume": new_reps},
                            }
                        )

        elif a_type == "Adjust_Sets":
            try:
                delta_sets = int(params.get("value"))
            except Exception:
                delta_sets = 0
            if delta_sets == 0:
                return patches
            for wid, payload in w_details.items():
                for ex in payload.get("exercises", []):
                    exercise_id = ex.get("exercise_id")
                    if allowed_ex_ids is not None and exercise_id not in allowed_ex_ids:
                        continue
                    sets = list(ex.get("sets", []) or [])
                    if not sets:
                        continue
                    if delta_sets > 0:
                        template = sets[-1]
                        for i in range(delta_sets):
                            patches.append(
                                {
                                    "workout_id": wid,
                                    "exercise_id": exercise_id,
                                    "set_id": None,
                                    "changes": {
                                        "action": "add_set",
                                        "template": {
                                            "intensity": template.get("intensity"),
                                            "effort": template.get("effort"),
                                            "volume": template.get("volume"),
                                        },
                                    },
                                }
                            )
                    else:
                        remove_n = min(len(sets), abs(delta_sets))
                        for s in reversed(sets[-remove_n:]):
                            patches.append(
                                {
                                    "workout_id": wid,
                                    "exercise_id": exercise_id,
                                    "set_id": s.get("id"),
                                    "changes": {"action": "remove_set"},
                                }
                            )

    async def _resolve_target_exercise_ids(self, target: dict[str, Any]) -> set[int] | None:
        if not isinstance(target, dict) or not target:
            return None
        ex_id = target.get("exercise_id")
        ex_ids = target.get("exercise_ids") if isinstance(target.get("exercise_ids"), list) else None
        if ex_id is not None and not ex_ids:
            try:
                return {int(ex_id)}
            except Exception:
                return None
        if ex_ids:
            out: set[int] = set()
            for v in ex_ids:
                try:
                    out.add(int(v))
                except Exception:
                    continue
            return out if out else None

        selector = _get_dict(target, "selector")
        if not selector:
            return None
        if str(selector.get("type") or "").lower() != "tags":
            return set()
        val = _get_dict(selector, "value")
        mv = val.get("movement_type")
        rg = val.get("region")
        mg = val.get("muscle_group")
        eq = val.get("equipment")

        def _norm(x):
            if x is None:
                return None
            if isinstance(x, str):
                return {x.lower()}
            if isinstance(x, list):
                return {str(i).lower() for i in x}
            return None

        mv_set = _norm(mv)
        rg_set = _norm(rg)
        mg_set = _norm(mg)
        eq_set = _norm(eq)

        base = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002").rstrip("/")
        if not httpx:
            return None
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                url = f"{base}/exercises/definitions"
                res = await client.get(url)
                if res.status_code != 200:
                    return None
                data = res.json()
                if not isinstance(data, list):
                    return None
                out: set[int] = set()
                for item in data:
                    try:
                        eid = int(item.get("id"))
                    except Exception:
                        continue
                    mt = str(item.get("movement_type") or "").lower()
                    rgv = str(item.get("region") or "").lower()
                    mgl = str(item.get("muscle_group") or "").lower()
                    eqv = str(item.get("equipment") or "").lower()
                    if mv_set and mt not in mv_set:
                        continue
                    if rg_set and rgv not in rg_set:
                        continue
                    if mg_set and mgl not in mg_set:
                        continue
                    if eq_set and eqv not in eq_set:
                        continue
                    out.add(eid)
                return out if out else None
        except Exception:
            return None

        return None

    async def _fetch_workout_details(self, workout_ids: list[int]) -> dict[int, dict[str, Any]]:
        out: dict[int, dict[str, Any]] = {}
        if not workout_ids:
            return out
        base = os.getenv("WORKOUTS_SERVICE_URL")
        if not base:
            return out
        base = base.rstrip("/")
        if not httpx:
            return out

        async with httpx.AsyncClient(timeout=6.0) as client:
            for wid in workout_ids:
                try:
                    url = f"{base}/workouts/{wid}"
                    headers = {"X-User-Id": self.user_id}
                    res = await client.get(url, headers=headers)
                    if res.status_code == 200:
                        data = res.json() or {}

                        out[wid] = {
                            "exercises": data.get("exercises") or [],
                            "date": data.get("scheduled_for") or data.get("completed_at"),
                        }
                except Exception:
                    continue
        return out
