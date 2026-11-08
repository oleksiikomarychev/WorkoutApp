"""Low-level lookup functions for RPE table."""

from collections.abc import Mapping


class TableLookupError(Exception):
    """Base exception for RPE table lookup errors."""


class IntensityNotFoundError(TableLookupError):
    """Raised when the specified intensity percentage does not exist in the table."""


class EffortNotFoundError(TableLookupError):
    """Raised when the specified RPE effort value does not exist for the given intensity."""


class VolumeNotFoundError(TableLookupError):
    """Raised when the specified repetition volume does not match the criteria."""


def get_volume(
    rpe_table: Mapping[int, Mapping[int, int]],
    *,
    intensity: float | int | None,
    effort: float | int | None,
) -> int | None:
    """Find repetition count (volume) for given intensity and effort."""
    if intensity is None or effort is None:
        return None
    intensity_key = int(round(intensity))
    effort_key = int(round(effort))
    if intensity_key not in rpe_table:
        raise IntensityNotFoundError(f"Intensity {intensity_key} not found")
    efforts = rpe_table[intensity_key]
    if effort_key not in efforts:
        raise EffortNotFoundError(f"Effort {effort_key} not found for intensity {intensity_key}")
    return efforts[effort_key]


def get_intensity(
    rpe_table: Mapping[int, Mapping[int, int]],
    *,
    volume: int | float | None,
    effort: float | int | None,
) -> int | None:
    """Find intensity percentage for given repetition count (volume) and effort."""
    if volume is None or effort is None:
        return None
    effort_key = int(round(effort))
    volume_key = int(round(volume))
    for intensity, efforts in rpe_table.items():
        if effort_key in efforts and efforts[effort_key] == volume_key:
            return intensity
    raise VolumeNotFoundError(f"Volume {volume_key} with effort {effort_key} not found")


def get_effort(
    rpe_table: Mapping[int, Mapping[int, int]],
    *,
    volume: int | float | None,
    intensity: float | int | None,
) -> float | None:
    """Find RPE effort value for given repetition count (volume) and intensity."""
    if volume is None or intensity is None:
        return None
    intensity_key = int(round(intensity))
    volume_key = int(round(volume))
    if intensity_key not in rpe_table:
        raise IntensityNotFoundError(f"Intensity {intensity_key} not found")
    efforts = rpe_table[intensity_key]
    for effort, vol in efforts.items():
        if vol == volume_key:
            return float(effort)
    raise VolumeNotFoundError(f"Volume {volume_key} not found for intensity {intensity_key}")
