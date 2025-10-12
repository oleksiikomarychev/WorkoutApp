import os
import logging
from typing import Iterable, Optional
from datetime import date

import httpx

logger = logging.getLogger(__name__)


class UserMaxClient:
    """Async HTTP client for pushing strength PRs into user-max-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0) -> None:
        base_env = base_url or os.getenv("USER_MAX_SERVICE_URL")
        self.base_url = (base_env or "http://user-max-service:8003").rstrip("/")
        self.timeout = timeout

    async def push_entries(self, entries: Iterable[dict]) -> None:
        payload = [self._normalize_entry(e) for e in entries if self._normalize_entry(e)]
        if not payload:
            logger.info("UserMaxClient.push_entries: no valid entries to send")
            return
        url = f"{self.base_url}/user-max/bulk"
        logger.info("UserMaxClient.push_entries: sending %d entries to %s | payload=%s", len(payload), url, payload)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("UserMaxClient.push_entries: success | status=%d response=%s", response.status_code, response.text[:200])
            except Exception as exc:
                logger.exception("UserMaxClient.push_entries failed: %s", exc)

    def _normalize_entry(self, entry: dict) -> Optional[dict]:
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
        except Exception:
            logger.warning("UserMaxClient: invalid entry discarded: %s", entry)
            return None
