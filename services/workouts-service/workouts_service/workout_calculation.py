import logging
import os

import httpx

logger = logging.getLogger(__name__)


class WorkoutCalculator:
    @staticmethod
    async def get_true_1rm_from_user_max(user_max: dict) -> float | None:
        if not user_max:
            return None
        max_weight = user_max.get("max_weight")
        rep_max = user_max.get("rep_max")
        if max_weight is None or rep_max is None:
            return None

        return max_weight * (1 + 0.0333 * rep_max)

    async def _get_base_candidates(self) -> list[str]:
        candidates: list[str] = []
        um_env = os.getenv("USER_MAX_SERVICE_URL")
        if um_env:
            candidates.append(um_env.rstrip("/"))
        else:
            candidates.append("http://user-max-service:8003")
        gw_env = os.getenv("GATEWAY_URL")
        internal_secret = (os.getenv("INTERNAL_GATEWAY_SECRET") or os.getenv("GATEWAY_INTERNAL_SECRET") or "").strip()
        if gw_env and internal_secret:
            candidates.append(gw_env.rstrip("/"))
        seen = set()
        unique: list[str] = []
        for c in candidates:
            if c and not c.startswith("http"):
                c = "http://" + c
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    async def _fetch_user_maxes(self, exercise_ids: list[int], *, user_id: str) -> list[dict]:
        if not exercise_ids:
            return []
        headers = {"Content-Type": "application/json", "X-User-Id": user_id}

        internal_secret = (os.getenv("INTERNAL_GATEWAY_SECRET") or os.getenv("GATEWAY_INTERNAL_SECRET") or "").strip()
        if internal_secret:
            headers["X-Internal-Secret"] = internal_secret

        svc_token = os.getenv("SERVICE_TOKEN") or os.getenv("USER_MAX_SERVICE_TOKEN")
        if svc_token:
            headers["Authorization"] = f"Bearer {svc_token}"
        bases = await self._get_base_candidates()
        gw_env = (os.getenv("GATEWAY_URL") or "").strip()
        gw_base = gw_env.rstrip("/")
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
                    logger.error(f"Failed to fetch user maxes from {base}: {e}")
                    continue

        logger.error("All user-max services failed. Aborting workout calculation.")
        raise RuntimeError("Failed to fetch user maxes from all configured services")

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

    def _apply_normalization(self, effective_1rms: dict[int, float], value: float | None, unit: str | None):
        if value is None or unit is None:
            return
        if unit == "percentage":
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm * (1 + value / 100.0)
        elif unit == "absolute":
            for exercise_id, current_1rm in effective_1rms.items():
                effective_1rms[exercise_id] = current_1rm + value
