from typing import Optional

from .rpc import get_intensity, get_rpe_table


class WorkoutCalculator:
    RPE_TABLE = None

    @classmethod
    async def _get_rpe_table(cls, headers=None):
        if cls.RPE_TABLE is None:
            cls.RPE_TABLE = await get_rpe_table(headers=headers)
        return cls.RPE_TABLE

    @classmethod
    async def calculate_true_1rm(cls, weight: float, reps: int, rpe: float = 10.0, headers=None) -> Optional[float]:
        if weight is None or reps is None or rpe is None:
            return None
        # Best-effort: warm up RPE table cache, but do not fail if unavailable
        try:
            await cls._get_rpe_table(headers=headers)
        except Exception:
            pass
        # Compute intensity via RPC with safe fallback
        try:
            intensity = await get_intensity(volume=reps, effort=rpe, headers=headers)
        except Exception:
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
    async def get_true_1rm_from_user_max(cls, user_max, headers=None) -> Optional[float]:
        if not user_max or user_max.get("max_weight") is None or user_max.get("rep_max") is None:
            return None
        return await cls.calculate_true_1rm(
            weight=float(user_max.get("max_weight")),
            reps=user_max.get("rep_max"),
            rpe=10.0,
            headers=headers,
        )
