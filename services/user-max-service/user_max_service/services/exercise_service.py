import os
import httpx
from fastapi import HTTPException
import time
import logging

logger = logging.getLogger(__name__)

EXERCISES_SERVICE_URL = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")


def get_exercise_name_by_id(exercise_id: int, max_retries: int = 3, retry_delay: float = 1.0) -> str:
    """
    Fetches exercise name from exercises-service by exercise ID with retry logic
    """
    url = f"{EXERCISES_SERVICE_URL}/exercises/definitions/{exercise_id}"
    logger.info(f"Fetching exercise name from: {url}")
    
    for attempt in range(max_retries):
        try:
            # Use a timeout of 3 seconds
            response = httpx.get(url, timeout=3.0)
            response.raise_for_status()
            exercise = response.json()
            return exercise["name"]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} for URL {url}")
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from exercises-service: {e.response.text}"
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.error(f"Connection error to {url}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to exercises-service: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error fetching exercise name: {str(e)}"
            )
    
    raise HTTPException(
        status_code=503,
        detail="Failed to fetch exercise name after retries"
    )


def get_all_exercises_meta(max_retries: int = 3, retry_delay: float = 1.0) -> list:
    """
    Fetch the full list of exercise definitions (including target/synergist_muscles)
    from exercises-service. Used for aggregation/analysis to avoid per-ID calls.
    """
    url = f"{EXERCISES_SERVICE_URL}/exercises/definitions/"
    logger.info(f"Fetching all exercises meta from: {url}")
    for attempt in range(max_retries):
        try:
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} for URL {url}")
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from exercises-service: {e.response.text}"
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.error(f"Connection error to {url}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to exercises-service: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error fetching exercises meta: {str(e)}"
            )
    return []
