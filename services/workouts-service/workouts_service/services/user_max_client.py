from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class UserMaxClient:
    """Client for pushing workout max records to user-max-service."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        base_env = base_url or settings.USER_MAX_SERVICE_URL
        resolved = (base_env or "http://user-max-service:8003").rstrip("/")
        if resolved and not resolved.startswith("http"):
            resolved = "http://" + resolved
        self.base_url = resolved
        self.timeout = timeout

    async def push_entries(self, entries: Iterable[dict[str, Any]], user_id: str) -> None:
        payload = [self._normalize_entry(e) for e in entries if self._normalize_entry(e)]
        if not payload:
            logger.info("UserMaxClient.push_entries: no valid entries to send")
            return

        internal_secret = settings.INTERNAL_GATEWAY_SECRET
        gateway_url = (settings.GATEWAY_URL or "").strip().rstrip("/")
        if gateway_url and not gateway_url.startswith("http"):
            gateway_url = "http://" + gateway_url

        if gateway_url and self.base_url == gateway_url:
            url = f"{self.base_url}/api/v1/user-max/bulk"
        else:
            url = f"{self.base_url}/user-max/bulk"

        headers = {"X-User-Id": user_id}
        if internal_secret:
            headers["X-Internal-Secret"] = internal_secret

        logger.info(
            "UserMaxClient.push_entries: sending %d entries to %s for user %s",
            len(payload),
            url,
            user_id,
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(
                    "UserMaxClient.push_entries: success | status=%d",
                    response.status_code,
                )
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.exception("UserMaxClient.push_entries failed: %s", exc)

    def _normalize_entry(self, entry: dict[str, Any]) -> dict[str, Any] | None:
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
