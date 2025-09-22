import httpx
import logging
import asyncio
from fastapi import HTTPException
import os
logger = logging.getLogger(__name__)

async def get_exercise_by_id(exercise_id: int):
    """Fetch an exercise by ID from the exercises service"""
    base_url = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")
    if not base_url.startswith("http"):
        base_url = "http://" + base_url
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
            base_url = os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005")  # Default to service name in Docker network
        # Ensure base_url has a protocol
        if not base_url.startswith("http"):
            base_url = "http://" + base_url
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
                    timeout=5.0
                )
                if response.status_code == 200:
                    return response.json().get("valid_ids", [])
                raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Plans service unreachable: {str(e)}")

    async def get_params_workout(self, params_workout_id: int):
        """Fetch a ParamsWorkout by ID"""
        response = await self.call_rpc(
            "get_params_workout",
            {"params_workout_id": params_workout_id}
        )
        return response