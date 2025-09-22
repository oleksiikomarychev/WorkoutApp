import requests
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

WORKOUTS_SERVICE_URL = os.getenv("WORKOUTS_SERVICE_URL", "http://workouts-service:8004")
# Ensure URL has a scheme
if not WORKOUTS_SERVICE_URL.startswith('http'):
    WORKOUTS_SERVICE_URL = f"http://{WORKOUTS_SERVICE_URL}"

def create_workouts_batch(workouts: list) -> list:
    """Create multiple workouts via workouts-service"""
    try:
        url = f"{WORKOUTS_SERVICE_URL}/workouts/batch"
        logger.debug(f"Calling workouts service at: {url}")
        response = requests.post(
            url,
            json=workouts,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Failed to create workouts: {str(e)}")

def get_workouts_by_microcycle_ids(microcycle_ids: list) -> list:
    """Get workouts by microcycle IDs from workouts-service"""
    try:
        url = f"{WORKOUTS_SERVICE_URL}/workouts/by-microcycles"
        logger.debug(f"Calling workouts service at: {url}")
        response = requests.post(
            url,
            json={"microcycle_ids": microcycle_ids},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Failed to get workouts: {str(e)}")

def create_workout_rpc(workout_data: dict, microcycle_id: int, day: str) -> dict:
    """Create a single workout via workouts-service using batch endpoint"""
    try:
        if hasattr(workout_data, 'model_dump'):
            workout_data = workout_data.model_dump()
        
        # Prepare payload for batch endpoint with only top-level workout fields
        # Remove nested exercises since batch endpoint only creates workout objects
        workout_payload = {k: v for k, v in workout_data.items() if k != 'exercises'}
        payload = [workout_payload]
        
        logger.debug(f"Payload for workouts batch: {payload}")
        
        url = f"{WORKOUTS_SERVICE_URL}/workouts/batch"
        logger.debug(f"Calling workouts service at: {url}")
        response = requests.post(
            url,
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        # The response should be a list of created workouts; return the first one
        created_workouts = response.json()
        if created_workouts:
            return created_workouts[0]
        raise RuntimeError("Batch create returned empty list")
    except Exception as e:
        raise RuntimeError(f"Failed to create workout: {str(e)}")
