from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class WorkoutCalculator:
    """Workout metrics and 1RM calculation helpers."""

    @staticmethod
    async def get_true_1rm_from_user_max(user_max: dict[str, Any] | None) -> float | None:
        """Calculate true 1RM from user max record, respecting precalculated true_1rm."""
        if not user_max:
            return None

        # If true_1rm is already precalculated, prioritize it
        true_1rm = user_max.get("true_1rm")
        if true_1rm is not None:
            try:
                return float(true_1rm)
            except (TypeError, ValueError):
                pass

        max_weight = user_max.get("max_weight")
        rep_max = user_max.get("rep_max")
        if max_weight is None:
            return None

        try:
            w = float(max_weight)
            r = int(rep_max) if rep_max is not None else 1
            if r <= 0:
                return w
            return w * (1 + 0.0333 * r)
        except (TypeError, ValueError):
            return None

    async def _get_base_candidates(self) -> list[str]:
        candidates: list[str] = []
        um_env = settings.USER_MAX_SERVICE_URL
        if um_env:
            candidates.append(um_env.rstrip("/"))

        gw_env = settings.GATEWAY_URL
        internal_secret = settings.INTERNAL_GATEWAY_SECRET
        if gw_env and internal_secret:
            candidates.append(gw_env.rstrip("/"))

        seen: set[str] = set()
        unique: list[str] = []
        for c in candidates:
            if c and not c.startswith("http"):
                c = "http://" + c
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    async def _fetch_user_maxes(self, exercise_ids: list[int], *, user_id: str) -> list[dict[str, Any]]:
        if not exercise_ids:
            return []
        headers: dict[str, str] = {"Content-Type": "application/json", "X-User-Id": user_id}

        internal_secret = settings.INTERNAL_GATEWAY_SECRET
        if internal_secret:
            headers["X-Internal-Secret"] = internal_secret

        bases = await self._get_base_candidates()
        gw_base = (settings.GATEWAY_URL or "").strip().rstrip("/")
        if gw_base and not gw_base.startswith("http"):
            gw_base = "http://" + gw_base

        async with httpx.AsyncClient(timeout=10.0) as client:
            for base in bases:
                try:
                    if gw_base and base == gw_base:
                        url = f"{base}/api/v1/user-max/by-exercises"
                    else:
                        url = f"{base}/user-max/by-exercises"
                    response = await client.get(url, params={"exercise_ids": exercise_ids}, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    if isinstance(data, list) and data:
                        return data
                except Exception as e:
                    logger.error("Failed to fetch user maxes from %s: %s", base, e)
                    continue

        logger.error("All user-max services failed. Aborting workout calculation.")
        raise RuntimeError("Failed to fetch user maxes from all configured services")

    async def _ensure_exercises_present(self, exercise_ids: set[int]) -> None:
        if not exercise_ids:
            return

        bases: list[str] = []
        if settings.EXERCISES_SERVICE_URL:
            bases.append(settings.EXERCISES_SERVICE_URL.rstrip("/"))
        if settings.GATEWAY_URL:
            bases.append(settings.GATEWAY_URL.rstrip("/"))

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
                    logger.warning("Exercise definition id=%s not found via remote services", ex_id)
                    continue

    def _apply_normalization(
        self,
        effective_1rms: dict[int, float],
        value: float | None,
        unit: str | None,
    ) -> None:
        if value is None or unit is None:
            return
        if unit == "percentage":
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm * (1 + value / 100.0)
        elif unit == "absolute":
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm + value
