from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import count
from typing import Any

import structlog
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator, model_validator

from ..config import Settings
from ..prompts import (
    build_headers_prompt,
    build_outline_prompt,
    build_sets_prompt,
    build_summary_rationale_prompt,
)
from ..schemas.training_plans import (
    CalendarPlan,
    Mesocycle,
    Microcycle,
    PlanExercise,
    PlanSet,
    PlanWorkout,
    TrainingPlan,
)
from ..schemas.user_data import UserDataInput


def _parse_int_tolerant(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, str):
        s = value.strip().lower()

        m = re.search(r"(\d+)\s*[-–]\s*(\d+)", s)
        if m:
            a = int(m.group(1))
            b = int(m.group(2))
            try:
                return int(round((a + b) / 2))
            except Exception:
                return a

        m = re.search(r"(?:rpe)\s*(\d+)", s)
        if m:
            return int(m.group(1))

        m = re.search(r"(\d+)\s*%", s)
        if m:
            return int(m.group(1))

        m = re.search(r"(\d+)\s*(?:reps?|x)\b", s)
        if m:
            return int(m.group(1))

        m = re.search(r"\b(\d+)\b", s)
        if m:
            return int(m.group(1))

    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _load_rpe_table() -> dict[str, dict[str, int]]:
    logger = structlog.get_logger(__name__)
    base_url = (os.getenv("RPE_SERVICE_URL") or "http://rpe-service:8001").rstrip("/")
    url = f"{base_url}/rpe/table"
    try:
        try:
            import httpx
        except Exception as exc:  # pragma: no cover
            logger.warning("httpx not available for RPE HTTP load: %s", exc)
        else:
            headers = {"X-User-Id": os.getenv("RPE_TABLE_USER_ID", "system")}
            with httpx.Client(timeout=3.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                raw_data = resp.json()

            if not isinstance(raw_data, dict):
                logger.warning(
                    "RPE table URL %s returned non-dict payload of type %s",
                    url,
                    type(raw_data).__name__,
                )
            else:
                table_http: dict[str, dict[str, int]] = {}
                for intensity_key, mapping in raw_data.items():
                    if not isinstance(mapping, dict):
                        continue
                    normalized_intensity = (
                        str(int(round(intensity_key))) if isinstance(intensity_key, int | float) else str(intensity_key)
                    )
                    normalized_mapping: dict[str, int] = {}
                    for effort_key, reps_value in mapping.items():
                        if not isinstance(reps_value, int | float):
                            continue
                        normalized_effort = (
                            str(int(round(effort_key))) if isinstance(effort_key, int | float) else str(effort_key)
                        )
                        normalized_mapping[normalized_effort] = int(round(reps_value))
                    if normalized_mapping:
                        table_http[normalized_intensity] = normalized_mapping
                if table_http:
                    logger.info("Loaded RPE table from %s with %d intensity rows", url, len(table_http))
                    return table_http
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Failed to load RPE table from %s: %s", url, exc)

    logger.warning("RPE table not found; falling back to static guidance")
    return {}


def _format_rpe_summary(table: dict[str, dict[str, int]]) -> str:
    if not table:
        return ""
    lines: list[str] = []
    for intensity in sorted(table.keys(), key=lambda x: int(x), reverse=True):
        mapping = table[intensity]
        if not mapping:
            continue
        combos = ", ".join(
            f"RPE {effort} -> reps {mapping[effort]}"
            for effort in sorted(mapping.keys(), key=lambda x: int(x), reverse=True)
        )
        lines.append(f"{intensity}%: {combos}")
    return "\n".join(lines)


_RPE_TABLE: dict[str, dict[str, int]] | None = None
_RPE_TABLE_SUMMARY: str | None = None
_RPE_TABLE_JSON_TEXT: str | None = None


def get_rpe_table() -> dict[str, dict[str, int]]:
    global _RPE_TABLE, _RPE_TABLE_JSON_TEXT, _RPE_TABLE_SUMMARY
    if _RPE_TABLE is not None:
        return _RPE_TABLE
    table = _load_rpe_table()
    _RPE_TABLE = table
    _RPE_TABLE_JSON_TEXT = json.dumps(table, ensure_ascii=False, indent=2, sort_keys=True) if table else ""
    _RPE_TABLE_SUMMARY = _format_rpe_summary(table)
    return table


def get_rpe_summary() -> str:
    global _RPE_TABLE_SUMMARY
    if _RPE_TABLE_SUMMARY is None:
        get_rpe_table()
    return _RPE_TABLE_SUMMARY or ""


ALLOWED_VOLUME_KEYS = {
    "chest",
    "back",
    "legs",
    "arms",
    "shoulders",
    "core",
    "upper",
    "lower",
    "compound",
    "isolation",
}

try:
    _EXERCISES_CACHE_TTL_SECONDS = max(0, int(os.getenv("EXERCISES_CACHE_TTL_SECONDS", "1800")))
except (TypeError, ValueError):
    _EXERCISES_CACHE_TTL_SECONDS = 1800

_EXERCISES_CACHE: dict[str, Any] = {"data": None, "expires_at": 0.0}
_EXERCISES_CACHE_LOCK = asyncio.Lock()

_SETTINGS = Settings()
_GENAI_CLIENT: genai.Client | None = None
_GENAI_MODEL = _SETTINGS.staged_llm_model
_GENAI_MAX_ATTEMPTS = _SETTINGS.genai_max_attempts
_GENAI_BASE_DELAY = _SETTINGS.genai_base_delay
_GENAI_RATE_LIMIT_PER_MINUTE = _SETTINGS.genai_rate_limit_per_minute
_GENAI_RATE_LIMIT_WINDOW_SECONDS = _SETTINGS.genai_rate_limit_window_seconds
_GENAI_RATE_LIMIT_CONCURRENCY = _SETTINGS.genai_rate_limit_concurrency

_GENAI_RATE_LIMIT_SEMAPHORE = asyncio.Semaphore(_GENAI_RATE_LIMIT_CONCURRENCY)
_GENAI_RATE_LIMIT_LOCK = asyncio.Lock()
_GENAI_RATE_LIMIT_HISTORY: defaultdict[str, deque[float]] = defaultdict(deque)

logger = logging.getLogger(__name__)


class GenAIUnavailableError(RuntimeError):
    pass


def _is_quota_or_rate_limit_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status, int) and status in {403, 429}:
        return True

    text = str(exc).lower()
    patterns = (
        "quota",
        "rate limit",
        "too many requests",
        "resourceexhausted",
        "resource exhausted",
        "429",
    )
    return any(token in text for token in patterns)


async def _acquire_genai_rate_limit(model_name: str) -> None:
    if _GENAI_RATE_LIMIT_PER_MINUTE <= 0:
        return

    while True:
        async with _GENAI_RATE_LIMIT_LOCK:
            history = _GENAI_RATE_LIMIT_HISTORY[model_name]
            now = time.monotonic()
            window_start = now - _GENAI_RATE_LIMIT_WINDOW_SECONDS

            while history and history[0] < window_start:
                history.popleft()

            if len(history) < _GENAI_RATE_LIMIT_PER_MINUTE:
                history.append(now)
                return

            oldest = history[0]
            wait_seconds = _GENAI_RATE_LIMIT_WINDOW_SECONDS - (now - oldest)

        await asyncio.sleep(max(wait_seconds, 0.05))


def _get_genai_client() -> genai.Client:
    global _GENAI_CLIENT
    if _GENAI_CLIENT is None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) must be set for staged generation")
        _GENAI_CLIENT = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
    return _GENAI_CLIENT


async def _genai_generate_json(
    *,
    prompt: str,
    response_schema: dict[str, Any],
    temperature: float = 0.3,
    model: str | None = None,
    max_output_tokens: int = 100000,
) -> dict[str, Any]:
    client = _get_genai_client()
    chosen_model = model or _GENAI_MODEL

    try:
        async with _GENAI_RATE_LIMIT_SEMAPHORE:
            await _acquire_genai_rate_limit(chosen_model)
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=chosen_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
    except Exception as exc:
        logger.warning("GenAI request failed: %s", exc)
        if _is_quota_or_rate_limit_error(exc):
            raise GenAIUnavailableError("GenAI quota exhausted") from exc
        raise

    candidate = response.candidates[0] if getattr(response, "candidates", None) else None
    finish_reason = getattr(candidate, "finish_reason", None)
    safety_ratings = getattr(candidate, "safety_ratings", None)
    usage = getattr(response, "usage_metadata", None)
    logger.debug(
        "GenAI finish_reason=%s safety=%s usage=%s",
        finish_reason,
        safety_ratings,
        usage,
    )

    response_text = getattr(response, "text", None)
    if not response_text:
        raise ValueError("Empty GenAI JSON response text")

    truncated_preview = response_text[:5000]

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        logger.error(
            "GenAI JSON parse error: %s | preview=%s",
            exc,
            truncated_preview,
        )
        raise

    if not isinstance(parsed, dict):
        logger.error("GenAI JSON result is not dict | preview=%s", truncated_preview)
        raise ValueError("Non-dict GenAI JSON response")

    return parsed


def _format_available_exercises_preview(available_exercises: list[dict[str, Any]], *, limit: int = 30) -> str:
    lines: list[str] = []
    for raw in available_exercises[:limit]:
        ex_id = raw.get("id")
        name = raw.get("name", "")
        pattern = raw.get("movement_pattern") or raw.get("pattern") or "unknown"
        equipment = raw.get("equipment") or raw.get("category") or raw.get("type") or "unspecified"
        lines.append(f"{ex_id}: {name} | pattern={pattern} | equipment={equipment}")
    if len(available_exercises) > limit:
        lines.append(f"... (+{len(available_exercises) - limit} more)")
    return "\n".join(lines)


def _collect_workout_constraints(
    skeleton: StagedSkeleton,
) -> dict[int, tuple[int | None, int | None, int | None]]:
    micro_lookup = {mc.id: mc for mc in skeleton.microcycles}
    meso_lookup = {meso.id: meso for meso in skeleton.mesocycles}
    constraints: dict[int, tuple[int | None, int | None, int | None]] = {}

    for workout in skeleton.workouts:
        micro = micro_lookup.get(workout.microcycle_id)
        meso = meso_lookup.get(micro.mesocycle_id) if micro else None
        outline = skeleton.meso_outline_map.get(meso.id) if meso else None
        per_targets = outline.guidelines.per_workout_targets if outline and outline.guidelines else None

        desired_exercises: int | None = None
        min_sets: int | None = None
        max_sets: int | None = None

        if per_targets:
            if per_targets.number_of_exercises is not None:
                desired_parsed = _parse_int_tolerant(per_targets.number_of_exercises)
                desired_exercises = int(desired_parsed) if desired_parsed is not None else None

            if per_targets.set_range:
                range_values = list(per_targets.set_range)
                if len(range_values) >= 1:
                    min_parsed = _parse_int_tolerant(range_values[0])
                    min_sets = int(min_parsed) if min_parsed is not None else None
                if len(range_values) >= 2:
                    max_parsed = _parse_int_tolerant(range_values[1])
                    max_sets = int(max_parsed) if max_parsed is not None else None

        if min_sets is not None and max_sets is not None and min_sets > max_sets:
            min_sets, max_sets = max_sets, min_sets

        constraints[workout.id] = (desired_exercises, min_sets, max_sets)

    return constraints


def _apply_set_constraints(
    workouts: list[WorkoutSetsDraft],
    constraints: dict[int, tuple[int | None, int | None, int | None]],
) -> tuple[list[WorkoutSetsDraft], list[str]]:
    adjustments: list[str] = []
    adjusted_workouts: list[WorkoutSetsDraft] = []

    for workout in workouts:
        desired_exercises, min_sets, max_sets = constraints.get(workout.workout_id, (None, None, None))

        copy = workout.model_copy(deep=True)
        exercises = copy.exercises or []
        total_sets = sum(len(exercise.sets) for exercise in exercises)
        original_sets = total_sets
        changed = False

        if max_sets is not None and max_sets >= 0:
            while total_sets > max_sets:
                sortable = sorted(exercises, key=lambda ex: len(ex.sets), reverse=True)
                target = next((ex for ex in sortable if ex.sets), None)
                if not target:
                    break
                target.sets.pop()
                total_sets -= 1
                changed = True

        if min_sets is not None and min_sets > 0:
            while total_sets < min_sets:
                candidate = next((ex for ex in exercises if ex.sets), None)
                if not candidate:
                    break
                template = candidate.sets[-1]
                clone = PlanSetDraft(
                    order_index=(template.order_index or len(candidate.sets)) + 1,
                    intensity=template.intensity,
                    effort=template.effort,
                    volume=template.volume,
                )
                candidate.sets.append(clone)
                total_sets += 1
                changed = True

        if desired_exercises is not None and desired_exercises >= 0:
            if len(exercises) > desired_exercises:
                trimmed = exercises[desired_exercises:]
                if trimmed:
                    total_sets -= sum(len(ex.sets) for ex in trimmed)
                    del exercises[desired_exercises:]
                    changed = True
            elif len(exercises) < desired_exercises:
                adjustments.append(
                    f"Workout {copy.workout_id}: only {len(exercises)} exercises but target {desired_exercises}"
                )

        for ex in exercises:
            for idx, plan_set in enumerate(ex.sets, start=1):
                plan_set.order_index = idx

        if changed:
            adjustments.append(
                "Workout {}: sets adjusted from {} to {} (min={}, max={})".format(
                    copy.workout_id,
                    original_sets,
                    total_sets,
                    min_sets or "-",
                    max_sets or "-",
                )
            )

        adjusted_workouts.append(copy)

    return adjusted_workouts, adjustments


async def _generate_headers_staged(
    user_data: UserDataInput,
    skeleton: StagedSkeleton,
    available_exercises: list[dict[str, Any]],
) -> list[WorkoutHeaderDraft]:
    logger = logging.getLogger(__name__)

    if not _is_staged_headers_enabled():
        raise RuntimeError("LLM headers stage is disabled")

    allowed_map = _allowed_exercise_ids(available_exercises)
    if not allowed_map:
        raise RuntimeError("No allowed exercises available for headers stage")

    micro_lookup = {mc.id: mc for mc in skeleton.microcycles}
    meso_lookup = {meso.id: meso for meso in skeleton.mesocycles}

    preview = _format_available_exercises_preview(available_exercises, limit=40)
    schema = {
        "type": "object",
        "properties": {
            "workouts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "workout_id": {"type": "number"},
                        "exercises": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "exercise_definition_id": {"type": "number"},
                                    "exercise_name": {"type": "string"},
                                    "order_index": {"type": "number"},
                                },
                                "required": [
                                    "exercise_definition_id",
                                    "exercise_name",
                                    "order_index",
                                ],
                            },
                            "minItems": 1,
                        },
                    },
                    "required": ["workout_id", "exercises"],
                },
            }
        },
        "required": ["workouts"],
    }

    from collections import defaultdict as _dd

    workouts_by_micro: dict[int, list[PlanWorkout]] = _dd(list)
    for w in skeleton.workouts:
        workouts_by_micro[w.microcycle_id].append(w)

    workout_lookup = {w.id: w for w in skeleton.workouts}
    aggregated: list[WorkoutHeaderDraft] = []
    chunks = 0

    for micro in skeleton.microcycles:
        group = workouts_by_micro.get(micro.id, [])
        if not group:
            continue
        chunks += 1

        workout_lines: list[str] = []
        for workout in group:
            mc = micro_lookup.get(workout.microcycle_id)
            meso = meso_lookup.get(mc.mesocycle_id) if mc else None
            outline = skeleton.meso_outline_map.get(meso.id) if meso else None
            guideline_summary = ""
            if outline and outline.guidelines:
                try:
                    guideline_summary = json.dumps(
                        outline.guidelines.model_dump(exclude_none=True),
                        ensure_ascii=False,
                    )
                except (TypeError, ValueError):
                    guideline_summary = str(outline.guidelines)
            workout_lines.append(
                f"Workout {workout.id} ({workout.day_label}) | microcycle={mc.name if mc else '-'} "
                f"| mesocycle={meso.name if meso else '-'} | guidelines={guideline_summary}"
            )

        prompt = build_headers_prompt(
            user_data=user_data,
            workout_lines=workout_lines,
            preview=preview,
        )

        payload = await _genai_generate_json(
            prompt=prompt,
            response_schema=schema,
            temperature=0.4,
        )
        batch = WorkoutHeaderBatch.model_validate(payload)

        for item in batch.workouts:
            if not item.day_label:
                original = workout_lookup.get(item.workout_id)
                if not original:
                    raise ValueError(f"Unknown workout_id returned by LLM: {item.workout_id}")
                item.day_label = original.day_label
            aggregated.append(item)

    logger.info(
        "LLM headers generated (chunked): %d workouts across %d microcycles",
        len(aggregated),
        chunks,
    )
    return aggregated


async def _generate_sets_staged(
    user_data: UserDataInput,
    skeleton: StagedSkeleton,
    plan_exercises: list[PlanExercise],
    available_exercises: list[dict[str, Any]],
) -> list[WorkoutSetsDraft]:
    logger = logging.getLogger(__name__)

    if not _is_staged_headers_enabled():
        raise RuntimeError("LLM sets stage is disabled")

    if not plan_exercises:
        raise RuntimeError("No plan exercises available for sets stage")

    exercises_by_workout: dict[int, list[PlanExercise]] = defaultdict(list)
    for ex in plan_exercises:
        exercises_by_workout[ex.plan_workout_id].append(ex)

    try:
        debug_workout_map = {
            workout_id: [
                {
                    "exercise_definition_id": pe.exercise_definition_id,
                    "exercise_name": pe.exercise_name,
                    "order_index": pe.order_index,
                }
                for pe in sorted(ex_list, key=lambda e: e.order_index)
            ]
            for workout_id, ex_list in exercises_by_workout.items()
        }
        logger.info("SETS_STAGE_INPUT | workouts=%d", len(debug_workout_map))
        for wid, items in debug_workout_map.items():
            logger.debug(
                "SETS_STAGE_INPUT_WORKOUT | workout_id=%s exercises=%s",
                wid,
                items,
            )
    except Exception:
        logger.exception("Failed to log sets stage input map")

    schema = {
        "type": "object",
        "properties": {
            "workouts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "workout_id": {"type": "number"},
                        "exercises": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "exercise_definition_id": {"type": "number"},
                                    "sets": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "order_index": {"type": "number"},
                                                "intensity": {"type": "number"},
                                                "effort": {"type": "number"},
                                                "volume": {"type": "number"},
                                            },
                                            "required": ["order_index"],
                                        },
                                        "minItems": 1,
                                    },
                                },
                                "required": ["exercise_definition_id", "sets"],
                            },
                            "minItems": 1,
                        },
                    },
                    "required": ["workout_id", "exercises"],
                },
            }
        },
        "required": ["workouts"],
    }

    from collections import defaultdict as _dd

    workouts_by_micro: dict[int, list[PlanWorkout]] = _dd(list)
    for w in skeleton.workouts:
        workouts_by_micro[w.microcycle_id].append(w)

    aggregated_sets: list[WorkoutSetsDraft] = []
    chunks = 0
    for micro in skeleton.microcycles:
        group = [w for w in workouts_by_micro.get(micro.id, []) if exercises_by_workout.get(w.id)]
        if not group:
            continue
        chunks += 1

        workout_context: list[str] = []
        for workout in group:
            exercises = exercises_by_workout.get(workout.id, [])
            if not exercises:
                continue
            exercise_lines = ", ".join(f"{ex.exercise_name} (id={ex.exercise_definition_id})" for ex in exercises)
            workout_context.append(f"Workout {workout.id} {workout.day_label}: {exercise_lines}")

        prompt = build_sets_prompt(
            user_data=user_data,
            workout_context=workout_context,
            rpe_summary=get_rpe_summary(),
        )

        payload = await _genai_generate_json(
            prompt=prompt,
            response_schema=schema,
            temperature=0.35,
        )
        batch = WorkoutSetsBatch.model_validate(payload)

        try:
            for workout_sets in batch.workouts:
                per_ex_counts = {ex.exercise_definition_id: len(ex.sets or []) for ex in workout_sets.exercises or []}
                logger.info(
                    "SETS_STAGE_LLM_OUTPUT | workout_id=%s exercises=%s",
                    workout_sets.workout_id,
                    per_ex_counts,
                )
        except Exception:
            logger.exception("Failed to log LLM sets batch output")

        aggregated_sets.extend(batch.workouts)

    constraints = _collect_workout_constraints(skeleton)
    adjusted_workouts, adjustments = _apply_set_constraints(aggregated_sets, constraints)

    try:
        for workout_sets in adjusted_workouts:
            per_ex_counts = {ex.exercise_definition_id: len(ex.sets or []) for ex in workout_sets.exercises or []}
            logger.info(
                "SETS_STAGE_AFTER_CONSTRAINTS | workout_id=%s exercises=%s",
                workout_sets.workout_id,
                per_ex_counts,
            )
    except Exception:
        logger.exception("Failed to log adjusted workouts after constraints")
    if adjustments:
        for msg in adjustments:
            logger.info("Set constraint adjustment | %s", msg)
    logger.info(
        "LLM sets generated (chunked): %d workouts across %d microcycles (adjusted=%d)",
        len(adjusted_workouts),
        chunks,
        len(adjustments),
    )
    return adjusted_workouts


def _is_staged_headers_enabled() -> bool:
    return os.getenv("LLM_SPLIT_GENERATION", "").strip() == "1"


async def _get_available_exercises(settings: Settings) -> list[dict[str, Any]]:
    now = time.time()
    async with _EXERCISES_CACHE_LOCK:
        cached = _EXERCISES_CACHE.get("data")
        expires_at = _EXERCISES_CACHE.get("expires_at", 0.0)
        if cached is not None and expires_at > now:
            return cached  # type: ignore[return-value]

    url = f"{settings.exercises_service_url.rstrip('/')}/exercises/definitions"
    logger = logging.getLogger(__name__)

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error(
            "available_exercises_fetch_failed",
            url=url,
            error=str(exc),
        )
        raise RuntimeError("Failed to fetch available exercises") from exc

    if not isinstance(data, list):
        logger.error(
            "available_exercises_unexpected_payload",
            url=url,
            payload_type=type(data).__name__,
        )
        raise RuntimeError("Exercises service returned unexpected payload type")

    sanitized: list[dict[str, Any]] = [item for item in data if isinstance(item, dict)]

    async with _EXERCISES_CACHE_LOCK:
        _EXERCISES_CACHE["data"] = sanitized
        _EXERCISES_CACHE["expires_at"] = time.time() + _EXERCISES_CACHE_TTL_SECONDS

    logger.debug(
        "available_exercises_fetched",
        count=len(sanitized),
        ttl_seconds=_EXERCISES_CACHE_TTL_SECONDS,
    )
    return sanitized


class LLMPlanSet(BaseModel):
    order_index: int = Field(description="Sequential order starting from 1")
    intensity: int | None = None
    effort: int | None = None
    volume: int | None = None

    @field_validator("intensity", "effort", "volume", mode="before")
    @classmethod
    def _parse_numbers_tolerant(cls, v, info):
        field_name = info.field_name
        parsed = _parse_int_tolerant(v)
        logger.debug(
            "LLMPlanSet field parsing | field=%s raw_value=%s parsed_value=%s raw_type=%s",
            field_name,
            repr(v),
            repr(parsed),
            type(v).__name__,
        )
        return parsed

    @model_validator(mode="after")
    def _validate_and_clamp(self):
        logger.debug(
            "LLMPlanSet validation | order_index=%d intensity=%s effort=%s volume=%s",
            self.order_index,
            repr(self.intensity),
            repr(self.effort),
            repr(self.volume),
        )

        if self.intensity is not None:
            self.intensity = max(0, min(100, int(self.intensity)))
        if self.effort is not None:
            self.effort = max(1, min(10, int(self.effort)))
        if self.volume is not None:
            self.volume = max(1, int(self.volume))

        present = sum(1 for v in (self.intensity, self.effort, self.volume) if v is not None)
        if present < 2:
            logger.error(
                "LLMPlanSet VALIDATION FAILED | order_index=%d intensity=%s effort=%s volume=%s present=%d",
                self.order_index,
                repr(self.intensity),
                repr(self.effort),
                repr(self.volume),
                present,
            )
            raise ValueError("At least two of intensity/effort/volume must be provided")
        return self


class LLMPlanExercise(BaseModel):
    exercise_definition_id: int = Field(description="ID from the allowed exercises list")
    exercise_name: str = Field(description="Exact name from the allowed exercises list")
    order_index: int = Field(description="Sequential order starting from 1")
    sets: list[LLMPlanSet] = Field(description="List of sets for this exercise")


class LLMPlanWorkout(BaseModel):
    day_label: str = Field(description="Day label like 'Monday', 'Day 1', etc.")
    order_index: int = Field(description="Sequential order starting from 1")
    exercises: list[LLMPlanExercise] = Field(description="List of exercises in this workout")


class LLMMicrocycle(BaseModel):
    name: str = Field(description="Microcycle name")
    order_index: int = Field(description="Sequential order starting from 1")
    days_count: int = Field(description="Number of days in this microcycle")
    plan_workouts: list[LLMPlanWorkout] = Field(description="List of workouts in this microcycle")


class LLMMesocycle(BaseModel):
    name: str = Field(description="Mesocycle name")
    order_index: int = Field(description="Sequential order starting from 1")
    weeks_count: int = Field(description="Number of weeks in this mesocycle")
    microcycles: list[LLMMicrocycle] = Field(description="List of microcycles in this mesocycle")


class LLMCalendarPlan(BaseModel):
    name: str = Field(description="Training plan name")
    duration_weeks: int = Field(description="Total duration in weeks")


class LLMTrainingPlanResponse(BaseModel):
    calendar_plan: LLMCalendarPlan
    mesocycles: list[LLMMesocycle]

    plan_rationale: LLMPlanRationale | None = None

    plan_summary: str | None = None


class LLMPlanRationale(BaseModel):
    goals_interpretation: str | None = Field(default=None, description="Как цели пользователя интерпретированы")
    periodization: str | None = Field(
        default=None,
        description="Почему выбрана такая периодизация и длительность мезо/микроциклов",
    )
    frequency: str | None = Field(
        default=None,
        description="Почему выбрана такая частота тренировок и распределение по неделям",
    )
    exercise_selection: str | None = Field(
        default=None,
        description="Логика выбора упражнений: баланс тяга/жим/ноги/кор, вариативность",
    )
    set_parameters: str | None = Field(default=None, description="Интенсивность/повторения/RPE и соответствие целям")
    constraints_equipment: str | None = Field(
        default=None, description="Как учтены ограничения и доступное оборудование"
    )
    progression: str | None = Field(
        default=None,
        description="Как планируется прогрессия и адаптация при нехватке времени/усталости",
    )


LLMTrainingPlanResponse.model_rebuild()


class OutlineMicrocycle(BaseModel):
    name: str | None = Field(default=None, description="Microcycle name")
    days_count: int | None = Field(default=None, description="Number of days in this microcycle")
    workouts_per_microcycle: int | None = Field(
        default=None,
        description="Number of workouts to schedule inside this microcycle",
    )
    order_index: int | None = Field(default=None, description="1-based microcycle order inside the mesocycle")
    day_labels: list[str] | None = Field(
        default=None,
        description="Optional list of day labels for workouts (e.g., ['Пн', 'Ср', 'Пт'])",
    )
    focus: str | None = Field(default=None, description="Optional focus/theme for the microcycle")


class OutlinePerWorkoutTargets(BaseModel):
    number_of_exercises: int | None = None
    set_range: list[int] | None = None


class OutlineGuidelines(BaseModel):
    weekly_volume_targets: dict[str, Any] | None = None
    intensity_bands: dict[str, Any] | None = None
    per_workout_targets: OutlinePerWorkoutTargets | None = None
    focus_areas: list[str] | None = None
    exercise_categories_allowed: list[str] | None = None


class OutlineMesocycle(BaseModel):
    name: str = Field(description="Mesocycle name")
    weeks_count: int = Field(description="Number of weeks in this mesocycle")
    microcycles: list[OutlineMicrocycle] | None = Field(
        default=None,
        description="Explicit list of microcycles (one per week). If omitted, fallback to template",
    )
    microcycle_template: OutlineMicrocycle | None = Field(
        default=None,
        description="Legacy microcycle template repeated to fill missing weeks",
    )
    guidelines: OutlineGuidelines = Field(description="Dynamic guidelines for this mesocycle (mandatory)")

    @model_validator(mode="after")
    def _ensure_microcycle_order(self) -> OutlineMesocycle:
        default_template = self.microcycle_template
        if not self.microcycles and default_template is None:
            default_template = OutlineMicrocycle(
                name=f"{self.name} - Week",
                days_count=7,
                workouts_per_microcycle=3,
            )
            self.microcycle_template = default_template

        if self.microcycles:
            normalized: list[OutlineMicrocycle] = []
            for idx, micro in enumerate(self.microcycles, start=1):
                defaults: dict[str, Any] = {}
                if micro.order_index is None:
                    defaults["order_index"] = idx
                if not micro.name:
                    defaults["name"] = f"Week {idx}"
                if micro.days_count is None and default_template and default_template.days_count is not None:
                    defaults["days_count"] = default_template.days_count
                if (
                    micro.workouts_per_microcycle is None
                    and default_template
                    and default_template.workouts_per_microcycle is not None
                ):
                    defaults["workouts_per_microcycle"] = default_template.workouts_per_microcycle
                if defaults:
                    micro = micro.model_copy(update=defaults)
                normalized.append(micro)
            self.microcycles = normalized
        return self


class OutlineSpec(BaseModel):
    name: str = Field(description="Outline name (plan name)")
    duration_weeks: int | None = Field(
        default=None, description="Total duration in weeks (optional; if omitted, infer later)"
    )
    mesocycles: list[OutlineMesocycle] = Field(description="List of mesocycles with weeks_count and microcycle data")

    def total_weeks(self) -> int:
        weeks = sum(m.weeks_count for m in self.mesocycles)
        if weeks <= 0:
            raise ValueError("Outline must contain at least one week across mesocycles")
        return weeks


def _meso_micro_schedule(meso_outline: OutlineMesocycle) -> list[OutlineMicrocycle]:
    default_template = meso_outline.microcycle_template
    if default_template is None:
        default_template = OutlineMicrocycle(
            name=f"{meso_outline.name} - Week",
            days_count=7,
            workouts_per_microcycle=3,
        )

    if meso_outline.microcycles:
        micro_list = [micro.model_copy() for micro in meso_outline.microcycles]
        if len(micro_list) < meso_outline.weeks_count:
            for idx in range(len(micro_list) + 1, meso_outline.weeks_count + 1):
                micro_list.append(
                    default_template.model_copy(
                        update={
                            "order_index": idx,
                            "name": f"Week {idx}",
                        }
                    )
                )
        elif len(micro_list) > meso_outline.weeks_count:
            micro_list = micro_list[: meso_outline.weeks_count]

        normalized: list[OutlineMicrocycle] = []
        for idx, micro in enumerate(micro_list, start=1):
            updates: dict[str, Any] = {}
            if micro.order_index is None:
                updates["order_index"] = idx
            if not micro.name:
                updates["name"] = f"Week {idx}"
            if micro.days_count is None and default_template.days_count is not None:
                updates["days_count"] = default_template.days_count
            if micro.workouts_per_microcycle is None and default_template.workouts_per_microcycle is not None:
                updates["workouts_per_microcycle"] = default_template.workouts_per_microcycle
            if not micro.day_labels and default_template.day_labels:
                updates["day_labels"] = list(default_template.day_labels)
            if updates:
                micro = micro.model_copy(update=updates)
            normalized.append(micro)
        return normalized

    materialized: list[OutlineMicrocycle] = []
    for idx in range(1, meso_outline.weeks_count + 1):
        defaults = {
            "order_index": idx,
            "name": default_template.name or f"Week {idx}",
            "days_count": default_template.days_count,
            "workouts_per_microcycle": default_template.workouts_per_microcycle,
            "day_labels": default_template.day_labels,
        }
        materialized.append(default_template.model_copy(update={k: v for k, v in defaults.items() if v is not None}))
    return materialized


class WorkoutHeaderExerciseDraft(BaseModel):
    exercise_definition_id: int
    exercise_name: str
    order_index: int


class WorkoutHeaderDraft(BaseModel):
    workout_id: int
    day_label: str | None = None
    exercises: list[WorkoutHeaderExerciseDraft]


class WorkoutHeaderBatch(BaseModel):
    workouts: list[WorkoutHeaderDraft]


class PlanSetDraft(BaseModel):
    order_index: int
    intensity: int | None = Field(default=None, ge=0, le=100)
    effort: int | None = Field(default=None, ge=1, le=10)
    volume: int | None = Field(default=None, ge=1)

    @field_validator("intensity", "effort", "volume", mode="before")
    @classmethod
    def _coerce_numbers(cls, value):
        parsed = _parse_int_tolerant(value)
        return parsed if parsed is not None else value


class WorkoutSetExerciseDraft(BaseModel):
    exercise_definition_id: int
    sets: list[PlanSetDraft]


class WorkoutSetsDraft(BaseModel):
    workout_id: int
    exercises: list[WorkoutSetExerciseDraft]


class WorkoutSetsBatch(BaseModel):
    workouts: list[WorkoutSetsDraft]


@dataclass
class StagedSkeleton:
    id_gen: count
    calendar_plan: CalendarPlan
    mesocycles: list[Mesocycle]
    microcycles: list[Microcycle]
    workouts: list[PlanWorkout]
    meso_outline_map: dict[int, OutlineMesocycle]


def _find_mesocycle_for_microcycle(mesocycles: list[Mesocycle], microcycle: Microcycle) -> Mesocycle | None:
    for meso in mesocycles:
        if meso.id == microcycle.mesocycle_id:
            return meso
    return None


def _allowed_exercise_ids(available_exercises: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for raw in available_exercises:
        try:
            ex_id = int(raw["id"])
        except (KeyError, TypeError, ValueError):
            continue
        mapping[ex_id] = raw
    return mapping


def _validate_header_exercises(
    exercises: list[WorkoutHeaderExerciseDraft],
    allowed_map: dict[int, dict[str, Any]],
) -> None:
    for ex in exercises:
        if ex.exercise_definition_id not in allowed_map:
            raise ValueError(f"exercise_definition_id {ex.exercise_definition_id} is not allowed")


def _build_staged_skeleton(outline: OutlineSpec) -> StagedSkeleton:
    id_gen = count(1)
    duration = outline.duration_weeks or outline.total_weeks()

    calendar_plan = CalendarPlan(
        id=next(id_gen),
        name=outline.name,
        duration_weeks=duration,
    )

    mesocycles: list[Mesocycle] = []
    microcycles: list[Microcycle] = []
    workouts: list[PlanWorkout] = []
    meso_outline_map: dict[int, OutlineMesocycle] = {}

    for meso_idx, meso_outline in enumerate(outline.mesocycles, start=1):
        meso_id = next(id_gen)
        meso = Mesocycle(
            id=meso_id,
            calendar_plan_id=calendar_plan.id,
            name=meso_outline.name,
            order_index=meso_idx,
            weeks_count=meso_outline.weeks_count,
        )
        mesocycles.append(meso)
        meso_outline_map[meso_id] = meso_outline

        micro_outline_list = _meso_micro_schedule(meso_outline)
        default_template = meso_outline.microcycle_template

        for local_idx, micro_outline in enumerate(micro_outline_list, start=1):
            order_index = micro_outline.order_index or local_idx
            days_count = micro_outline.days_count
            if days_count is None and default_template and default_template.days_count is not None:
                days_count = default_template.days_count
            if days_count is None:
                days_count = 7

            micro_id = next(id_gen)
            micro = Microcycle(
                id=micro_id,
                mesocycle_id=meso_id,
                name=micro_outline.name or f"{meso_outline.name} - Week {order_index}",
                order_index=order_index,
                days_count=days_count,
            )
            microcycles.append(micro)

            workouts_target: int | None = None
            if micro_outline.day_labels:
                workouts_target = len(micro_outline.day_labels)
            elif micro_outline.workouts_per_microcycle is not None:
                workouts_target = micro_outline.workouts_per_microcycle
            elif default_template and default_template.workouts_per_microcycle is not None:
                workouts_target = default_template.workouts_per_microcycle
            else:
                workouts_target = 3

            day_labels = list(micro_outline.day_labels or [])
            if not day_labels and default_template:
                if default_template.day_labels:
                    day_labels = list(default_template.day_labels)
                elif default_template.workouts_per_microcycle:
                    day_labels = [f"Day {i}" for i in range(1, default_template.workouts_per_microcycle + 1)]

            if workouts_target and workouts_target > 0:
                if not day_labels:
                    day_labels = [f"Day {i}" for i in range(1, workouts_target + 1)]
                elif len(day_labels) < workouts_target:
                    day_labels.extend(f"Day {i}" for i in range(len(day_labels) + 1, workouts_target + 1))
                elif len(day_labels) > workouts_target:
                    day_labels = day_labels[:workouts_target]

            for day in range(1, (workouts_target or 0) + 1):
                workout_id = next(id_gen)
                label = day_labels[day - 1] if day_labels and day - 1 < len(day_labels) else f"Day {day}"
                workout = PlanWorkout(
                    id=workout_id,
                    microcycle_id=micro_id,
                    day_label=label,
                    order_index=day,
                )
                workouts.append(workout)

    return StagedSkeleton(
        id_gen=id_gen,
        calendar_plan=calendar_plan,
        mesocycles=mesocycles,
        microcycles=microcycles,
        workouts=workouts,
        meso_outline_map=meso_outline_map,
    )


def _map_headers_into_plan(
    skeleton: StagedSkeleton,
    headers: list[WorkoutHeaderDraft],
) -> list[PlanExercise]:
    workout_ids = {w.id for w in skeleton.workouts}
    exercises: list[PlanExercise] = []
    for header in headers:
        if header.workout_id not in workout_ids:
            raise ValueError(f"Unknown workout_id {header.workout_id} in header output")
        for idx, draft in enumerate(header.exercises, start=1):
            plan_ex = PlanExercise(
                id=next(skeleton.id_gen),
                plan_workout_id=header.workout_id,
                exercise_definition_id=draft.exercise_definition_id,
                exercise_name=draft.exercise_name,
                order_index=draft.order_index or idx,
            )
            exercises.append(plan_ex)
    return exercises


def _map_sets_into_plan(
    skeleton: StagedSkeleton,
    plan_exercises: list[PlanExercise],
    sets_batch: list[WorkoutSetsDraft],
) -> list[PlanSet]:
    lookup: dict[tuple[int, int], PlanExercise] = {}
    for ex in plan_exercises:
        lookup[(ex.plan_workout_id, ex.exercise_definition_id)] = ex

    plan_sets: list[PlanSet] = []
    for workout_sets in sets_batch:
        for exercise_sets in workout_sets.exercises:
            key = (workout_sets.workout_id, exercise_sets.exercise_definition_id)
            if key not in lookup:
                raise ValueError(
                    f"Workout {workout_sets.workout_id} returned sets for unknown "
                    f"exercise_definition_id {exercise_sets.exercise_definition_id}"
                )
            plan_exercise = lookup[key]
            for idx, set_draft in enumerate(exercise_sets.sets, start=1):
                plan_set = PlanSet(
                    id=next(skeleton.id_gen),
                    plan_exercise_id=plan_exercise.id,
                    order_index=set_draft.order_index or idx,
                    intensity=set_draft.intensity,
                    effort=set_draft.effort,
                    volume=set_draft.volume,
                )
                plan_sets.append(plan_set)
    return plan_sets


@dataclass
class StagedDiagnostics:
    volume_by_pattern_per_micro: dict[int, dict[str, int]]
    per_workout_stats: dict[int, dict[str, int]]
    violations: list[str]
    auto_fixes: list[str]
    raw_llm: dict[str, Any] | None = None
    plan_summary: str | None = None
    plan_rationale: LLMPlanRationale | None = None


def _compute_plan_metrics(
    plan: TrainingPlan,
    allowed_map: dict[int, dict[str, Any]],
) -> tuple[dict[int, dict[str, int]], dict[int, dict[str, int]]]:
    volume_by_micro: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_workout_stats: dict[int, dict[str, int]] = {}

    exercises_by_workout: dict[int, list[PlanExercise]] = defaultdict(list)
    for ex in plan.exercises:
        exercises_by_workout[ex.plan_workout_id].append(ex)

    sets_by_exercise: dict[int, list[PlanSet]] = defaultdict(list)
    for plan_set in plan.sets:
        sets_by_exercise[plan_set.plan_exercise_id].append(plan_set)

    for workout in plan.workouts:
        exercises = exercises_by_workout.get(workout.id, [])
        total_sets = 0
        for ex in exercises:
            sets_for_exercise = sets_by_exercise.get(ex.id, [])
            total_sets += len(sets_for_exercise)

            raw_ex = allowed_map.get(ex.exercise_definition_id, {})
            pattern_raw = raw_ex.get("movement_type") or raw_ex.get("muscle_group") or raw_ex.get("region")
            pattern = str(pattern_raw) if pattern_raw else "unknown"

            if sets_for_exercise:
                for plan_set in sets_for_exercise:
                    parsed_volume = plan_set.volume if plan_set.volume is not None else 1
                    volume_by_micro[workout.microcycle_id][pattern] += int(parsed_volume)
            else:
                volume_by_micro[workout.microcycle_id][pattern] += 1

        per_workout_stats[workout.id] = {
            "exercises": len(exercises),
            "sets": total_sets,
        }

    materialized_volume = {micro_id: dict(patterns) for micro_id, patterns in volume_by_micro.items()}
    return materialized_volume, per_workout_stats


def _validate_against_guidelines(
    skeleton: StagedSkeleton,
    plan: TrainingPlan,
    volume_by_micro: dict[int, dict[str, int]],
    per_workout_stats: dict[int, dict[str, int]],
) -> tuple[list[str], dict[int, int]]:
    violations: list[str] = []
    adjustments_dict: dict[int, int] = {}
    workouts_by_micro: dict[int, list[PlanWorkout]] = defaultdict(list)
    for workout in skeleton.workouts:
        workouts_by_micro[workout.microcycle_id].append(workout)

    for meso in skeleton.mesocycles:
        outline = skeleton.meso_outline_map.get(meso.id)
        if not outline or not outline.guidelines:
            continue

        guidelines = outline.guidelines or {}
        weekly_targets = guidelines.weekly_volume_targets or {}
        if weekly_targets:
            for micro in skeleton.microcycles:
                if micro.mesocycle_id != meso.id:
                    continue
                micro_stats = volume_by_micro.get(micro.id, {})
                for pattern, target in weekly_targets.items():
                    target_value = _parse_int_tolerant(target)
                    if not target_value:
                        continue
                    actual = micro_stats.get(pattern, 0)
                    if actual < target_value:
                        diff = target_value - actual
                        violations.append(f"Microcycle '{micro.name}' pattern '{pattern}' short by {diff} units")

        per_workout_targets = guidelines.per_workout_targets
        if per_workout_targets:
            desired_ex = per_workout_targets.number_of_exercises
            min_sets: int | None = None
            max_sets: int | None = None
            if per_workout_targets.set_range and len(per_workout_targets.set_range) == 2:
                min_sets = _parse_int_tolerant(per_workout_targets.set_range[0])
                max_sets = _parse_int_tolerant(per_workout_targets.set_range[1])

            for micro in skeleton.microcycles:
                if micro.mesocycle_id != meso.id:
                    continue
                for workout in workouts_by_micro.get(micro.id, []):
                    stats = per_workout_stats.get(workout.id, {"exercises": 0, "sets": 0})
                    if desired_ex is not None and stats["exercises"] < desired_ex:
                        diff = desired_ex - stats["exercises"]
                        violations.append(
                            f"Workout '{workout.day_label}' in microcycle '{micro.name}' lacks {diff} exercises"
                        )
                    if min_sets is not None and stats["sets"] < min_sets:
                        diff = min_sets - stats["sets"]
                        violations.append(
                            f"Workout '{workout.day_label}' in microcycle '{micro.name}' short by {diff} sets"
                        )

                        if diff == 1:
                            adjustments_dict[workout.id] = 1
                    if max_sets is not None and stats["sets"] > max_sets:
                        diff = stats["sets"] - max_sets
                        violations.append(
                            f"Workout '{workout.day_label}' in microcycle '{micro.name}' "
                            f"exceeds guideline by {diff} sets"
                        )

                        if diff == 1:
                            adjustments_dict[workout.id] = -1

    violations_deduped = list(dict.fromkeys(violations))
    return violations_deduped, adjustments_dict


def _apply_minor_adjustments(
    plan: TrainingPlan,
    adjustments: dict[int, int],
) -> tuple[TrainingPlan, list[str]]:
    if not adjustments:
        return plan, []

    exercises_by_workout: dict[int, list[PlanExercise]] = defaultdict(list)
    for plan_ex in plan.exercises:
        exercises_by_workout[plan_ex.plan_workout_id].append(plan_ex)

    sets_by_exercise: dict[int, list[PlanSet]] = defaultdict(list)
    for plan_set in plan.sets:
        sets_by_exercise[plan_set.plan_exercise_id].append(plan_set)

    new_sets = list(plan.sets)
    fix_logs: list[str] = []

    next_set_id = (max((s.id for s in plan.sets), default=0) or 0) + 1

    for workout_id, delta in adjustments.items():
        if not delta:
            continue
        exercises = exercises_by_workout.get(workout_id)
        if not exercises:
            continue

        target_ex = max(exercises, key=lambda ex: len(sets_by_exercise.get(ex.id, [])) or 0)
        target_sets = sets_by_exercise.setdefault(target_ex.id, [])

        if delta > 0:
            if not target_sets:
                continue
            template = target_sets[-1]
            for _ in range(delta):
                clone = PlanSet(
                    id=next_set_id,
                    plan_exercise_id=target_ex.id,
                    order_index=(target_sets[-1].order_index + 1) if target_sets else 1,
                    intensity=template.intensity,
                    effort=template.effort,
                    volume=template.volume,
                )
                next_set_id += 1
                target_sets.append(clone)
                new_sets.append(clone)
                fix_logs.append(f"Workout {workout_id}: added set to exercise {target_ex.exercise_definition_id}")
        else:
            remove_count = min(abs(delta), len(target_sets))
            for _ in range(remove_count):
                removed = target_sets.pop()
                new_sets = [s for s in new_sets if s.id != removed.id]
                fix_logs.append(f"Workout {workout_id}: removed set from exercise {target_ex.exercise_definition_id}")

    updated_plan = plan.model_copy(update={"sets": new_sets})
    return updated_plan, fix_logs


async def _generate_summary_and_rationale_staged(
    user_data: UserDataInput,
    plan: TrainingPlan,
    skeleton: StagedSkeleton,
    diagnostics: StagedDiagnostics,
    available_exercises: list[dict[str, Any]],
) -> tuple[str | None, LLMPlanRationale | None]:
    logger = logging.getLogger(__name__)
    try:
        plan_context = _prepare_plan_context_for_summary(
            user_data=user_data,
            plan=plan,
            skeleton=skeleton,
            diagnostics=diagnostics,
            available_exercises=available_exercises,
        )
        prompt = build_summary_rationale_prompt(
            user_data=user_data,
            plan_context=plan_context,
        )
        schema = {
            "type": "object",
            "properties": {
                "plan_summary": {"type": "string"},
                "plan_rationale": {
                    "type": "object",
                    "properties": {
                        "goals_interpretation": {"type": "string"},
                        "periodization": {"type": "string"},
                        "frequency": {"type": "string"},
                        "exercise_selection": {"type": "string"},
                        "set_parameters": {"type": "string"},
                        "constraints_equipment": {"type": "string"},
                        "progression": {"type": "string"},
                    },
                    "required": [],
                },
            },
            "required": ["plan_summary", "plan_rationale"],
        }
        parsed = await _genai_generate_json(prompt=prompt, response_schema=schema, temperature=0.3)
        summary = parsed.get("plan_summary")
        rationale_dict = parsed.get("plan_rationale") or {}
        rationale = LLMPlanRationale(
            **{
                k: (rationale_dict.get(k) or None)
                for k in [
                    "goals_interpretation",
                    "periodization",
                    "frequency",
                    "exercise_selection",
                    "set_parameters",
                    "constraints_equipment",
                    "progression",
                ]
            }
        )
        return summary, rationale
    except Exception as exc:
        logger.warning("Summary/Rationale LLM failed: %s", exc)
        return None, None


async def _generate_staged_plan(
    user_data: UserDataInput,
    available_exercises: list[dict[str, Any]],
) -> tuple[TrainingPlan, StagedDiagnostics]:
    logger = logging.getLogger(__name__)
    logger.info("Starting staged plan generation")

    outline = await _generate_outline_staged(user_data, available_exercises)
    logger.info(f"Outline generated: {outline.name}, {len(outline.mesocycles)} mesocycles")

    skeleton = _build_staged_skeleton(outline)
    logger.info(
        f"Skeleton built: {len(skeleton.workouts)} workouts, "
        f"{len(skeleton.microcycles)} microcycles, {len(skeleton.mesocycles)} mesocycles"
    )

    headers = await _generate_headers_staged(user_data, skeleton, available_exercises)
    logger.info(f"Headers generated: {len(headers)} workout headers")

    plan_exercises = _map_headers_into_plan(skeleton, headers)

    sets_batch = await _generate_sets_staged(user_data, skeleton, plan_exercises, available_exercises)
    logger.info(f"Sets generated: {len(sets_batch)} workout sets")

    plan_sets = _map_sets_into_plan(skeleton, plan_exercises, sets_batch)

    plan = TrainingPlan(
        calendar_plan=skeleton.calendar_plan,
        mesocycles=skeleton.mesocycles,
        microcycles=skeleton.microcycles,
        workouts=skeleton.workouts,
        exercises=plan_exercises,
        sets=plan_sets,
    )

    allowed_map = _allowed_exercise_ids(available_exercises)
    auto_fix_logs: list[str] = []

    vol_by_micro, per_workout_stats = _compute_plan_metrics(plan, allowed_map)
    violations, minor_adjust = _validate_against_guidelines(skeleton, plan, vol_by_micro, per_workout_stats)

    if minor_adjust:
        plan, fix_logs = _apply_minor_adjustments(plan, minor_adjust)
        auto_fix_logs.extend(fix_logs)
        auto_fix_logs = list(dict.fromkeys(auto_fix_logs))
        vol_by_micro, per_workout_stats = _compute_plan_metrics(plan, allowed_map)
        post_violations, _ = _validate_against_guidelines(skeleton, plan, vol_by_micro, per_workout_stats)
        violations = list(dict.fromkeys(post_violations))

    if violations:
        raise ValueError("Staged reconciliation failed: " + "; ".join(violations))

    diagnostics = StagedDiagnostics(
        volume_by_pattern_per_micro=vol_by_micro,
        per_workout_stats=per_workout_stats,
        violations=violations,
        auto_fixes=auto_fix_logs,
        raw_llm=None,
    )

    summary, rationale = await _generate_summary_and_rationale_staged(
        user_data=user_data,
        plan=plan,
        skeleton=skeleton,
        diagnostics=diagnostics,
        available_exercises=available_exercises,
    )

    diagnostics.plan_summary = summary
    diagnostics.plan_rationale = rationale

    logger.info(
        "Staged plan generation complete | violations=%d auto_fixes=%d summary=%s rationale=%s",
        len(violations),
        len(auto_fix_logs),
        "present" if summary else "missing",
        "present" if rationale else "missing",
    )

    return plan, diagnostics


class _MicrocycleRaw(BaseModel):
    name: str | None = None
    days_count: int | None = None
    workouts_per_microcycle: int | None = None
    order_index: int | None = None
    day_labels: list[str] | None = None
    focus: str | None = None

    @field_validator("days_count", "workouts_per_microcycle", "order_index", mode="before")
    @classmethod
    def coerce_int(cls, v):
        return _parse_int_tolerant(v)

    @field_validator("day_labels", mode="before")
    @classmethod
    def coerce_labels(cls, v):
        if not isinstance(v, list):
            return None
        cleaned = [str(lab).strip() for lab in v if lab not in (None, "")]
        return cleaned or None

    @field_validator("name", "focus", mode="before")
    @classmethod
    def coerce_str(cls, v):
        if v in (None, ""):
            return None
        return str(v).strip() or None


def _normalize_microcycle(raw: dict[str, Any], order_idx: int) -> dict[str, Any]:
    parsed = _MicrocycleRaw.model_validate(raw)
    result = parsed.model_dump()
    if result.get("order_index") is None:
        result["order_index"] = order_idx
    return result


def _sanitize_outline_payload(payload: dict[str, Any]) -> dict[str, Any]:
    def _kv_pairs_to_dict(arr: Any, value_parser=None) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if isinstance(arr, list):
            for item in arr:
                if not isinstance(item, dict):
                    continue
                key = item.get("key")
                if key is None:
                    continue
                try:
                    key_str = str(key)
                except Exception:
                    continue
                val = item.get("value")
                if value_parser is not None:
                    try:
                        val = value_parser(val)
                    except Exception:
                        pass
                out[key_str] = val
        return out

    if not isinstance(payload, dict):
        return payload

    mesocycles = payload.get("mesocycles")
    if not isinstance(mesocycles, list):
        return payload

    for meso in mesocycles:
        if not isinstance(meso, dict):
            continue

        template = meso.get("microcycle_template")
        if isinstance(template, dict):
            meso["microcycle_template"] = _normalize_microcycle(template, 1)
        elif template is not None:
            meso.pop("microcycle_template", None)

        microcycles = meso.get("microcycles")
        if isinstance(microcycles, list):
            normalized_microcycles: list[dict[str, Any]] = []
            for idx, item in enumerate(microcycles, start=1):
                if isinstance(item, dict):
                    normalized_microcycles.append(_normalize_microcycle(item, idx))
            meso["microcycles"] = normalized_microcycles or None
        elif microcycles is not None:
            meso.pop("microcycles", None)

        guidelines = meso.get("guidelines")
        if not isinstance(guidelines, dict):
            continue

        wvt = guidelines.get("weekly_volume_targets")
        if isinstance(wvt, list):
            parsed = _kv_pairs_to_dict(wvt, _parse_int_tolerant)
            guidelines["weekly_volume_targets"] = {
                k: int(v) for k, v in parsed.items() if _parse_int_tolerant(v) is not None and k in ALLOWED_VOLUME_KEYS
            }
        elif isinstance(wvt, dict):
            guidelines["weekly_volume_targets"] = {
                str(k): int(_parse_int_tolerant(v))  # type: ignore[arg-type]
                for k, v in wvt.items()
                if _parse_int_tolerant(v) is not None and str(k) in ALLOWED_VOLUME_KEYS
            }

        ib = guidelines.get("intensity_bands")
        if isinstance(ib, list):
            parsed = _kv_pairs_to_dict(ib, lambda x: x)
            guidelines["intensity_bands"] = {k: (str(v) if v is not None else "") for k, v in parsed.items()}
        elif isinstance(ib, dict):
            guidelines["intensity_bands"] = {str(k): (str(v) if v is not None else "") for k, v in ib.items()}

        pwt = guidelines.get("per_workout_targets")
        if isinstance(pwt, dict):
            number = _parse_int_tolerant(pwt.get("number_of_exercises"))
            set_range = pwt.get("set_range")
            sr_out: list[int] | None = None
            if isinstance(set_range, list) and len(set_range) >= 2:
                a = _parse_int_tolerant(set_range[0])
                b = _parse_int_tolerant(set_range[1])
                if a is not None and b is not None:
                    sr_out = [int(a), int(b)]
            guidelines["per_workout_targets"] = {
                "number_of_exercises": (int(number) if number is not None else None),
                "set_range": sr_out,
            }
        else:
            if "per_workout_targets" in guidelines and not isinstance(pwt, dict):
                guidelines.pop("per_workout_targets", None)

    return payload


async def _generate_outline_staged(
    user_data: UserDataInput,
    available_exercises: list[dict[str, Any]],
) -> OutlineSpec:
    preview = _format_available_exercises_preview(available_exercises)
    prompt = build_outline_prompt(user_data=user_data, preview=preview)
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "duration_weeks": {"type": "number"},
            "mesocycles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "weeks_count": {"type": "number"},
                        "microcycles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "order_index": {"type": "number"},
                                    "days_count": {"type": "number"},
                                    "workouts_per_microcycle": {"type": "number"},
                                    "day_labels": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "focus": {"type": "string"},
                                },
                                "required": [],
                            },
                        },
                        "microcycle_template": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "days_count": {"type": "number"},
                                "workouts_per_microcycle": {"type": "number"},
                                "day_labels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": [],
                        },
                        "guidelines": {
                            "type": "object",
                            "properties": {
                                "weekly_volume_targets": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {"type": "number"},
                                        },
                                        "required": ["key", "value"],
                                    },
                                },
                                "intensity_bands": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {"type": "string"},
                                        },
                                        "required": ["key", "value"],
                                    },
                                },
                                "per_workout_targets": {
                                    "type": "object",
                                    "properties": {
                                        "number_of_exercises": {"type": "number"},
                                        "set_range": {
                                            "type": "array",
                                            "items": {"type": "number"},
                                            "minItems": 2,
                                            "maxItems": 2,
                                        },
                                    },
                                },
                                "focus_areas": {"type": "array", "items": {"type": "string"}},
                                "exercise_categories_allowed": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["name", "weeks_count", "guidelines"],
                },
            },
        },
        "required": ["name", "mesocycles"],
    }
    payload = await _genai_generate_json(
        prompt=prompt,
        response_schema=schema,
        temperature=0.35,
    )

    payload = _sanitize_outline_payload(payload)
    outline = OutlineSpec(**payload)
    return outline


async def generate_training_plan(user_data: UserDataInput) -> TrainingPlan:
    from ..config import Settings

    settings = Settings()
    available_exercises = await _get_available_exercises(settings)
    plan, _ = await _generate_staged_plan(user_data, available_exercises)
    return plan


async def generate_training_plan_with_rationale(
    user_data: UserDataInput,
) -> tuple[TrainingPlan, str | None]:
    from ..config import Settings

    settings = Settings()
    available_exercises = await _get_available_exercises(settings)
    plan, diagnostics = await _generate_staged_plan(user_data, available_exercises)
    rationale_json: str | None = None
    if diagnostics and diagnostics.plan_rationale is not None:
        try:
            data = diagnostics.plan_rationale.model_dump()
        except Exception:
            data = getattr(diagnostics.plan_rationale, "__dict__", None)
        if data is not None:
            import json as _json

            rationale_json = _json.dumps(data, ensure_ascii=False, indent=2)
    return plan, rationale_json


async def generate_training_plan_with_summary(
    user_data: UserDataInput,
) -> tuple[TrainingPlan, str | None]:
    from ..config import Settings

    settings = Settings()
    available_exercises = await _get_available_exercises(settings)
    plan, diagnostics = await _generate_staged_plan(user_data, available_exercises)
    summary = diagnostics.plan_summary if diagnostics else None
    logger.info("Generated training plan with summary")
    return plan, summary


def _prepare_plan_context_for_summary(
    *,
    user_data: UserDataInput,
    plan: TrainingPlan,
    skeleton: StagedSkeleton,
    diagnostics: StagedDiagnostics,
    available_exercises: list[dict[str, Any]],
) -> dict[str, Any]:
    workouts_by_micro: dict[int, list[PlanWorkout]] = defaultdict(list)
    for workout in plan.workouts:
        workouts_by_micro[workout.microcycle_id].append(workout)

    micro_summaries = []
    for micro in plan.microcycles:
        workouts = workouts_by_micro.get(micro.id, [])
        micro_summaries.append(
            {
                "id": micro.id,
                "name": micro.name,
                "order": micro.order_index,
                "days": micro.days_count,
                "workouts": [w.day_label for w in workouts],
            }
        )

    per_workout_stats = diagnostics.per_workout_stats or {}
    workout_summaries = []
    for workout in plan.workouts:
        stats = per_workout_stats.get(workout.id, {})
        workout_summaries.append(
            {
                "id": workout.id,
                "label": workout.day_label,
                "microcycle_id": workout.microcycle_id,
                "exercises": stats.get("exercises", 0),
                "sets": stats.get("sets", 0),
            }
        )

    volume_summary = diagnostics.volume_by_pattern_per_micro or {}
    available_preview = _format_available_exercises_preview(available_exercises, limit=10)

    return {
        "user": user_data.model_dump(mode="json"),
        "plan": {
            "name": plan.calendar_plan.name,
            "duration_weeks": plan.calendar_plan.duration_weeks,
            "mesocycles": len(plan.mesocycles),
            "microcycles": len(plan.microcycles),
            "workouts": len(plan.workouts),
        },
        "microcycles": micro_summaries,
        "workouts": workout_summaries,
        "volume_by_micro": volume_summary,
        "auto_fixes": diagnostics.auto_fixes,
        "available_exercises_preview": available_preview,
    }
