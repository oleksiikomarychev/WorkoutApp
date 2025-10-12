from __future__ import annotations

import os
import json
import logging
import time
import asyncio
from dataclasses import dataclass
from collections import defaultdict, deque
from itertools import count
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator, model_validator
import re

from ..config import Settings
from ..prompts import (
    build_headers_prompt,
    build_outline_prompt,
    build_sets_prompt,
    build_summary_rationale_prompt,
)

# Optional: tolerant JSON parser removed (was used for LM Studio only)

def _parse_int_tolerant(value: Any) -> Optional[int]:
    """Parse integers from various user/LLM formats.
    Supports:
    - plain ints/floats
    - percentages: "70%"
    - reps: "8 reps", "x8"
    - effort: "RPE 8", "рпе 8"
    - ranges: "8-10", "6–8" (returns rounded average)
    - generic first integer in string
    Returns None if nothing sensible can be parsed.
    """
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
        # Range: 8-10 / 6–8
        m = re.search(r"(\d+)\s*[-–]\s*(\d+)", s)
        if m:
            a = int(m.group(1))
            b = int(m.group(2))
            try:
                return int(round((a + b) / 2))
            except Exception:
                return a
        # RPE
        m = re.search(r"(?:rpe)\s*(\d+)", s)
        if m:
            return int(m.group(1))
        # Percentage
        m = re.search(r"(\d+)\s*%", s)
        if m:
            return int(m.group(1))
        # Reps / x8
        m = re.search(r"(\d+)\s*(?:reps?|x)\b", s)
        if m:
            return int(m.group(1))
        # Fallback: first integer
        m = re.search(r"\b(\d+)\b", s)
        if m:
            return int(m.group(1))
    # Last resort: try builtin int()
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None


def _load_rpe_table() -> Dict[str, Dict[str, int]]:
    """Load the RPE reference table from disk (or env override)."""
    logger = logging.getLogger(__name__)
    candidates: List[Path] = []
    env_path = os.getenv("RPE_TABLE_PATH")
    if env_path:
        candidates.append(Path(env_path))
    try:
        default_path = Path(__file__).resolve().parents[3] / "rpe-service" / "rpe_table.json"
        candidates.append(default_path)
        # Also check nested path used by rpe-service package layout
        alt_default_path = Path(__file__).resolve().parents[3] / "rpe-service" / "rpe_service" / "rpe_table.json"
        candidates.append(alt_default_path)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to build default RPE table path: %s", exc)

    for candidate in candidates:
        try:
            with candidate.open("r", encoding="utf-8") as f:
                raw_data = json.load(f)
            if not isinstance(raw_data, dict):
                logger.warning("RPE table at %s is not a dict", candidate)
                continue
            table: Dict[str, Dict[str, int]] = {}
            for intensity_key, mapping in raw_data.items():
                if not isinstance(mapping, dict):
                    continue
                normalized_intensity = str(int(round(intensity_key))) if isinstance(intensity_key, (int, float)) else str(intensity_key)
                normalized_mapping: Dict[str, int] = {}
                for effort_key, reps_value in mapping.items():
                    if not isinstance(reps_value, (int, float)):
                        continue
                    normalized_effort = str(int(round(effort_key))) if isinstance(effort_key, (int, float)) else str(effort_key)
                    normalized_mapping[normalized_effort] = int(round(reps_value))
                if normalized_mapping:
                    table[normalized_intensity] = normalized_mapping
            if table:
                logger.debug("Loaded RPE table from %s with %d intensity rows", candidate, len(table))
                return table
        except FileNotFoundError:
            continue
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("Failed to load RPE table from %s: %s", candidate, exc)

    # HTTP fallback: try environment URL, then common service URLs
    http_urls: List[str] = []
    env_url = os.getenv("RPE_TABLE_URL")
    if env_url:
        http_urls.append(env_url)
    # Docker compose service name (in-network)
    http_urls.append("http://rpe-service:8001/rpe/table")
    # Host-local fallback (useful during local dev without compose networking)
    http_urls.append("http://localhost:8001/rpe/table")

    for url in http_urls:
        try:
            try:
                import httpx  # lazy import to avoid hard dependency on import
            except Exception as exc:  # pragma: no cover
                logger.debug("httpx not available for RPE HTTP fallback: %s", exc)
                break

            with httpx.Client(timeout=3.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                raw_data = resp.json()

            if not isinstance(raw_data, dict):
                logger.warning("RPE table URL %s returned non-dict payload of type %s", url, type(raw_data).__name__)
                continue

            # Normalize to Dict[str, Dict[str, int]]
            table: Dict[str, Dict[str, int]] = {}
            for intensity_key, mapping in raw_data.items():
                if not isinstance(mapping, dict):
                    continue
                normalized_intensity = str(int(round(intensity_key))) if isinstance(intensity_key, (int, float)) else str(intensity_key)
                normalized_mapping: Dict[str, int] = {}
                for effort_key, reps_value in mapping.items():
                    if not isinstance(reps_value, (int, float)):
                        continue
                    normalized_effort = str(int(round(effort_key))) if isinstance(effort_key, (int, float)) else str(effort_key)
                    normalized_mapping[normalized_effort] = int(round(reps_value))
                if normalized_mapping:
                    table[normalized_intensity] = normalized_mapping
            if table:
                logger.info("Loaded RPE table from %s with %d intensity rows", url, len(table))
                return table
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("Failed to load RPE table from URL %s: %s", url, exc)

    logger.warning("RPE table not found; falling back to static guidance")
    return {}


def _format_rpe_summary(table: Dict[str, Dict[str, int]]) -> str:
    if not table:
        return ""
    lines: List[str] = []
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


_RPE_TABLE: Dict[str, Dict[str, int]] = _load_rpe_table()
_RPE_TABLE_SUMMARY: str = _format_rpe_summary(_RPE_TABLE)
_RPE_TABLE_JSON_TEXT: str = json.dumps(_RPE_TABLE, ensure_ascii=False, indent=2, sort_keys=True) if _RPE_TABLE else ""

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
except Exception:
    _EXERCISES_CACHE_TTL_SECONDS = 1800

_EXERCISES_CACHE: Dict[str, Any] = {"data": None, "expires_at": 0.0}
_EXERCISES_CACHE_LOCK = asyncio.Lock()

_SETTINGS = Settings()
_GENAI_CLIENT: Optional[genai.Client] = None
_GENAI_MODEL = _SETTINGS.staged_llm_model
_GENAI_MAX_ATTEMPTS = _SETTINGS.genai_max_attempts
_GENAI_BASE_DELAY = _SETTINGS.genai_base_delay
_GENAI_RATE_LIMIT_PER_MINUTE = _SETTINGS.genai_rate_limit_per_minute
_GENAI_RATE_LIMIT_WINDOW_SECONDS = _SETTINGS.genai_rate_limit_window_seconds
_GENAI_RATE_LIMIT_CONCURRENCY = _SETTINGS.genai_rate_limit_concurrency

_GENAI_RATE_LIMIT_SEMAPHORE = asyncio.Semaphore(_GENAI_RATE_LIMIT_CONCURRENCY)
_GENAI_RATE_LIMIT_LOCK = asyncio.Lock()
_GENAI_RATE_LIMIT_HISTORY: defaultdict[str, Deque[float]] = defaultdict(deque)


class GenAIUnavailableError(RuntimeError):
    """Raised when the GenAI service quota is exhausted."""


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
    """Lazily initialize Google GenAI client from GEMINI_API_KEY/GOOGLE_API_KEY."""
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
    response_schema: Dict[str, Any],
    temperature: float = 0.4,
    model: Optional[str] = None,
    max_output_tokens: int = 100000,
) -> Dict[str, Any]:
    """Call Gemini model once and return parsed JSON dict with diagnostics."""

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
        logging.warning("GenAI request failed: %s", exc)
        if _is_quota_or_rate_limit_error(exc):
            raise GenAIUnavailableError("GenAI quota exhausted") from exc
        raise

    candidate = response.candidates[0] if getattr(response, "candidates", None) else None
    finish_reason = getattr(candidate, "finish_reason", None)
    safety_ratings = getattr(candidate, "safety_ratings", None)
    usage = getattr(response, "usage_metadata", None)
    logging.debug(
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
    except Exception as exc:
        logging.error(
            "GenAI JSON parse error: %s | preview=%s",
            exc,
            truncated_preview,
        )
        raise

    if not isinstance(parsed, dict):
        logging.error("GenAI JSON result is not dict | preview=%s", truncated_preview)
        raise ValueError("Non-dict GenAI JSON response")

    return parsed


def _format_available_exercises_preview(available_exercises: List[Dict[str, Any]], *, limit: int = 30) -> str:
    lines: List[str] = []
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
) -> Dict[int, Tuple[Optional[int], Optional[int], Optional[int]]]:
    micro_lookup = {mc.id: mc for mc in skeleton.microcycles}
    meso_lookup = {meso.id: meso for meso in skeleton.mesocycles}
    constraints: Dict[int, Tuple[Optional[int], Optional[int], Optional[int]]] = {}

    for workout in skeleton.workouts:
        micro = micro_lookup.get(workout.microcycle_id)
        meso = meso_lookup.get(micro.mesocycle_id) if micro else None
        outline = skeleton.meso_outline_map.get(meso.id) if meso else None
        per_targets = outline.guidelines.per_workout_targets if outline and outline.guidelines else None

        desired_exercises: Optional[int] = None
        min_sets: Optional[int] = None
        max_sets: Optional[int] = None

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
    workouts: List[WorkoutSetsDraft],
    constraints: Dict[int, Tuple[Optional[int], Optional[int], Optional[int]]],
) -> Tuple[List[WorkoutSetsDraft], List[str]]:
    adjustments: List[str] = []
    adjusted_workouts: List[WorkoutSetsDraft] = []

    for workout in workouts:
        desired_exercises, min_sets, max_sets = constraints.get(
            workout.workout_id, (None, None, None)
        )

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
                f"Workout {copy.workout_id}: sets adjusted from {original_sets} to {total_sets} (min={min_sets or '-'}, max={max_sets or '-'})"
            )

        adjusted_workouts.append(copy)

    return adjusted_workouts, adjustments


async def _generate_headers_staged(
    user_data: "UserDataInput",
    skeleton: StagedSkeleton,
    available_exercises: List[Dict[str, Any]],
) -> List[WorkoutHeaderDraft]:
    logger = logging.getLogger(__name__)

    if not _is_staged_headers_enabled():
        raise RuntimeError("LLM headers stage is disabled")

    allowed_map = _allowed_exercise_ids(available_exercises)
    if not allowed_map:
        raise RuntimeError("No allowed exercises available for headers stage")

    micro_lookup = {mc.id: mc for mc in skeleton.microcycles}
    meso_lookup = {meso.id: meso for meso in skeleton.mesocycles}

    # Prepare common preview and schema once
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

    # Group workouts by microcycle to reduce per-call JSON size
    from collections import defaultdict as _dd
    workouts_by_micro: Dict[int, List[PlanWorkout]] = _dd(list)
    for w in skeleton.workouts:
        workouts_by_micro[w.microcycle_id].append(w)

    workout_lookup = {w.id: w for w in skeleton.workouts}
    aggregated: List[WorkoutHeaderDraft] = []
    chunks = 0

    for micro in skeleton.microcycles:
        group = workouts_by_micro.get(micro.id, [])
        if not group:
            continue
        chunks += 1

        # Build microcycle-specific workout lines
        workout_lines: List[str] = []
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
                except Exception:
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

    logger.info("LLM headers generated (chunked): %d workouts across %d microcycles", len(aggregated), chunks)
    return aggregated


async def _generate_sets_staged(
    user_data: "UserDataInput",
    skeleton: StagedSkeleton,
    plan_exercises: List[PlanExercise],
    available_exercises: List[Dict[str, Any]],
) -> List[WorkoutSetsDraft]:
    logger = logging.getLogger(__name__)

    if not _is_staged_headers_enabled():
        raise RuntimeError("LLM sets stage is disabled")

    if not plan_exercises:
        raise RuntimeError("No plan exercises available for sets stage")

    # Map exercises by workout for quick access
    exercises_by_workout: Dict[int, List[PlanExercise]] = defaultdict(list)
    for ex in plan_exercises:
        exercises_by_workout[ex.plan_workout_id].append(ex)

    # Common schema reused for each chunk
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

    # Group workouts by microcycle and build context per chunk
    from collections import defaultdict as _dd
    workouts_by_micro: Dict[int, List[PlanWorkout]] = _dd(list)
    for w in skeleton.workouts:
        workouts_by_micro[w.microcycle_id].append(w)

    aggregated_sets: List[WorkoutSetsDraft] = []
    chunks = 0
    for micro in skeleton.microcycles:
        group = [w for w in workouts_by_micro.get(micro.id, []) if exercises_by_workout.get(w.id)]
        if not group:
            continue
        chunks += 1

        workout_context: List[str] = []
        for workout in group:
            exercises = exercises_by_workout.get(workout.id, [])
            if not exercises:
                continue
            exercise_lines = ", ".join(
                f"{ex.exercise_name} (id={ex.exercise_definition_id})" for ex in exercises
            )
            workout_context.append(
                f"Workout {workout.id} {workout.day_label}: {exercise_lines}"
            )

        prompt = build_sets_prompt(
            user_data=user_data,
            workout_context=workout_context,
            rpe_summary=_RPE_TABLE_SUMMARY,
        )

        payload = await _genai_generate_json(
            prompt=prompt,
            response_schema=schema,
            temperature=0.35,
        )
        batch = WorkoutSetsBatch.model_validate(payload)
        aggregated_sets.extend(batch.workouts)

    constraints = _collect_workout_constraints(skeleton)
    adjusted_workouts, adjustments = _apply_set_constraints(aggregated_sets, constraints)
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


async def _get_available_exercises(settings: "Settings") -> List[Dict[str, Any]]:
    """Fetch exercise definitions from exercises-service with caching."""
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
        logger.error("Failed to fetch available exercises: %s", exc)
        raise RuntimeError("Failed to fetch available exercises") from exc

    if not isinstance(data, list):
        logger.error("Exercises service returned unexpected payload type: %s", type(data).__name__)
        raise RuntimeError("Exercises service returned unexpected payload type")

    sanitized: List[Dict[str, Any]] = [item for item in data if isinstance(item, dict)]

    async with _EXERCISES_CACHE_LOCK:
        _EXERCISES_CACHE["data"] = sanitized
        _EXERCISES_CACHE["expires_at"] = time.time() + _EXERCISES_CACHE_TTL_SECONDS

    logger.debug(
        "Fetched %d available exercises (cached for %ds)",
        len(sanitized),
        _EXERCISES_CACHE_TTL_SECONDS,
    )
    return sanitized

from ..schemas.training_plans import (
    TrainingPlan,
    CalendarPlan,
    Mesocycle,
    Microcycle,
    PlanWorkout,
    PlanExercise,
    PlanSet,
)
from ..schemas.user_data import UserDataInput

# LLM response schemas (without IDs - they'll be assigned during normalization)
class LLMPlanSet(BaseModel):
    """Set configuration for LLM response."""
    order_index: int = Field(description="Sequential order starting from 1")
    intensity: Optional[int] = None
    effort: Optional[int] = None
    volume: Optional[int] = None

    @field_validator("intensity", "effort", "volume", mode="before")
    @classmethod
    def _parse_numbers_tolerant(cls, v, info):
        field_name = info.field_name
        parsed = _parse_int_tolerant(v)
        logger = logging.getLogger(__name__)
        logger.debug(
            "LLMPlanSet field parsing | field=%s raw_value=%s parsed_value=%s raw_type=%s",
            field_name, repr(v), repr(parsed), type(v).__name__
        )
        return parsed

    @model_validator(mode="after")
    def _validate_and_clamp(self):
        logger = logging.getLogger(__name__)
        logger.debug(
            "LLMPlanSet validation | order_index=%d intensity=%s effort=%s volume=%s",
            self.order_index, repr(self.intensity), repr(self.effort), repr(self.volume)
        )
        
        # Clamp to sensible ranges
        if self.intensity is not None:
            self.intensity = max(0, min(100, int(self.intensity)))
        if self.effort is not None:
            self.effort = max(1, min(10, int(self.effort)))
        if self.volume is not None:
            self.volume = max(1, int(self.volume))

        # Require at least two parameters for every set (no special cases for time-based/isometric exercises).
        present = sum(1 for v in (self.intensity, self.effort, self.volume) if v is not None)
        if present < 2:
            logger.error(
                "LLMPlanSet VALIDATION FAILED | order_index=%d intensity=%s effort=%s volume=%s present=%d",
                self.order_index, repr(self.intensity), repr(self.effort), repr(self.volume), present
            )
            raise ValueError("At least two of intensity/effort/volume must be provided")
        return self

class LLMPlanExercise(BaseModel):
    """Exercise in a workout for LLM response."""
    exercise_definition_id: int = Field(description="ID from the allowed exercises list")
    exercise_name: str = Field(description="Exact name from the allowed exercises list")
    order_index: int = Field(description="Sequential order starting from 1")
    sets: List[LLMPlanSet] = Field(description="List of sets for this exercise")

class LLMPlanWorkout(BaseModel):
    """Workout in a microcycle for LLM response."""
    day_label: str = Field(description="Day label like 'Monday', 'Day 1', etc.")
    order_index: int = Field(description="Sequential order starting from 1")
    exercises: List[LLMPlanExercise] = Field(description="List of exercises in this workout")

class LLMMicrocycle(BaseModel):
    """Microcycle (week) in a mesocycle for LLM response."""
    name: str = Field(description="Microcycle name")
    order_index: int = Field(description="Sequential order starting from 1")
    days_count: int = Field(description="Number of days in this microcycle")
    plan_workouts: List[LLMPlanWorkout] = Field(description="List of workouts in this microcycle")

class LLMMesocycle(BaseModel):
    """Mesocycle (training block) for LLM response."""
    name: str = Field(description="Mesocycle name")
    order_index: int = Field(description="Sequential order starting from 1")
    weeks_count: int = Field(description="Number of weeks in this mesocycle")
    microcycles: List[LLMMicrocycle] = Field(description="List of microcycles in this mesocycle")

class LLMCalendarPlan(BaseModel):
    """Calendar plan metadata for LLM response."""
    name: str = Field(description="Training plan name")
    duration_weeks: int = Field(description="Total duration in weeks")

class LLMTrainingPlanResponse(BaseModel):
    """Complete training plan structure for LLM response."""
    calendar_plan: LLMCalendarPlan
    mesocycles: List[LLMMesocycle]
    # Optional structured rationale for decisions (in-RU strings)
    plan_rationale: Optional["LLMPlanRationale"] = None
    # Optional concise plan summary in Russian, referencing exact plan details
    plan_summary: Optional[str] = None

class LLMPlanRationale(BaseModel):
    """Structured rationale sections in Russian. Keep values concise, plain text."""
    goals_interpretation: Optional[str] = Field(default=None, description="Как цели пользователя интерпретированы")
    periodization: Optional[str] = Field(default=None, description="Почему выбрана такая периодизация и длительность мезо/микроциклов")
    frequency: Optional[str] = Field(default=None, description="Почему выбрана такая частота тренировок и распределение по неделям")
    exercise_selection: Optional[str] = Field(default=None, description="Логика выбора упражнений: баланс тяга/жим/ноги/кор, вариативность")
    set_parameters: Optional[str] = Field(default=None, description="Интенсивность/повторения/RPE и соответствие целям")
    constraints_equipment: Optional[str] = Field(default=None, description="Как учтены ограничения и доступное оборудование")
    progression: Optional[str] = Field(default=None, description="Как планируется прогрессия и адаптация при нехватке времени/усталости")

# Resolve forward refs for plan_rationale
LLMTrainingPlanResponse.model_rebuild()

class OutlineMicrocycle(BaseModel):
    """Explicit microcycle definition used by LLM outline stage."""
    name: Optional[str] = Field(default=None, description="Microcycle name")
    days_count: Optional[int] = Field(default=None, description="Number of days in this microcycle")
    workouts_per_microcycle: Optional[int] = Field(
        default=None,
        description="Number of workouts to schedule inside this microcycle",
    )
    order_index: Optional[int] = Field(default=None, description="1-based microcycle order inside the mesocycle")
    day_labels: Optional[List[str]] = Field(
        default=None,
        description="Optional list of day labels for workouts (e.g., ['Пн', 'Ср', 'Пт'])",
    )
    focus: Optional[str] = Field(default=None, description="Optional focus/theme for the microcycle")


class OutlinePerWorkoutTargets(BaseModel):
    """Optional per-workout targets (kept generic and data-only)."""
    number_of_exercises: Optional[int] = None
    set_range: Optional[List[int]] = None  # [min_sets, max_sets] per workout


class OutlineGuidelines(BaseModel):
    """Dynamic training intents derived by LLM (no hardcoded numbers in code)."""
    # Schemas are relaxed to Optional[Dict[str, Any]] to allow initial parsing of schema-like LLM output.
    # The _sanitize_outline_data function is responsible for converting these to the correct types.
    weekly_volume_targets: Optional[Dict[str, Any]] = None  # e.g., {"push": 12, "pull": 14, "legs": 16}
    intensity_bands: Optional[Dict[str, Any]] = None        # e.g., {"main_lifts": "70-85%", "assistance": "60-75%"}
    per_workout_targets: Optional[OutlinePerWorkoutTargets] = None
    focus_areas: Optional[List[str]] = None                  # e.g., ["bench_press_strength"]
    exercise_categories_allowed: Optional[List[str]] = None  # e.g., ["barbell","dumbbell","bodyweight"]


class OutlineMesocycle(BaseModel):
    """High-level mesocycle description with optional explicit microcycles and guidelines."""
    name: str = Field(description="Mesocycle name")
    weeks_count: int = Field(description="Number of weeks in this mesocycle")
    microcycles: Optional[List[OutlineMicrocycle]] = Field(
        default=None,
        description="Explicit list of microcycles (one per week). If omitted, fallback to template",
    )
    microcycle_template: Optional[OutlineMicrocycle] = Field(
        default=None,
        description="Legacy microcycle template repeated to fill missing weeks",
    )
    guidelines: OutlineGuidelines = Field(description="Dynamic guidelines for this mesocycle (mandatory)")

    @model_validator(mode="after")
    def _ensure_microcycle_order(self) -> "OutlineMesocycle":
        default_template = self.microcycle_template
        if not self.microcycles and default_template is None:
            default_template = OutlineMicrocycle(
                name=f"{self.name} - Week",
                days_count=7,
                workouts_per_microcycle=3,
            )
            self.microcycle_template = default_template

        if self.microcycles:
            normalized: List[OutlineMicrocycle] = []
            for idx, micro in enumerate(self.microcycles, start=1):
                defaults: Dict[str, Any] = {}
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
    """High-level training plan outline to guide the final deterministic generation."""
    name: str = Field(description="Outline name (plan name)")
    duration_weeks: Optional[int] = Field(default=None, description="Total duration in weeks (optional; if omitted, infer later)")
    mesocycles: List[OutlineMesocycle] = Field(description="List of mesocycles with weeks_count and microcycle data")

    def total_weeks(self) -> int:
        weeks = sum(m.weeks_count for m in self.mesocycles)
        if weeks <= 0:
            raise ValueError("Outline must contain at least one week across mesocycles")
        return weeks


def _meso_micro_schedule(meso_outline: OutlineMesocycle) -> List[OutlineMicrocycle]:
    """Materialize ordered microcycles for a mesocycle using explicit list or template."""

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

        normalized: List[OutlineMicrocycle] = []
        for idx, micro in enumerate(micro_list, start=1):
            updates: Dict[str, Any] = {}
            if micro.order_index is None:
                updates["order_index"] = idx
            if not micro.name:
                updates["name"] = f"Week {idx}"
            if micro.days_count is None and default_template.days_count is not None:
                updates["days_count"] = default_template.days_count
            if (
                micro.workouts_per_microcycle is None
                and default_template.workouts_per_microcycle is not None
            ):
                updates["workouts_per_microcycle"] = default_template.workouts_per_microcycle
            if not micro.day_labels and default_template.day_labels:
                updates["day_labels"] = list(default_template.day_labels)
            if updates:
                micro = micro.model_copy(update=updates)
            normalized.append(micro)
        return normalized

    materialized: List[OutlineMicrocycle] = []
    for idx in range(1, meso_outline.weeks_count + 1):
        defaults = {
            "order_index": idx,
            "name": default_template.name or f"Week {idx}",
            "days_count": default_template.days_count,
            "workouts_per_microcycle": default_template.workouts_per_microcycle,
            "day_labels": default_template.day_labels,
        }
        materialized.append(
            default_template.model_copy(
                update={k: v for k, v in defaults.items() if v is not None}
            )
        )
    return materialized


class WorkoutHeaderExerciseDraft(BaseModel):
    exercise_definition_id: int
    exercise_name: str
    order_index: int


class WorkoutHeaderDraft(BaseModel):
    workout_id: int
    day_label: Optional[str] = None
    exercises: List[WorkoutHeaderExerciseDraft]


class WorkoutHeaderBatch(BaseModel):
    workouts: List[WorkoutHeaderDraft]


class PlanSetDraft(BaseModel):
    order_index: int
    intensity: Optional[int] = Field(default=None, ge=0, le=100)
    effort: Optional[int] = Field(default=None, ge=1, le=10)
    volume: Optional[int] = Field(default=None, ge=1)

    @field_validator("intensity", "effort", "volume", mode="before")
    @classmethod
    def _coerce_numbers(cls, value):
        parsed = _parse_int_tolerant(value)
        return parsed if parsed is not None else value


class WorkoutSetExerciseDraft(BaseModel):
    exercise_definition_id: int
    sets: List[PlanSetDraft]


class WorkoutSetsDraft(BaseModel):
    workout_id: int
    exercises: List[WorkoutSetExerciseDraft]


class WorkoutSetsBatch(BaseModel):
    workouts: List[WorkoutSetsDraft]


@dataclass
class StagedSkeleton:
    id_gen: count
    calendar_plan: "CalendarPlan"
    mesocycles: List["Mesocycle"]
    microcycles: List["Microcycle"]
    workouts: List["PlanWorkout"]
    meso_outline_map: Dict[int, OutlineMesocycle]


def _find_mesocycle_for_microcycle(mesocycles: List["Mesocycle"], microcycle: "Microcycle") -> Optional["Mesocycle"]:
    for meso in mesocycles:
        if meso.id == microcycle.mesocycle_id:
            return meso
    return None


def _allowed_exercise_ids(available_exercises: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    mapping: Dict[int, Dict[str, Any]] = {}
    for raw in available_exercises:
        try:
            ex_id = int(raw["id"])
        except Exception:
            continue
        mapping[ex_id] = raw
    return mapping


def _validate_header_exercises(
    exercises: List[WorkoutHeaderExerciseDraft],
    allowed_map: Dict[int, Dict[str, Any]],
) -> None:
    for ex in exercises:
        if ex.exercise_definition_id not in allowed_map:
            raise ValueError(
                f"exercise_definition_id {ex.exercise_definition_id} is not allowed"
            )


def _build_staged_skeleton(outline: OutlineSpec) -> StagedSkeleton:
    id_gen = count(1)
    duration = outline.duration_weeks or outline.total_weeks()

    calendar_plan = CalendarPlan(
        id=next(id_gen),
        name=outline.name,
        duration_weeks=duration,
    )

    mesocycles: List[Mesocycle] = []
    microcycles: List[Microcycle] = []
    workouts: List[PlanWorkout] = []
    meso_outline_map: Dict[int, OutlineMesocycle] = {}

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

            workouts_target: Optional[int] = None
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
                    day_labels.extend(
                        f"Day {i}" for i in range(len(day_labels) + 1, workouts_target + 1)
                    )
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
    headers: List[WorkoutHeaderDraft],
) -> List[PlanExercise]:
    workout_ids = {w.id for w in skeleton.workouts}
    exercises: List[PlanExercise] = []
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
    plan_exercises: List[PlanExercise],
    sets_batch: List[WorkoutSetsDraft],
) -> List[PlanSet]:
    lookup: Dict[tuple[int, int], PlanExercise] = {}
    for ex in plan_exercises:
        lookup[(ex.plan_workout_id, ex.exercise_definition_id)] = ex

    plan_sets: List[PlanSet] = []
    for workout_sets in sets_batch:
        for exercise_sets in workout_sets.exercises:
            key = (workout_sets.workout_id, exercise_sets.exercise_definition_id)
            if key not in lookup:
                raise ValueError(
                    f"Workout {workout_sets.workout_id} returned sets for unknown exercise_definition_id {exercise_sets.exercise_definition_id}"
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
    volume_by_pattern_per_micro: Dict[int, Dict[str, int]]
    per_workout_stats: Dict[int, Dict[str, int]]  # workout_id -> {exercises, sets}
    violations: List[str]
    auto_fixes: List[str]
    raw_llm: Optional[Dict[str, Any]] = None
    plan_summary: Optional[str] = None
    plan_rationale: Optional["LLMPlanRationale"] = None


def _compute_plan_metrics(
    plan: "TrainingPlan",
    allowed_map: Dict[int, Dict[str, Any]],
) -> tuple[Dict[int, Dict[str, int]], Dict[int, Dict[str, int]]]:
    """Compute per-micro pattern volumes and per-workout exercise/set counts."""

    volume_by_micro: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_workout_stats: Dict[int, Dict[str, int]] = {}

    exercises_by_workout: Dict[int, List[PlanExercise]] = defaultdict(list)
    for ex in plan.exercises:
        exercises_by_workout[ex.plan_workout_id].append(ex)

    sets_by_exercise: Dict[int, List[PlanSet]] = defaultdict(list)
    for plan_set in plan.sets:
        sets_by_exercise[plan_set.plan_exercise_id].append(plan_set)

    for workout in plan.workouts:
        exercises = exercises_by_workout.get(workout.id, [])
        total_sets = 0
        for ex in exercises:
            sets_for_exercise = sets_by_exercise.get(ex.id, [])
            total_sets += len(sets_for_exercise)

            raw_ex = allowed_map.get(ex.exercise_definition_id, {})
            pattern_raw = (
                raw_ex.get("movement_type")
                or raw_ex.get("muscle_group")
                or raw_ex.get("region")
            )
            pattern = str(pattern_raw) if pattern_raw else "unknown"

            if sets_for_exercise:
                for plan_set in sets_for_exercise:
                    parsed_volume = plan_set.volume if plan_set.volume is not None else 1
                    if not isinstance(parsed_volume, int):
                        parsed_volume = _parse_int_tolerant(parsed_volume) or 1
                    volume_by_micro[workout.microcycle_id][pattern] += int(parsed_volume)
            else:
                volume_by_micro[workout.microcycle_id][pattern] += 1

        per_workout_stats[workout.id] = {
            "exercises": len(exercises),
            "sets": total_sets,
        }

    materialized_volume = {
        micro_id: dict(patterns)
        for micro_id, patterns in volume_by_micro.items()
    }
    return materialized_volume, per_workout_stats


def _validate_against_guidelines(
    skeleton: "StagedSkeleton",
    plan: "TrainingPlan",
    volume_by_micro: Dict[int, Dict[str, int]],
    per_workout_stats: Dict[int, Dict[str, int]],
) -> tuple[List[str], Dict[int, int]]:
    """Compare generated plan against dynamic outline guidelines.
    
    Returns:
        violations: List of validation error messages
        adjustments_dict: Dict[workout_id, ±1] for minor set adjustments
    """

    violations: List[str] = []
    adjustments_dict: Dict[int, int] = {}
    workouts_by_micro: Dict[int, List[PlanWorkout]] = defaultdict(list)
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
                        violations.append(
                            f"Microcycle '{micro.name}' pattern '{pattern}' short by {diff} units"
                        )

        per_workout_targets = guidelines.per_workout_targets
        if per_workout_targets:
            desired_ex = per_workout_targets.number_of_exercises
            min_sets: Optional[int] = None
            max_sets: Optional[int] = None
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
                        # Minor adjustment: add 1 set if diff is 1
                        if diff == 1:
                            adjustments_dict[workout.id] = 1
                    if max_sets is not None and stats["sets"] > max_sets:
                        diff = stats["sets"] - max_sets
                        violations.append(
                            f"Workout '{workout.day_label}' in microcycle '{micro.name}' exceeds guideline by {diff} sets"
                        )
                        # Minor adjustment: remove 1 set if diff is 1
                        if diff == 1:
                            adjustments_dict[workout.id] = -1

    violations_deduped = list(dict.fromkeys(violations))
    return violations_deduped, adjustments_dict


def _apply_minor_adjustments(
    plan: TrainingPlan,
    adjustments: Dict[int, int],
) -> tuple[TrainingPlan, List[str]]:
    """Вносит корректировки объёма (±1 сет на тренировку). Возвращает новый план и логи правок."""
    if not adjustments:
        return plan, []

    exercises_by_workout: Dict[int, List[PlanExercise]] = defaultdict(list)
    for plan_ex in plan.exercises:
        exercises_by_workout[plan_ex.plan_workout_id].append(plan_ex)

    sets_by_exercise: Dict[int, List[PlanSet]] = defaultdict(list)
    for plan_set in plan.sets:
        sets_by_exercise[plan_set.plan_exercise_id].append(plan_set)

    new_sets = list(plan.sets)
    fix_logs: List[str] = []

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
                fix_logs.append(
                    f"Workout {workout_id}: added set to exercise {target_ex.exercise_definition_id}"
                )
        else:
            remove_count = min(abs(delta), len(target_sets))
            for _ in range(remove_count):
                removed = target_sets.pop()
                new_sets = [s for s in new_sets if s.id != removed.id]
                fix_logs.append(
                    f"Workout {workout_id}: removed set from exercise {target_ex.exercise_definition_id}"
                )

    updated_plan = plan.model_copy(update={"sets": new_sets})
    return updated_plan, fix_logs


async def _generate_summary_and_rationale_staged(
    user_data: UserDataInput,
    plan: TrainingPlan,
    skeleton: StagedSkeleton,
    diagnostics: StagedDiagnostics,
    available_exercises: List[Dict[str, Any]],
) -> tuple[Optional[str], Optional[LLMPlanRationale]]:
    """Generate summary and rationale for a staged-generated plan via LLM."""
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
                    "required": []
                }
            },
            "required": ["plan_summary","plan_rationale"]
        }
        parsed = await _genai_generate_json(prompt=prompt, response_schema=schema, temperature=0.3)
        summary = parsed.get("plan_summary")
        rationale_dict = parsed.get("plan_rationale") or {}
        rationale = LLMPlanRationale(**{k: (rationale_dict.get(k) or None) for k in [
            "goals_interpretation","periodization","frequency","exercise_selection","set_parameters","constraints_equipment","progression"
        ]})
        return summary, rationale
    except Exception as exc:
        logger.warning("Summary/Rationale LLM failed: %s", exc)
        return None, None
async def _generate_staged_plan(
    user_data: UserDataInput,
    available_exercises: List[Dict[str, Any]],
) -> tuple[TrainingPlan, StagedDiagnostics]:
    """Generate training plan using staged pipeline: outline → headers → sets → summary/rationale.
    
    Args:
        user_data: User input data
        available_exercises: Available exercise definitions
        
    Returns:
        (plan, diagnostics) tuple with complete plan and diagnostics including summary/rationale
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting staged plan generation")
    
    # Stage 1: Generate outline
    outline = await _generate_outline_staged(user_data, available_exercises)
    logger.info(f"Outline generated: {outline.name}, {len(outline.mesocycles)} mesocycles")
    
    # Stage 2: Build skeleton from outline
    skeleton = _build_staged_skeleton(outline)
    logger.info(
        f"Skeleton built: {len(skeleton.workouts)} workouts, "
        f"{len(skeleton.microcycles)} microcycles, {len(skeleton.mesocycles)} mesocycles"
    )
    
    headers = await _generate_headers_staged(user_data, skeleton, available_exercises)
    logger.info(f"Headers generated: {len(headers)} workout headers")
    
    # Map headers into plan exercises
    plan_exercises = _map_headers_into_plan(skeleton, headers)
    
    # Stage 4: Generate sets for each workout
    sets_batch = await _generate_sets_staged(user_data, skeleton, plan_exercises, available_exercises)
    logger.info(f"Sets generated: {len(sets_batch)} workout sets")
    
    # Map sets into plan
    plan_sets = _map_sets_into_plan(skeleton, plan_exercises, sets_batch)
    
    # Assemble complete plan
    plan = TrainingPlan(
        calendar_plan=skeleton.calendar_plan,
        mesocycles=skeleton.mesocycles,
        microcycles=skeleton.microcycles,
        workouts=skeleton.workouts,
        exercises=plan_exercises,
        sets=plan_sets,
    )
    
    # Reconciliation and validation
    allowed_map = _allowed_exercise_ids(available_exercises)
    auto_fix_logs: List[str] = []
    
    vol_by_micro, per_workout_stats = _compute_plan_metrics(plan, allowed_map)
    violations, minor_adjust = _validate_against_guidelines(
        skeleton, plan, vol_by_micro, per_workout_stats
    )
    
    if minor_adjust:
        plan, fix_logs = _apply_minor_adjustments(plan, minor_adjust)
        auto_fix_logs.extend(fix_logs)
        auto_fix_logs = list(dict.fromkeys(auto_fix_logs))
        vol_by_micro, per_workout_stats = _compute_plan_metrics(plan, allowed_map)
        post_violations, _ = _validate_against_guidelines(
            skeleton, plan, vol_by_micro, per_workout_stats
        )
        violations = list(dict.fromkeys(post_violations))
    
    if violations:
        raise ValueError("Staged reconciliation failed: " + "; ".join(violations))
    
    # Create initial diagnostics
    diagnostics = StagedDiagnostics(
        volume_by_pattern_per_micro=vol_by_micro,
        per_workout_stats=per_workout_stats,
        violations=violations,
        auto_fixes=auto_fix_logs,
        raw_llm=None,
    )
    
    # Stage 5: Generate summary and rationale
    summary, rationale = await _generate_summary_and_rationale_staged(
        user_data=user_data,
        plan=plan,
        skeleton=skeleton,
        diagnostics=diagnostics,
        available_exercises=available_exercises,
    )
    
    # Update diagnostics with summary/rationale
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


def _sanitize_outline_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize outline payload from LLM (Variant 2 KV-arrays -> dicts, normalize values).

    - weekly_volume_targets: array[{key:string, value:number|string}] -> Dict[str, int]
    - intensity_bands:      array[{key:string, value:string}] -> Dict[str, str]
    - per_workout_targets:  keep only {number_of_exercises:int, set_range:[int,int]}
    """

    def _kv_pairs_to_dict(arr: Any, value_parser=None) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
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

    def _normalize_microcycle(raw: Dict[str, Any], order_idx: int) -> Dict[str, Any]:
        name = raw.get("name")
        name = str(name) if name not in (None, "") else None
        days = _parse_int_tolerant(raw.get("days_count"))
        workouts = _parse_int_tolerant(raw.get("workouts_per_microcycle"))
        order_val = _parse_int_tolerant(raw.get("order_index")) or order_idx

        day_labels_raw = raw.get("day_labels")
        day_labels: Optional[List[str]] = None
        if isinstance(day_labels_raw, list):
            converted = [str(lab).strip() for lab in day_labels_raw if lab not in (None, "")]
            day_labels = converted or None

        focus_val = raw.get("focus")
        focus = str(focus_val).strip() if isinstance(focus_val, str) and focus_val.strip() else None

        return {
            "name": name,
            "days_count": int(days) if days is not None else None,
            "workouts_per_microcycle": int(workouts) if workouts is not None else None,
            "order_index": order_val,
            "day_labels": day_labels,
            "focus": focus,
        }

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
            normalized_microcycles: List[Dict[str, Any]] = []
            for idx, item in enumerate(microcycles, start=1):
                if isinstance(item, dict):
                    normalized_microcycles.append(_normalize_microcycle(item, idx))
            meso["microcycles"] = normalized_microcycles or None
        elif microcycles is not None:
            meso.pop("microcycles", None)

        guidelines = meso.get("guidelines")
        if not isinstance(guidelines, dict):
            continue

        # weekly_volume_targets: KV array -> dict[str,int]
        wvt = guidelines.get("weekly_volume_targets")
        if isinstance(wvt, list):
            parsed = _kv_pairs_to_dict(wvt, _parse_int_tolerant)
            guidelines["weekly_volume_targets"] = {
                k: int(v)
                for k, v in parsed.items()
                if _parse_int_tolerant(v) is not None and k in ALLOWED_VOLUME_KEYS
            }
        elif isinstance(wvt, dict):
            guidelines["weekly_volume_targets"] = {
                str(k): int(_parse_int_tolerant(v))  # type: ignore[arg-type]
                for k, v in wvt.items()
                if _parse_int_tolerant(v) is not None and str(k) in ALLOWED_VOLUME_KEYS
            }

        # intensity_bands: KV array -> dict[str,str]
        ib = guidelines.get("intensity_bands")
        if isinstance(ib, list):
            parsed = _kv_pairs_to_dict(ib, lambda x: x)
            guidelines["intensity_bands"] = {k: (str(v) if v is not None else "") for k, v in parsed.items()}
        elif isinstance(ib, dict):
            guidelines["intensity_bands"] = {str(k): (str(v) if v is not None else "") for k, v in ib.items()}

        # per_workout_targets: keep only allowed fields and normalize
        pwt = guidelines.get("per_workout_targets")
        if isinstance(pwt, dict):
            number = _parse_int_tolerant(pwt.get("number_of_exercises"))
            set_range = pwt.get("set_range")
            sr_out: Optional[List[int]] = None
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
    available_exercises: List[Dict[str, Any]],
) -> OutlineSpec:
    """Generate high-level plan outline using LLM."""
    logger = logging.getLogger(__name__)
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
                                            "value": {"type": "number"}
                                        },
                                        "required": ["key", "value"]
                                    }
                                },
                                "intensity_bands": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {"type": "string"}
                                        },
                                        "required": ["key", "value"]
                                    }
                                },
                                "per_workout_targets": {
                                    "type": "object",
                                    "properties": {
                                        "number_of_exercises": {"type": "number"},
                                        "set_range": {
                                            "type": "array",
                                            "items": {"type": "number"},
                                            "minItems": 2,
                                            "maxItems": 2
                                        }
                                    }
                                },
                                "focus_areas": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "exercise_categories_allowed": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            }
                        },
                    },
                    "required": ["name", "weeks_count", "guidelines"]
                }
            }
        },
        "required": ["name", "mesocycles"]
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
    """Generate a training plan using staged pipeline only."""
    from ..config import Settings

    settings = Settings()
    available_exercises = await _get_available_exercises(settings)
    plan, _ = await _generate_staged_plan(user_data, available_exercises)
    return plan


async def generate_training_plan_with_rationale(user_data: UserDataInput) -> tuple[TrainingPlan, Optional[str]]:
    """Generate a training plan (staged) and return rationale JSON string if available."""
    from ..config import Settings

    settings = Settings()
    available_exercises = await _get_available_exercises(settings)
    plan, diagnostics = await _generate_staged_plan(user_data, available_exercises)
    rationale_json: Optional[str] = None
    if diagnostics and diagnostics.plan_rationale is not None:
        try:
            data = diagnostics.plan_rationale.model_dump()
        except Exception:
            data = getattr(diagnostics.plan_rationale, "__dict__", None)
        if data is not None:
            import json as _json
            rationale_json = _json.dumps(data, ensure_ascii=False, indent=2)
    return plan, rationale_json


async def generate_training_plan_with_summary(user_data: UserDataInput) -> tuple[TrainingPlan, Optional[str]]:
    """Generate a training plan (staged) and return concise summary if available."""
    from ..config import Settings

    settings = Settings()
    available_exercises = await _get_available_exercises(settings)
    plan, diagnostics = await _generate_staged_plan(user_data, available_exercises)
    summary = diagnostics.plan_summary if diagnostics else None
    return plan, summary
