from typing import Dict, Optional, Union
from app.config.prompts import RPE_TABLE
import math

class WorkoutCalculator:    
    RPE_TABLE = RPE_TABLE
    
    @classmethod
    def get_volume(cls, intensity: int, effort: float) -> Union[int, str, None]:
        if intensity is None or effort is None:
            return None
        # Округление усилия вниз
        effort_key = math.floor(effort)
        return cls.RPE_TABLE.get(intensity, {}).get(effort_key, None)

    @classmethod
    def get_intensity(cls, volume: int, effort: float) -> Union[int, str, None]:
        if volume is None or effort is None:
            return None
        effort_key = math.floor(effort)
        for intensity, efforts in cls.RPE_TABLE.items():
            if effort_key in efforts and efforts[effort_key] == volume:
                return intensity
        return None

    @classmethod
    def get_effort(cls, volume: int, intensity: int) -> Union[float, str, None]:
        if volume is None or intensity is None:
            return None
        # Поиск effort по volume и intensity
        efforts = cls.RPE_TABLE.get(intensity, {})
        for effort, vol in efforts.items():
            if vol == volume:
                return effort
        return None