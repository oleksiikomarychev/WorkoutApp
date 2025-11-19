import os
import httpx
from fastapi import APIRouter, HTTPException

EXERCISE_SERVICE_URL = os.getenv("EXERCISES_SERVICE_URL") or os.getenv("GATEWAY_URL")
if not EXERCISE_SERVICE_URL:
    raise RuntimeError("EXERCISES_SERVICE_URL or GATEWAY_URL must be set")
if not EXERCISE_SERVICE_URL.startswith(('http://', 'https://')):
    EXERCISE_SERVICE_URL = f"https://{EXERCISE_SERVICE_URL}"

router = APIRouter()

async def create_exercise_instances_batch(instances: list) -> list:
    """Create multiple exercise instances via exercises-service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EXERCISE_SERVICE_URL}/api/v1/exercises/instances/batch",
                json=instances,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to create exercise instances: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create exercise instances: {str(e)}"
        )

@router.get("/list/{exercise_id}")
async def get_exercise_details(exercise_id: int):
    try:
        return {"id": exercise_id, "name": "Bench Press", "muscle_group": "Chest"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch exercise details: {str(e)}"
        )
