"""RPE table loading, validation, and calculation engine."""

import json
import logging
import math
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .config import settings
from .rpe_calculations import (
    EffortNotFoundError,
    IntensityNotFoundError,
    VolumeNotFoundError,
    get_effort,
    get_intensity,
    get_volume,
)

logger = logging.getLogger(__name__)


def _normalize_int_keys(data: Any) -> Any:
    """Recursively convert dictionary string keys to integer keys where possible."""
    if isinstance(data, Mapping):
        out: dict[Any, Any] = {}
        for k, v in data.items():
            try:
                ik = int(k)
            except (TypeError, ValueError):
                ik = k
            out[ik] = _normalize_int_keys(v)
        return out
    return data


def round_to_step(value: float | int, step: float | int, mode: str = "nearest") -> float:
    """Round a numeric value to the nearest step increment using the given mode.

    Modes:
      - 'floor': round down to nearest step
      - 'ceil': round up to nearest step
      - 'nearest': round to closest step (standard)
    """
    if not math.isfinite(value):
        return float(value)
    if step <= 0 or not math.isfinite(step):
        return round(float(value), 2)

    mode_str = (mode or "nearest").lower().strip()
    # Mitigate IEEE 754 precision issues before integer rounding operations
    ratio = round(float(value) / float(step), 9)
    if mode_str == "floor":
        rounded = math.floor(ratio) * step
    elif mode_str == "ceil":
        rounded = math.ceil(ratio) * step
    else:
        rounded = round(ratio) * step
    return round(float(rounded), 2)


def validate_rpe_table(table: Mapping[Any, Any]) -> bool:
    """Validate structure and value bounds of the RPE table."""
    if not isinstance(table, Mapping) or not table:
        return False
    for intensity, efforts in table.items():
        if not isinstance(intensity, int) or isinstance(intensity, bool) or not (40 <= intensity <= 100):
            return False
        if not isinstance(efforts, Mapping) or not efforts:
            return False

        for effort, reps in efforts.items():
            if not isinstance(effort, int) or isinstance(effort, bool) or not (1 <= effort <= 10):
                return False
            if not isinstance(reps, int) or isinstance(reps, bool) or not (1 <= reps <= 100):
                return False
    return True


def load_rpe_table() -> dict[int, dict[int, int]]:
    """Load RPE table from JSON string or file."""
    default_json_path = Path(__file__).resolve().parent.parent / "rpe_table.json"
    json_str = settings.RPE_TABLE_JSON or os.getenv("RPE_TABLE_JSON")
    json_path_str = settings.RPE_TABLE_PATH or os.getenv("RPE_TABLE_PATH")
    target_path = Path(json_path_str) if json_path_str else default_json_path

    if json_str:
        try:
            data = json.loads(json_str)
            logger.info("Loaded RPE table from environment variable")
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in RPE_TABLE_JSON environment variable: %s", e)
            raise RuntimeError("Invalid JSON in RPE_TABLE_JSON environment variable") from e
    else:
        if not target_path.is_file():
            if default_json_path.is_file():
                logger.warning(
                    "RPE table file not found at %s, falling back to default %s",
                    target_path,
                    default_json_path,
                )
                target_path = default_json_path
            else:
                logger.error("RPE table file not found at %s", target_path)
                raise RuntimeError(f"RPE table file not found at {target_path}")
        try:
            with open(target_path, encoding="utf-8") as f:
                data = json.load(f)
                logger.info("Loaded RPE table from file: %s", target_path)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Error reading RPE table from %s: %s", target_path, e)
            raise RuntimeError(f"Error reading RPE table from {target_path}") from e

    try:
        normalized: dict[int, dict[int, int]] = _normalize_int_keys(data)
        return normalized
    except Exception as e:
        logger.error("Error normalizing RPE table keys: %s", e)
        raise RuntimeError("Error normalizing RPE table keys") from e


_RPE_TABLE_CACHE: dict[int, dict[int, int]] | None = None


def clear_rpe_table_cache() -> None:
    """Clear cached RPE table to allow reloading."""
    global _RPE_TABLE_CACHE
    _RPE_TABLE_CACHE = None


def get_rpe_table(force_reload: bool = False) -> dict[int, dict[int, int]]:
    """Retrieve cached RPE table, initializing and validating on first call."""
    global _RPE_TABLE_CACHE
    if _RPE_TABLE_CACHE is None or force_reload:
        table = load_rpe_table()
        if not validate_rpe_table(table):
            raise RuntimeError("Invalid RPE table structure")
        _RPE_TABLE_CACHE = table
    return _RPE_TABLE_CACHE


def calculate_rpe_set_values(
    table: Mapping[int, Mapping[int, int]],
    *,
    intensity: float | int | None = None,
    effort: float | int | None = None,
    volume: int | float | None = None,
    max_weight: float | None = None,
    rounding_step: float = 2.5,
    rounding_mode: str = "nearest",
) -> tuple[int | None, float | None, int | None, float | None]:
    """Compute missing parameter among (intensity, effort, volume) and calculate target weight.

    Returns tuple of (intensity, effort, volume, weight).
    """
    if not table:
        return None, None, None, None

    provided = [p is not None for p in (intensity, effort, volume)]
    if sum(provided) >= 2:
        if intensity is not None and effort is not None and volume is None:
            try:
                volume = get_volume(table, intensity=intensity, effort=effort)
            except (IntensityNotFoundError, EffortNotFoundError):
                target_intensity = int(round(intensity))
                target_effort = int(round(effort))
                if table:
                    nearest_int = min(table.keys(), key=lambda x: abs(x - target_intensity))
                    mapping = table[nearest_int]
                    if mapping:
                        nearest_eff = min(mapping.keys(), key=lambda k: abs(k - target_effort))
                        volume = mapping[nearest_eff]
                        logger.warning(
                            "Adjusted (intensity,effort)->volume using nearest match | "
                            "input=(%s,%s) -> intensity=%s effort=%s volume=%s",
                            str(intensity),
                            str(effort),
                            nearest_int,
                            nearest_eff,
                            volume,
                        )
                        intensity = nearest_int
                        effort = float(nearest_eff)

        elif volume is not None and effort is not None and intensity is None:
            try:
                intensity = get_intensity(table, volume=volume, effort=effort)
            except VolumeNotFoundError:
                candidates: list[tuple[int, int]] = []
                target_effort = int(round(effort))
                target_volume = int(round(volume))
                for i, mapping in table.items():
                    if target_effort in mapping:
                        candidates.append((i, mapping[target_effort]))
                if not candidates and table:
                    all_efforts = {eff for mapping in table.values() for eff in mapping}
                    if all_efforts:
                        closest_eff = min(all_efforts, key=lambda k: abs(k - target_effort))
                        for i, mapping in table.items():
                            if closest_eff in mapping:
                                candidates.append((i, mapping[closest_eff]))
                if candidates:
                    nearest_int, reps = min(candidates, key=lambda t: abs(t[1] - target_volume))
                    logger.warning(
                        "Adjusted (volume,effort)->intensity using nearest match | "
                        "requested_volume=%s effort=%s -> intensity=%s volume=%s",
                        str(volume),
                        str(target_effort),
                        nearest_int,
                        reps,
                    )
                    intensity = nearest_int
                    volume = reps

        elif volume is not None and intensity is not None and effort is None:
            try:
                effort = get_effort(table, volume=volume, intensity=intensity)
            except (IntensityNotFoundError, VolumeNotFoundError):
                target_intensity = int(round(intensity))
                target_volume = int(round(volume))
                if table:
                    nearest_int = min(table.keys(), key=lambda x: abs(x - target_intensity))
                    mapping = table[nearest_int]
                    if mapping:
                        nearest_eff, reps = min(mapping.items(), key=lambda kv: abs(kv[1] - target_volume))
                        logger.warning(
                            "Adjusted (intensity,volume)->effort using nearest match | "
                            "input=(%s,%s) -> intensity=%s effort=%s volume=%s",
                            str(intensity),
                            str(volume),
                            nearest_int,
                            nearest_eff,
                            reps,
                        )
                        intensity = nearest_int
                        effort = float(nearest_eff)
                        volume = reps

    weight: float | None = None
    if max_weight is not None and intensity is not None:
        raw = float(max_weight) * (float(intensity) / 100.0)
        weight = round_to_step(raw, rounding_step, rounding_mode)

    out_intensity = int(round(intensity)) if intensity is not None else None
    out_effort = float(effort) if effort is not None else None
    out_volume = int(round(volume)) if volume is not None else None
    out_weight = float(weight) if weight is not None else None

    return out_intensity, out_effort, out_volume, out_weight
