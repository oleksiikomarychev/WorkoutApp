import os

import requests

WORKOUTS_SERVICE_URL = os.getenv("WORKOUTS_SERVICE_URL", "http://workouts-service:8004")

if not WORKOUTS_SERVICE_URL.startswith("http"):
    WORKOUTS_SERVICE_URL = f"http://{WORKOUTS_SERVICE_URL}"


def create_workouts_batch(workouts: list) -> list:
    try:
        url = f"{WORKOUTS_SERVICE_URL}/workouts/batch"
        response = requests.post(url, json=workouts, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to create workouts: {str(e)}")


def get_workouts_by_microcycle_ids(microcycle_ids: list) -> list:
    try:
        url = f"{WORKOUTS_SERVICE_URL}/workouts/by-microcycles"
        response = requests.post(url, json={"microcycle_ids": microcycle_ids}, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to get workouts: {str(e)}")


def create_workout_rpc(workout_data: dict, microcycle_id: int, day: str) -> dict:
    try:
        if hasattr(workout_data, "model_dump"):
            workout_data = workout_data.model_dump()

        workout_payload = {k: v for k, v in workout_data.items() if k != "exercises"}
        payload = [workout_payload]

        url = f"{WORKOUTS_SERVICE_URL}/workouts/batch"
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()

        created_workouts = response.json()
        if created_workouts:
            return created_workouts[0]
        raise RuntimeError("Batch create returned empty list")
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to create workout: {str(e)}")
