import math
from typing import Dict, Optional

class TableLookupError(Exception):
    pass

class IntensityNotFoundError(TableLookupError):
    pass

class EffortNotFoundError(TableLookupError):
    pass

class VolumeNotFoundError(TableLookupError):
    pass

def get_volume(rpe_table: Dict[int, Dict[int, int]], *, intensity: int, effort: float) -> int:
    if intensity is None or effort is None:
        return None
    effort_key = math.floor(effort)
    if intensity not in rpe_table:
        raise IntensityNotFoundError(f"Intensity {intensity} not found")
    efforts = rpe_table[intensity]
    if effort_key not in efforts:
        raise EffortNotFoundError(f"Effort {effort_key} not found for intensity {intensity}")
    return efforts[effort_key]

def get_intensity(rpe_table: Dict[int, Dict[int, int]], *, volume: int, effort: float) -> int:
    if volume is None or effort is None:
        return None
    effort_key = math.floor(effort)
    for intensity, efforts in rpe_table.items():
        if effort_key in efforts and efforts[effort_key] == volume:
            return intensity
    raise VolumeNotFoundError(f"Volume {volume} with effort {effort_key} not found")

def get_effort(rpe_table: Dict[int, Dict[int, int]], *, volume: int, intensity: int) -> float:
    if volume is None or intensity is None:
        return None
    if intensity not in rpe_table:
        raise IntensityNotFoundError(f"Intensity {intensity} not found")
    efforts = rpe_table[intensity]
    for effort, vol in efforts.items():
        if vol == volume:
            return effort
    raise VolumeNotFoundError(f"Volume {volume} not found for intensity {intensity}")
