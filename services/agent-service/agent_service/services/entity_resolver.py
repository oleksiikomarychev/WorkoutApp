from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import structlog

from ..config import settings


@dataclass
class InlineReference:
    """Lightweight representation of an inline entity reference in chat text.

    This parser is intentionally simple and side-effect free: it does not call
    other services, it only extracts *aliases* that the user wrote in a
    message. Higher-level code can then decide how to map these aliases to
    concrete IDs or filters.

    Supported patterns (for now):
    - /workout_6        -> kind="workout_order", index=6 (user-facing 1-based index)
    - /workout6         -> same as above
    - /plan_12          -> kind="calendar_plan", id=12
    - /applied_plan_5   -> kind="applied_plan", id=5
    - /applied_plan     -> kind="applied_plan", id=None (use context to resolve)
    - /Benchpress       -> kind="exercise_name", name="Benchpress" (no digits)
    """

    raw: str
    kind: str
    name: Optional[str] = None
    index: Optional[int] = None
    id: Optional[int] = None


_RE_WORKOUT = re.compile(r"/workout_?(?P<idx>\d+)")
_RE_PLAN = re.compile(r"/plan_?(?P<id>\d+)")
_RE_APPLIED_PLAN_WITH_ID = re.compile(r"/applied_plan_?(?P<id>\d+)")
_RE_APPLIED_PLAN_BARE = re.compile(r"/applied_plan(?![A-Za-z0-9_])")


def parse_inline_references(text: str) -> List[InlineReference]:
    """Extract inline references from arbitrary user text.

    This is best-effort and tolerant to malformed input. It never raises.
    """

    refs: List[InlineReference] = []
    if not text:
        return refs

    for m in _RE_WORKOUT.finditer(text):
        raw = m.group(0)
        idx_str = m.group("idx")
        try:
            idx = int(idx_str)
        except ValueError:
            continue
        refs.append(InlineReference(raw=raw, kind="workout_order", index=idx))

    for m in _RE_PLAN.finditer(text):
        raw = m.group(0)
        id_str = m.group("id")
        try:
            pid = int(id_str)
        except ValueError:
            continue
        refs.append(InlineReference(raw=raw, kind="calendar_plan", id=pid))

    for m in _RE_APPLIED_PLAN_WITH_ID.finditer(text):
        raw = m.group(0)
        id_str = m.group("id")
        try:
            aid = int(id_str)
        except ValueError:
            continue
        refs.append(InlineReference(raw=raw, kind="applied_plan", id=aid))

    for m in _RE_APPLIED_PLAN_BARE.finditer(text):
        raw = m.group(0)
        refs.append(InlineReference(raw=raw, kind="applied_plan", id=None))

    taken_spans = []
    for m in _RE_WORKOUT.finditer(text):
        taken_spans.append(m.span())
    for m in _RE_PLAN.finditer(text):
        taken_spans.append(m.span())
    for m in _RE_APPLIED_PLAN_WITH_ID.finditer(text):
        taken_spans.append(m.span())
    for m in _RE_APPLIED_PLAN_BARE.finditer(text):
        taken_spans.append(m.span())

    simple_name_pattern = re.compile(r"/(?P<name>[A-Za-z][A-Za-z0-9]*)")

    def _overlaps(start: int, end: int) -> bool:
        for s, e in taken_spans:
            if start < e and end > s:
                return True
        return False

    for m in simple_name_pattern.finditer(text):
        span = m.span()
        if _overlaps(*span):
            continue
        name = m.group("name")
        if name.lower() in {"workout", "plan", "applied", "applied_plan"}:
            continue
        refs.append(InlineReference(raw=m.group(0), kind="exercise_name", name=name))

    unique_refs: List[InlineReference] = []
    seen = set()
    for r in refs:
        key = (r.raw, r.kind, r.name, r.index, r.id)
        if key in seen:
            continue
        seen.add(key)
        unique_refs.append(r)

    return unique_refs


def build_inline_entities_snippet(
    refs: List[InlineReference],
    *,
    selection_date: Any = None,
    active_applied_plan_id: Any = None,
) -> str:
    """Build a short, LLM-oriented context snippet for inline references.

    This snippet is designed to be concatenated into a higher-level prompt,
    giving the model extra hints about how to interpret aliases like
    `/workout_6` or `/Benchpress`.
    """

    if not refs:
        return ""

    lines: List[str] = ["Inline entity references detected in user message:"]

    if active_applied_plan_id is not None:
        lines.append(f"- Active applied_plan_id (from context): {active_applied_plan_id}")
    if selection_date is not None:
        lines.append(f"- Current selection date (from context): {selection_date}")

    for r in refs:
        if r.kind == "workout_order":
            lines.append(
                f"- {r.raw}: workout in the ACTIVE applied plan with human order index {r.index} "
                "(LLM: map this to plan_order_indices or from/to_order_index filters)."
            )
        elif r.kind == "calendar_plan":
            lines.append(f"- {r.raw}: calendar training plan with id={r.id} (LLM: if tools require plan_id, use this).")
        elif r.kind == "applied_plan" and r.id is not None:
            lines.append(
                f"- {r.raw}: applied training plan with id={r.id} (LLM: you may prefer "
                "active_applied_plan_id from context if relevant)."
            )
        elif r.kind == "applied_plan" and r.id is None:
            lines.append(
                "- /applied_plan: refers to the ACTIVE applied plan for this user "
                "(LLM: use applied_plan_id from context)."
            )
        elif r.kind == "exercise_name" and r.name:
            lines.append(
                f"- {r.raw}: exercise name '{r.name}' (LLM: map this to "
                "exercise_definition_id using available exercises context if needed)."
            )

    return "\n".join(lines)


logger = structlog.get_logger(__name__)


@dataclass
class ResolvedReference:
    """Second-layer resolution of an InlineReference.

    For workouts in an applied plan we primarily care about plan_order_index.
    For exercises we want exercise_definition_id from exercises-service.
    """

    ref: InlineReference
    exercise_definition_id: Optional[int] = None
    calendar_plan_id: Optional[int] = None
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None  # zero-based for AppliedPlanExerciseFilter
    exercise_name: Optional[str] = None
    calendar_plan_name: Optional[str] = None
    errors: List[str] = field(default_factory=list)


async def _fetch_exercise_definitions_json() -> List[Dict[str, Any]]:
    base_url = settings.exercises_service_url
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            url = f"{base_url.rstrip('/')}/exercises/definitions/"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
    except Exception as exc:  # pragma: no cover - best-effort logging
        logger.warning("failed_to_fetch_exercise_definitions", error=str(exc))
    return []


async def _fetch_calendar_plan_name(plan_id: int) -> Optional[str]:
    base_url = settings.plans_service_url
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            url = f"{base_url.rstrip('/')}/plans/calendar-plans/{plan_id}"
            resp = await client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                name = data.get("name")
                if isinstance(name, str) and name:
                    return name
    except Exception as exc:  # pragma: no cover - best-effort logging
        logger.warning("failed_to_fetch_calendar_plan_name", plan_id=plan_id, error=str(exc))
    return None


async def resolve_inline_references_for_active_plan(
    refs: List[InlineReference],
    *,
    active_applied_plan_id: Optional[int] = None,
) -> List[ResolvedReference]:
    """Resolve inline references into ids and indices for an ACTIVE applied plan.

    - /workout_6  -> plan_order_index=5 (zero-based), tied to active_applied_plan_id
    - /Benchpress -> exercise_definition_id looked up in exercises-service
    - /plan_12    -> calendar_plan_id=12 (+ optional name from plans-service)
    - /applied_plan, /applied_plan_5 -> applied_plan_id
    """

    if not refs:
        return []

    resolved: List[ResolvedReference] = []

    needs_ex_defs = any(r.kind == "exercise_name" and r.name for r in refs)
    exercise_defs: List[Dict[str, Any]] = []
    if needs_ex_defs:
        exercise_defs = await _fetch_exercise_definitions_json()
    name_to_def: Dict[str, Dict[str, Any]] = {}
    for item in exercise_defs:
        name = item.get("name")
        if isinstance(name, str) and name:
            key = name.lower()
            if key not in name_to_def:
                name_to_def[key] = item

    calendar_plan_name_cache: Dict[int, Optional[str]] = {}

    for ref in refs:
        rr = ResolvedReference(ref=ref)

        if ref.kind == "workout_order" and ref.index is not None:
            # User-facing index is 1-based (/workout_6 -> 6-я тренировка).
            # AppliedPlanExerciseFilter.plan_order_indices is 0-based.
            idx = ref.index
            if idx > 0:
                rr.plan_order_index = idx - 1
            else:
                rr.plan_order_index = idx
            if active_applied_plan_id is not None:
                rr.applied_plan_id = active_applied_plan_id

        elif ref.kind == "exercise_name" and ref.name:
            key = ref.name.lower()
            item = name_to_def.get(key)
            if item is not None:
                ex_id = item.get("id")
                if isinstance(ex_id, int):
                    rr.exercise_definition_id = ex_id
                    name_val = item.get("name")
                    rr.exercise_name = name_val if isinstance(name_val, str) and name_val else ref.name
                else:
                    rr.exercise_name = ref.name
                    rr.errors.append("exercise_id_not_int")
            else:
                rr.exercise_name = ref.name
                rr.errors.append("exercise_not_found")

        elif ref.kind == "calendar_plan" and ref.id is not None:
            rr.calendar_plan_id = ref.id
            pid = ref.id
            if pid not in calendar_plan_name_cache:
                calendar_plan_name_cache[pid] = await _fetch_calendar_plan_name(pid)
            rr.calendar_plan_name = calendar_plan_name_cache[pid]

        elif ref.kind == "applied_plan":
            rr.applied_plan_id = ref.id or active_applied_plan_id

        resolved.append(rr)

    return resolved


async def build_resolved_inline_entities_snippet(
    refs: List[InlineReference],
    *,
    selection_date: Any = None,
    active_applied_plan_id: Any = None,
) -> str:
    """Async variant that resolves refs and builds a richer LLM context snippet."""

    resolved = await resolve_inline_references_for_active_plan(
        refs,
        active_applied_plan_id=active_applied_plan_id,
    )
    if not resolved:
        return ""

    lines: List[str] = ["Inline entity references detected in user message (resolved):"]

    if active_applied_plan_id is not None:
        lines.append(f"- Active applied_plan_id (from context): {active_applied_plan_id}")
    if selection_date is not None:
        lines.append(f"- Current selection date (from context): {selection_date}")

    for rr in resolved:
        r = rr.ref
        if r.kind == "workout_order" and rr.plan_order_index is not None:
            human_idx = r.index
            lines.append(
                f"- {r.raw}: workout in the ACTIVE applied plan; human index={human_idx}, "
                f"plan_order_index={rr.plan_order_index} (zero-based for filters)."
            )
        elif r.kind == "calendar_plan" and rr.calendar_plan_id is not None:
            if rr.calendar_plan_name:
                lines.append(
                    f"- {r.raw}: calendar training plan id={rr.calendar_plan_id}, name='{rr.calendar_plan_name}'."
                )
            else:
                lines.append(f"- {r.raw}: calendar training plan id={rr.calendar_plan_id}.")
        elif r.kind == "applied_plan" and rr.applied_plan_id is not None:
            lines.append(f"- {r.raw}: applied training plan id={rr.applied_plan_id}.")
        elif r.kind == "applied_plan" and rr.applied_plan_id is None:
            lines.append(
                "- /applied_plan: refers to the ACTIVE applied plan for this user "
                "(use applied_plan_id from context)."
            )
        elif r.kind == "exercise_name" and rr.exercise_name:
            if rr.exercise_definition_id is not None:
                lines.append(
                    f"- {r.raw}: exercise name '{rr.exercise_name}', "
                    f"exercise_definition_id={rr.exercise_definition_id}."
                )
            else:
                lines.append(
                    f"- {r.raw}: exercise name '{rr.exercise_name}' (definition not found in exercises-service)."
                )

    return "\n".join(lines)


async def build_applied_mass_edit_filter_hints(
    refs: List[InlineReference],
    *,
    active_applied_plan_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Produce ready-to-use filter hints for AppliedPlanMassEditCommand.

    Returns a dict that may contain:
    - plan_order_indices: List[int] (zero-based)
    - exercise_definition_ids: List[int]
    """

    resolved = await resolve_inline_references_for_active_plan(
        refs,
        active_applied_plan_id=active_applied_plan_id,
    )
    plan_order_indices: List[int] = []
    exercise_definition_ids: List[int] = []

    for rr in resolved:
        if rr.plan_order_index is not None:
            plan_order_indices.append(rr.plan_order_index)
        if rr.exercise_definition_id is not None:
            exercise_definition_ids.append(rr.exercise_definition_id)

    hints: Dict[str, Any] = {}
    if plan_order_indices:
        hints["plan_order_indices"] = sorted(set(plan_order_indices))
    if exercise_definition_ids:
        hints["exercise_definition_ids"] = sorted(set(exercise_definition_ids))

    return hints
