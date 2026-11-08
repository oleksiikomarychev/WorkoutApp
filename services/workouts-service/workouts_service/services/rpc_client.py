from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException

from ..config import settings

logger = logging.getLogger(__name__)


def _normalize_url(url: str | None, default: str) -> str:
    resolved = (url or default).strip().rstrip("/")
    if not resolved.startswith("http://") and not resolved.startswith("https://"):
        resolved = f"http://{resolved}"
    return resolved


async def get_exercise_by_id(exercise_id: int) -> dict[str, Any]:
    base_url = _normalize_url(settings.EXERCISES_SERVICE_URL, "http://exercises-service:8002")
    url = f"{base_url}/exercises/{exercise_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error from exercises-service: %s", e)
        raise HTTPException(status_code=e.response.status_code, detail=f"Exercises service error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error("Request to exercises-service failed: %s", e)
        raise HTTPException(status_code=503, detail="Service unavailable")


class PlansServiceRPC:
    """RPC client for plans-service."""

    def __init__(self, base_url: str = "") -> None:
        self.base_url = _normalize_url(base_url or settings.PLANS_SERVICE_URL, "http://plans-service:8005")

    async def get_calendar_plan(self, calendar_plan_id: int) -> dict[str, Any]:
        try:
            url = f"{self.base_url}/plans/calendar-plans/{calendar_plan_id}"
            logger.debug("Fetching calendar plan from: %s", url)
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error from plans-service: %s", e)
            raise HTTPException(status_code=e.response.status_code, detail=f"Plans service error: {e.response.text}")
        except httpx.RequestError as e:
            logger.error("Request to plans-service failed: %s", e)
            raise HTTPException(status_code=503, detail="Service unavailable")

    async def validate_microcycle_ids(self, microcycle_ids: list[int]) -> list[int]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/microcycles/validate",
                    json={"microcycle_ids": microcycle_ids},
                    timeout=5.0,
                )
                if response.status_code == 200:
                    return response.json().get("valid_ids", [])
                raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Plans service unreachable: {e}")


class RpeServiceRPC:
    """RPC client for rpe-service."""

    def __init__(self, base_url: str = "") -> None:
        self.base_url = _normalize_url(base_url or settings.RPE_SERVICE_URL, "http://rpe-service:8001")

    async def compute(
        self,
        *,
        intensity: float | None = None,
        effort: float | None = None,
        volume: int | None = None,
        max_weight: float | None = None,
        user_max_id: int | None = None,
        rounding_step: float = 2.5,
        rounding_mode: str = "nearest",
        headers: dict[str, str] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "intensity": intensity,
            "effort": effort,
            "volume": volume,
            "max_weight": max_weight,
            "user_max_id": user_max_id,
            "rounding_step": rounding_step,
            "rounding_mode": rounding_mode,
        }
        try:
            target_base = self.base_url
            if headers and headers.get("Authorization"):
                gw = settings.GATEWAY_URL
                if gw:
                    target_base = _normalize_url(gw, "http://gateway:8000")

            send_headers = dict(headers or {})
            if user_id and not send_headers.get("X-User-Id"):
                send_headers["X-User-Id"] = user_id

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{target_base}/rpe/compute",
                    json=payload,
                    headers=send_headers,
                    timeout=10.0,
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error from rpe-service: %s %s", e.response.status_code, e.response.text)
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"RPE service error: {e.response.text}",
            )
        except httpx.RequestError as e:
            logger.error("Request to rpe-service failed: %s", e)
            raise HTTPException(status_code=503, detail="RPE service unavailable")
