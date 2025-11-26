import os

import httpx
from fastapi import APIRouter, HTTPException

USER_MAX_SERVICE_URL = os.getenv("USER_MAX_SERVICE_URL") or os.getenv("GATEWAY_URL")
if not USER_MAX_SERVICE_URL:
    raise RuntimeError("USER_MAX_SERVICE_URL or GATEWAY_URL must be set")
if not USER_MAX_SERVICE_URL.startswith(("http://", "https://")):
    USER_MAX_SERVICE_URL = f"https://{USER_MAX_SERVICE_URL}"

router = APIRouter()


async def get_true_1rm(user_max_id: int) -> float:
    """Get true 1RM from user-max-service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{USER_MAX_SERVICE_URL}/api/v1/user-maxes/calculate-true-1rm",
                json={"user_max_id": user_max_id},
                timeout=3,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get true 1RM: {str(e)}")


async def get_user_maxes_by_exercises(exercise_ids: list[int]) -> list[dict]:
    """Get UserMax records by exercise IDs via user-max-service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{USER_MAX_SERVICE_URL}/api/v1/user-maxes/by-exercises",
                json={"exercise_ids": exercise_ids},
                timeout=3,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UserMax records: {str(e)}")


@router.get("/by_exercise/{exercise_id}")
async def get_user_max_by_exercise(exercise_id: int):
    try:
        # Placeholder: implement actual RPC call
        return {"exercise_id": exercise_id, "max_weight": 100.0, "rep_max": 5}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user max for exercise {exercise_id}: {str(e)}")
