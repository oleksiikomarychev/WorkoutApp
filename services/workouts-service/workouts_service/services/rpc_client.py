import logging
import os

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def get_exercise_by_id(exercise_id: int):
    base_url = os.getenv("EXERCISES_SERVICE_URL") or os.getenv("GATEWAY_URL")
    if not base_url:
        logger.error("EXERCISES_SERVICE_URL or GATEWAY_URL must be set")
        raise HTTPException(status_code=503, detail="Exercises service URL not configured")
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    url = f"{base_url}/exercises/{exercise_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from exercises-service: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Exercises service error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Request to exercises-service failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")


class PlansServiceRPC:
    def __init__(self, base_url: str = ""):
        if not base_url:
            base_url = os.getenv("PLANS_SERVICE_URL") or os.getenv("GATEWAY_URL")
        if not base_url:
            logger.error("PLANS_SERVICE_URL or GATEWAY_URL must be set")
            raise HTTPException(status_code=503, detail="Plans service URL not configured")

        if not base_url.startswith("http"):
            base_url = "https://" + base_url
        self.base_url = base_url

    async def get_calendar_plan(self, calendar_plan_id: int):
        try:
            url = f"{self.base_url}/plans/calendar-plans/{calendar_plan_id}"
            logger.debug(f"Fetching calendar plan from: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from plans-service: {str(e)}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Plans service error: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request to plans-service failed: {str(e)}")
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
            raise HTTPException(status_code=503, detail=f"Plans service unreachable: {str(e)}")

    async def get_params_workout(self, params_workout_id: int):
        response = await self.call_rpc("get_params_workout", {"params_workout_id": params_workout_id})
        return response


class RpeServiceRPC:
    def __init__(self, base_url: str = ""):
        if not base_url:
            base_url = os.getenv("RPE_SERVICE_URL") or os.getenv("GATEWAY_URL")
        if not base_url:
            logger.error("RPE_SERVICE_URL or GATEWAY_URL must be set")
            raise HTTPException(status_code=503, detail="RPE service URL not configured")
        if not base_url.startswith("http"):
            base_url = "https://" + base_url
        self.base_url = base_url.rstrip("/")

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
    ) -> dict:
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
                gw = os.getenv("GATEWAY_URL")
                if gw:
                    if not gw.startswith("http"):
                        gw = "https://" + gw
                    target_base = gw.rstrip("/")

            send_headers = dict(headers or {})
            if not send_headers.get("Authorization"):
                svc_token = os.getenv("SERVICE_TOKEN") or os.getenv("RPE_SERVICE_TOKEN")
                if svc_token:
                    send_headers["Authorization"] = f"Bearer {svc_token}"

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
            logger.error(f"HTTP error from rpe-service: {e.response.status_code} {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"RPE service error: {e.response.text}",
            )
        except httpx.RequestError as e:
            logger.error(f"Request to rpe-service failed: {str(e)}")
            raise HTTPException(status_code=503, detail="RPE service unavailable")
