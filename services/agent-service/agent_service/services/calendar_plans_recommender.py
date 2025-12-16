from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .llm_wrapper import generate_structured_output
from .tool_agent import ToolSpec

_QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "frequency_per_week": {
            "type": "integer",
            "minimum": 1,
            "maximum": 14,
            "description": "Desired training sessions per week",
        },
        "duration_weeks_min": {"type": "integer", "minimum": 1},
        "duration_weeks_max": {"type": "integer", "minimum": 1},
        "primary_goal": {"type": "string"},
        "experience_level": {"type": "string"},
        "volume_level": {
            "type": "string",
            "enum": ["any", "low", "medium", "high"],
        },
        "keywords": {"type": "array", "items": {"type": "string"}},
        "exclude_keywords": {"type": "array", "items": {"type": "string"}},
    },
}


def _norm_str(v: Any) -> str:
    return str(v).strip().lower() if v is not None else ""


def _infer_volume_bucket(plan: dict[str, Any]) -> str:
    minutes = plan.get("session_duration_target_min")
    freq = plan.get("intended_frequency_per_week")

    try:
        minutes_i = int(minutes) if minutes is not None else None
    except Exception:
        minutes_i = None

    try:
        freq_i = int(freq) if freq is not None else None
    except Exception:
        freq_i = None

    if minutes_i is not None:
        if minutes_i >= 75:
            return "high"
        if minutes_i >= 50:
            return "medium"
        return "low"

    if freq_i is not None:
        if freq_i >= 6:
            return "high"
        if freq_i >= 4:
            return "medium"
        return "low"

    return "any"


def _workload_proxy(plan: dict[str, Any]) -> float:
    minutes = plan.get("session_duration_target_min")
    freq = plan.get("intended_frequency_per_week")

    minutes_i: int | None
    freq_i: int | None

    try:
        minutes_i = int(minutes) if minutes is not None else None
    except Exception:
        minutes_i = None

    try:
        freq_i = int(freq) if freq is not None else None
    except Exception:
        freq_i = None

    if minutes_i is not None:
        return float(minutes_i)
    if freq_i is not None:
        return float(freq_i) * 15.0
    return 0.0


@dataclass
class _ScoredPlan:
    score: float
    plan: dict[str, Any]
    reasons: list[str]


async def _parse_query(user_request: str) -> dict[str, Any]:
    prompt = (
        "Extract constraints from the user's request for choosing a training plan from a list. "
        "Use these available plan fields when interpreting: "
        "name, duration_weeks, intended_frequency_per_week, session_duration_target_min, "
        "primary_goal, intended_experience_level, notes. "
        "If the user does not specify a constraint, omit it. "
        "Interpret 'high volume'/'high-volume'/'высокообъёмный' as volume_level='high'. "
        "Interpret requests about maximizing tonnage ('tonnage', 'тоннаж', 'максимальный тоннаж') "
        "as volume_level='high'. "
        "Interpret 'low volume'/'низкообъёмный' as volume_level='low'. "
        "If no volume preference, set volume_level='any' or omit it.\n\n"
        f"User request: {user_request}"
    )
    parsed = await generate_structured_output(prompt=prompt, response_schema=_QUERY_SCHEMA, temperature=0.2)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def recommend_calendar_plans_tool(user_id: str, session_context: dict[str, Any]) -> ToolSpec:
    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        user_request = args.get("user_request") or ""
        top_k = args.get("top_k", 3)
        try:
            top_k = int(top_k)
        except Exception:
            top_k = 3
        top_k = max(1, min(top_k, 10))

        entities = session_context.get("entities") or {}
        plans_raw = None
        if isinstance(entities, dict):
            plans_raw = entities.get("calendar_plans")
        if plans_raw is None:
            plans_raw = session_context.get("calendar_plans")

        if not isinstance(plans_raw, list) or not plans_raw:
            return {"error": "No plans were provided in the current screen context."}

        plans: list[dict[str, Any]] = [p for p in plans_raw if isinstance(p, dict)]
        if not plans:
            return {"error": "No valid plan objects were provided in the current screen context."}

        query = await _parse_query(str(user_request))
        freq_req = query.get("frequency_per_week")
        dur_min = query.get("duration_weeks_min")
        dur_max = query.get("duration_weeks_max")
        goal_req = _norm_str(query.get("primary_goal"))
        lvl_req = _norm_str(query.get("experience_level"))
        volume_req = _norm_str(query.get("volume_level"))
        if not volume_req:
            volume_req = "any"
        keywords = [str(x) for x in (query.get("keywords") or []) if str(x).strip()]
        exclude_keywords = [str(x) for x in (query.get("exclude_keywords") or []) if str(x).strip()]

        scored: list[_ScoredPlan] = []

        for p in plans:
            score = 0.0
            reasons: list[str] = []

            p_name = str(p.get("name") or "")
            p_goal = _norm_str(p.get("primary_goal"))
            p_lvl = _norm_str(p.get("intended_experience_level"))

            p_freq = p.get("intended_frequency_per_week")
            try:
                p_freq_i = int(p_freq) if p_freq is not None else None
            except Exception:
                p_freq_i = None

            p_dur = p.get("duration_weeks")
            try:
                p_dur_i = int(p_dur) if p_dur is not None else None
            except Exception:
                p_dur_i = None

            p_notes = _norm_str(p.get("notes"))
            haystack = " ".join([p_name.lower(), p_goal, p_lvl, p_notes])

            excluded = False
            for ek in exclude_keywords:
                if ek.strip().lower() in haystack:
                    excluded = True
                    break
            if excluded:
                continue

            if freq_req is not None:
                try:
                    freq_req_i = int(freq_req)
                except Exception:
                    freq_req_i = None
                if freq_req_i is not None:
                    if p_freq_i is None:
                        score -= 0.25
                    else:
                        diff = abs(p_freq_i - freq_req_i)
                        score += max(0.0, 2.0 - diff)
                        if diff == 0:
                            reasons.append(f"Frequency matches: {p_freq_i}x/week")
                        else:
                            reasons.append(f"Frequency: {p_freq_i}x/week (requested {freq_req_i}x/week)")

            if dur_min is not None or dur_max is not None:
                if p_dur_i is None:
                    score -= 0.2
                else:
                    ok = True
                    if dur_min is not None:
                        try:
                            ok = ok and p_dur_i >= int(dur_min)
                        except Exception:
                            pass
                    if dur_max is not None:
                        try:
                            ok = ok and p_dur_i <= int(dur_max)
                        except Exception:
                            pass
                    score += 1.0 if ok else -0.5
                    reasons.append(f"Duration: {p_dur_i} weeks")

            if goal_req:
                if goal_req in p_goal:
                    score += 1.25
                    reasons.append(f"Goal matches: {p.get('primary_goal')}")
                else:
                    score -= 0.25

            if lvl_req:
                if lvl_req in p_lvl:
                    score += 1.0
                    reasons.append(f"Level matches: {p.get('intended_experience_level')}")
                else:
                    score -= 0.15

            inferred_volume = _infer_volume_bucket(p)
            if volume_req and volume_req != "any":
                if inferred_volume == volume_req:
                    score += 1.0
                    reasons.append(f"Volume looks {inferred_volume}")
                else:
                    score -= 0.25
                    reasons.append(f"Volume looks {inferred_volume}")

                if volume_req == "high":
                    proxy = _workload_proxy(p)
                    if proxy:
                        score += proxy / 300.0
                        reasons.append("Higher estimated workload")

            for kw in keywords:
                k = kw.strip().lower()
                if not k:
                    continue
                if k in haystack:
                    score += 0.25

            score += _workload_proxy(p) / 5000.0

            scored.append(_ScoredPlan(score=score, plan=p, reasons=reasons))

        scored.sort(key=lambda x: x.score, reverse=True)
        matches = []
        for item in scored[:top_k]:
            p = item.plan
            matches.append(
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "duration_weeks": p.get("duration_weeks"),
                    "intended_frequency_per_week": p.get("intended_frequency_per_week"),
                    "primary_goal": p.get("primary_goal"),
                    "intended_experience_level": p.get("intended_experience_level"),
                    "session_duration_target_min": p.get("session_duration_target_min"),
                    "volume_inferred": _infer_volume_bucket(p),
                    "score": round(item.score, 3),
                    "reasons": item.reasons,
                }
            )

        if not matches:
            return {
                "query": query,
                "matches": [],
                "message": (
                    "No matching plans found in the current list. "
                    "Try relaxing constraints or syncing plan metadata (frequency/duration/goal)."
                ),
            }

        return {
            "query": query,
            "matches": matches,
        }

    return ToolSpec(
        name="recommend_calendar_plans",
        description=(
            "Analyze training plans currently visible on the calendar plans screen and recommend the best matches "
            "based on the user's request (e.g. frequency per week, duration, goal, experience, volume preference)."
        ),
        parameters_schema={
            "type": "object",
            "required": ["user_request"],
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Natural-language request from the user, e.g. 'high volume plan, 4 days per week'.",
                },
                "top_k": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
            },
        },
        handler=handler,
    )
