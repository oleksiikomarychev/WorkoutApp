import logging
import os
from collections.abc import Iterable
from datetime import date

import httpx

logger = logging.getLogger(__name__)


class UserMaxClient:
    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        base_env = base_url or os.getenv("USER_MAX_SERVICE_URL")
        self.base_url = (base_env or "http://user-max-service:8003").rstrip("/")
        self.timeout = timeout

    async def push_entries(self, entries: Iterable[dict], user_id: str) -> None:
        payload = [self._normalize_entry(e) for e in entries if self._normalize_entry(e)]
        if not payload:
            logger.info("UserMaxClient.push_entries: no valid entries to send")
            return
        url = f"{self.base_url}/user-max/bulk"
        headers = {"X-User-Id": user_id}
        logger.info(
            "UserMaxClient.push_entries: sending %d entries to %s for user %s",
            len(payload),
            url,
            user_id,
        )
        logger.debug(
            "UserMaxClient.push_entries payload=%s",
            payload,
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(
                    "UserMaxClient.push_entries: success | status=%d",
                    response.status_code,
                )
                logger.debug(
                    "UserMaxClient.push_entries response_text=%s",
                    response.text[:200],
                )
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.exception("UserMaxClient.push_entries failed: %s", exc)

    def _normalize_entry(self, entry: dict) -> dict | None:
        try:
            exercise_id = int(entry["exercise_id"])
            max_weight = float(entry["max_weight"])
            rep_max = int(entry["rep_max"])
            dt = entry.get("date")
            if isinstance(dt, date):
                date_str = dt.isoformat()
            elif isinstance(dt, str):
                date_str = dt
            else:
                return None
            return {
                "exercise_id": exercise_id,
                "max_weight": max_weight,
                "rep_max": rep_max,
                "date": date_str,
            }
        except (TypeError, ValueError, KeyError) as exc:
            logger.warning("UserMaxClient: invalid entry discarded: %s (error: %s)", entry, exc)
            return None
