from typing import Dict, Optional, Union
from app.config.prompts import RPE_TABLE

class WorkoutCalculator:
    """Класс для расчета параметров тренировок"""
    
    RPE_TABLE = RPE_TABLE
    
    @staticmethod
    def round_effort(effort: float) -> float:
        """Округляет усилие до ближайшего 0.5"""
        return round(effort * 2) / 2
    
    @staticmethod
    def round_intensity(intensity: int) -> int:
        """Округляет интенсивность до ближайшего 5%"""
        return round(intensity / 5) * 5
    
    @classmethod
    def get_volume(cls, intensity: int, effort: float) -> Union[int, str, None]:
        """Рассчитывает объем тренировки на основе интенсивности и усилия"""
        if intensity is None or effort is None:
            return None
            
        rounded_intensity = cls.round_intensity(intensity)
        rounded_intensity = max(60, min(100, rounded_intensity))
        
        rounded_effort = cls.round_effort(effort)
        rounded_effort = max(6, min(10, rounded_effort))
        
        try:
            intensity_key = min(
                cls.RPE_TABLE.keys(), 
                key=lambda x: abs(x - rounded_intensity)
            )
            
            effort_key = min(
                cls.RPE_TABLE[intensity_key].keys(), 
                key=lambda x: abs(x - rounded_effort)
            )
            
            return cls.RPE_TABLE[intensity_key].get(effort_key, None)
        except (KeyError, ValueError):
            return None
    
    @staticmethod
    def calculate_weight(max_weight: float, intensity: int) -> Optional[float]:
        """Рассчитывает вес на основе максимума и интенсивности"""
        if max_weight is None or intensity is None:
            return None
        return round(max_weight * (intensity / 100.0), 2)
