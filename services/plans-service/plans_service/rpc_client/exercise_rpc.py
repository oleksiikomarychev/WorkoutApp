import os

import httpx
from fastapi import APIRouter, HTTPException

EXERCISE_SERVICE_URL = os.getenv("EXERCISES_SERVICE_URL") or os.getenv("GATEWAY_URL")
if not EXERCISE_SERVICE_URL:
    raise RuntimeError("EXERCISES_SERVICE_URL or GATEWAY_URL must be set")
if not EXERCISE_SERVICE_URL.startswith(("http://", "https://")):
    EXERCISE_SERVICE_URL = f"https://{EXERCISE_SERVICE_URL}"

router = APIRouter()


async def create_exercise_instances_batch(instances: list) -> list:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EXERCISE_SERVICE_URL}/api/v1/exercises/instances/batch",
                json=instances,
                timeout=5,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to create exercise instances: {str(e)}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create exercise instances: {str(e)}")


@router.get("/list/{exercise_id}")
async def get_exercise_details(exercise_id: int):
    # Stub endpoint - no exception expected from static return
    return {"id": exercise_id, "name": "Bench Press", "muscle_group": "Chest"}
