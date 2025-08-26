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
    
    @classmethod
    def calculate_true_1rm(cls, weight: float, reps: int, rpe: float = 10.0) -> Optional[float]:
        """
        Рассчитывает истинный 1ПМ из веса и количества повторений при заданном RPE.
        
        Args:
            weight: Вес в подходе (кг)
            reps: Количество повторений
            rpe: RPE (Rate of Perceived Exertion), по умолчанию 10.0
            
        Returns:
            Истинный 1ПМ в кг или None если не удалось рассчитать
            
        Example:
            100кг x 4 повт при 10 RPE = 84% интенсивности
            1ПМ = (100 / 84) * 100 ≈ 119кг
        """
        if weight is None or reps is None or rpe is None:
            return None
            
        # Найти интенсивность по количеству повторений и RPE
        intensity = cls.get_intensity(reps, rpe)
        if intensity is None:
            return None
            
        # Рассчитать истинный 1ПМ: 1ПМ = (Вес в подходе / Процент от 1ПМ) * 100
        true_1rm = (weight / intensity) * 100
        return round(true_1rm, 1)
    
    @classmethod
    def get_true_1rm_from_user_max(cls, user_max) -> Optional[float]:
        """
        Получает истинный 1ПМ из записи UserMax.
        
        Args:
            user_max: Объект UserMax с полями max_weight и rep_max
            
        Returns:
            Истинный 1ПМ в кг
        """
        if not user_max or not hasattr(user_max, 'max_weight') or not hasattr(user_max, 'rep_max'):
            return None
            
        return cls.calculate_true_1rm(
            weight=float(user_max.max_weight),
            reps=user_max.rep_max,
            rpe=10.0  # Предполагаем максимальное усилие
        )