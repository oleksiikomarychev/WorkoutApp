from typing import Optional

from .rpc import get_intensity, get_rpe_table


class WorkoutCalculator:
    RPE_TABLE = None

    @classmethod
    async def _get_rpe_table(cls):
        if cls.RPE_TABLE is None:
            cls.RPE_TABLE = await get_rpe_table()
        return cls.RPE_TABLE

    @classmethod
    async def calculate_true_1rm(cls, weight: float, reps: int, rpe: float = 10.0) -> Optional[float]:
        if weight is None or reps is None or rpe is None:
            return None
        rpe_table = await cls._get_rpe_table()
        intensity = await get_intensity(volume=reps, effort=rpe)
        if intensity is None:
            return None
        true_1rm = (weight / intensity) * 100
        return round(true_1rm, 1)

    @classmethod
    async def get_true_1rm_from_user_max(cls, user_max) -> Optional[float]:
        if not user_max or user_max.get("max_weight") is None or user_max.get("rep_max") is None:
            return None
        return await cls.calculate_true_1rm(
            weight=float(user_max.get("max_weight")),
            reps=user_max.get("rep_max"),
            rpe=10.0,
        )
