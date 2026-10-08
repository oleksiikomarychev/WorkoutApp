"""Low-level lookup functions for RPE table."""

import math


class TableLookupError(Exception):
    """Base exception for RPE table lookup errors."""


class IntensityNotFoundError(TableLookupError):
    """Raised when the specified intensity percentage does not exist in table."""


class EffortNotFoundError(TableLookupError):
    """Raised when the specified RPE effort value does not exist for the intensity."""


class VolumeNotFoundError(TableLookupError):
    """Raised when the specified repetition volume does not match the criteria."""


def get_volume(
    rpe_table: dict[int, dict[int, int]],
    *,
    intensity: int | float | None,
    effort: float | int | None,
) -> int | None:
    """Find repetition count (volume) for given intensity and effort."""
    if intensity is None or effort is None:
        return None
    intensity_key = int(round(intensity))
    effort_key = int(math.floor(effort))
    if intensity_key not in rpe_table:
        raise IntensityNotFoundError(f"Intensity {intensity_key} not found")
    efforts = rpe_table[intensity_key]
    if effort_key not in efforts:
        raise EffortNotFoundError(f"Effort {effort_key} not found for intensity {intensity_key}")
    return efforts[effort_key]


def get_intensity(
    rpe_table: dict[int, dict[int, int]],
    *,
    volume: int | None,
    effort: float | int | None,
) -> int | None:
    """Find intensity percentage for given repetition count (volume) and effort."""
    if volume is None or effort is None:
        return None
    effort_key = int(math.floor(effort))
    for intensity, efforts in rpe_table.items():
        if effort_key in efforts and efforts[effort_key] == volume:
            return intensity
    raise VolumeNotFoundError(f"Volume {volume} with effort {effort_key} not found")


def get_effort(
    rpe_table: dict[int, dict[int, int]],
    *,
    volume: int | None,
    intensity: int | float | None,
) -> float | None:
    """Find RPE effort value for given repetition count (volume) and intensity."""
    if volume is None or intensity is None:
        return None
    intensity_key = int(round(intensity))
    if intensity_key not in rpe_table:
        raise IntensityNotFoundError(f"Intensity {intensity_key} not found")
    efforts = rpe_table[intensity_key]
    for effort, vol in efforts.items():
        if vol == volume:
            return float(effort)
    raise VolumeNotFoundError(f"Volume {volume} not found for intensity {intensity_key}")

