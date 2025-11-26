import logging
import os
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class WorkoutCalculator:
    @staticmethod
    async def get_true_1rm_from_user_max(user_max: Dict) -> Optional[float]:
        """Вычисляет 1ПМ на основе пользовательского максимума."""
        if not user_max:
            return None
        max_weight = user_max.get("max_weight")
        rep_max = user_max.get("rep_max")
        if max_weight is None or rep_max is None:
            return None
        # Формула Эпли: 1ПМ = вес * (1 + 0.0333 * повторения)
        return max_weight * (1 + 0.0333 * rep_max)

    async def _get_base_candidates(self) -> list[str]:
        candidates: list[str] = []
        um_env = os.getenv("USER_MAX_SERVICE_URL")
        if um_env:
            candidates.append(um_env.rstrip("/"))
        gw_env = os.getenv("GATEWAY_URL")
        if gw_env:
            candidates.append(gw_env.rstrip("/"))
        seen = set()
        unique: list[str] = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    async def _fetch_user_maxes(self, exercise_ids: List[int]) -> List[Dict]:
        if not exercise_ids:
            return []
        headers = {"Content-Type": "application/json"}
        # Inject service auth if available
        svc_token = os.getenv("SERVICE_TOKEN") or os.getenv("USER_MAX_SERVICE_TOKEN")
        if svc_token:
            headers["Authorization"] = f"Bearer {svc_token}"
        bases = await self._get_base_candidates()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for base in bases:
                try:
                    url = f"{base}/user-max/bulk"
                    payload = [{"exercise_id": ex_id} for ex_id in exercise_ids]
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    if isinstance(data, list) and data:
                        return data
                except Exception as e:
                    logger.error(f"Failed to fetch user maxes from {base}: {e}")
                    continue

        # Fallback: generate mock user maxes
        logger.warning("All user-max services failed. Generating mock user maxes")
        return [
            {
                "id": idx + 1000,
                "exercise_id": ex_id,
                "max_weight": 100.0,
                "rep_max": 5,
                "date": "2025-01-01",
            }
            for idx, ex_id in enumerate(exercise_ids)
        ]

    async def _ensure_exercises_present(self, exercise_ids: set[int]) -> None:
        if not exercise_ids:
            return

        bases: list[str] = []
        ex_env = os.getenv("EXERCISES_SERVICE_URL")
        if ex_env:
            bases.append(ex_env.rstrip("/"))
        gw_env = os.getenv("GATEWAY_URL")
        if gw_env:
            bases.append(gw_env.rstrip("/"))

        async with httpx.AsyncClient(timeout=10.0) as client:
            for ex_id in exercise_ids:
                found = False
                for base in bases:
                    try:
                        url = f"{base}/exercises/definitions/{ex_id}"
                        headers = {"Content-Type": "application/json"}
                        response = await client.get(url, headers=headers)
                        if response.status_code == 200:
                            found = True
                            break
                    except Exception:
                        continue
                if not found:
                    logger.warning(f"Exercise definition id={ex_id} not found via remote services")
                    continue
        return

    def _apply_normalization(self, effective_1rms: dict[int, float], value: Optional[float], unit: Optional[str]):
        if value is None or unit is None:
            return
        if unit == "percentage":
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm * (1 + value / 100.0)
        elif unit == "absolute":
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm + value
