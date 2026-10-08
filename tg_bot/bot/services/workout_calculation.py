import json
import logging
from pathlib import Path

from bot.services.rpe_calculations import get_intensity

logger = logging.getLogger(__name__)

class WorkoutCalculator:
    _rpe_table = None

    @classmethod
    def get_rpe_table(cls) -> dict[int, dict[int, int]]:
        if cls._rpe_table is None:
            rpe_file = Path(__file__).parent / "rpe_table.json"
            try:
                with open(rpe_file, "r") as f:
                    raw_table = json.load(f)
                
                # Convert string keys to integers
                parsed_table = {}
                for intensity, efforts in raw_table.items():
                    parsed_efforts = {int(k): v for k, v in efforts.items()}
                    parsed_table[int(intensity)] = parsed_efforts
                    
                cls._rpe_table = parsed_table
            except Exception as e:
                logger.error(f"Failed to load RPE table: {e}")
                cls._rpe_table = {}
        return cls._rpe_table

    @classmethod
    def calculate_true_1rm(cls, weight: float, reps: int, rpe: float = 10.0) -> float | None:
        if weight is None or reps is None or rpe is None:
            return None

        table = cls.get_rpe_table()
        if not table:
            return None

        try:
            intensity = get_intensity(table, volume=reps, effort=rpe)
        except Exception as e:
            logger.warning(f"Intensity not found for volume {reps}, effort {rpe}: {e}")
            return None

        if intensity is None:
            return None

        try:
            intensity_f = float(intensity)
        except (TypeError, ValueError):
            return None

        if intensity_f == 0.0:
            return None

        true_1rm = (float(weight) / intensity_f) * 100.0
        return round(true_1rm, 1)

    @classmethod
    def get_true_1rm_from_user_max(cls, user_max) -> float | None:
        """Calculates 1RM based on UserMax model instance"""
        if not user_max or user_max.max_weight is None or user_max.rep_max is None:
            return None
        return cls.calculate_true_1rm(
            weight=float(user_max.max_weight),
            reps=user_max.rep_max,
            rpe=10.0,
        )

    @classmethod
    def apply_normalization(cls, effective_1rms: dict[int, float], value: float | None, unit: str | None):
        """Applies normalization values (e.g., from a microcycle) to the effective 1RMs"""
        if value is None or unit is None:
            return
        if unit == "percentage":
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm * (1 + value / 100.0)
        elif unit == "absolute":
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm + value
