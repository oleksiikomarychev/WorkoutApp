import asyncio
import logging
import os
import time

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

EXERCISES_SERVICE_URL = os.getenv("EXERCISES_SERVICE_URL") or os.getenv("GATEWAY_URL")
if not EXERCISES_SERVICE_URL:
    raise RuntimeError("EXERCISES_SERVICE_URL or GATEWAY_URL must be set")
if not EXERCISES_SERVICE_URL.startswith(("http://", "https://")):
    EXERCISES_SERVICE_URL = f"https://{EXERCISES_SERVICE_URL}"


_EX_META_CACHE: list | None = None
_EX_META_CACHE_TS: float | None = None
_EX_META_TTL_SECONDS: float = float(os.getenv("EX_META_TTL_SECONDS", "1800"))

_async_client: httpx.AsyncClient | None = None


def get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=5.0)
    return _async_client


async def get_exercise_name_by_id_async(exercise_id: int, max_retries: int = 3, retry_delay: float = 1.0) -> str:
    url = f"{EXERCISES_SERVICE_URL}/exercises/definitions/{exercise_id}"
    logger.info(f"Fetching exercise name from: {url}")

    client = get_async_client()
    
    for attempt in range(max_retries):
        try:
            response = await client.get(url, timeout=3.0)
            response.raise_for_status()
            exercise = response.json()
            return exercise["name"]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} for URL {url}")
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from exercises-service: {e.response.text}",
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.error(f"Connection error to {url}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(status_code=503, detail=f"Cannot connect to exercises-service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error fetching exercise name: {str(e)}")

    raise HTTPException(status_code=503, detail="Failed to fetch exercise name after retries")


async def get_all_exercises_meta_async(max_retries: int = 3, retry_delay: float = 1.0) -> list:
    global _EX_META_CACHE, _EX_META_CACHE_TS
    now = time.time()

    if _EX_META_CACHE is not None and _EX_META_CACHE_TS is not None:
        if now - _EX_META_CACHE_TS < _EX_META_TTL_SECONDS:
            logger.info("Using cached exercises meta")
            return _EX_META_CACHE

    url = f"{EXERCISES_SERVICE_URL}/exercises/definitions/"
    logger.info(f"Fetching all exercises meta from: {url}")
    
    client = get_async_client()
    
    for attempt in range(max_retries):
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                _EX_META_CACHE = data
                _EX_META_CACHE_TS = now
                return data
            _EX_META_CACHE = []
            _EX_META_CACHE_TS = now
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} for URL {url}")
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after HTTP error")
                return _EX_META_CACHE
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from exercises-service: {e.response.text}",
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.error(f"Connection error to {url}: {str(e)}")
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after connection error")
                return _EX_META_CACHE
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(status_code=503, detail=f"Cannot connect to exercises-service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after unexpected error")
                return _EX_META_CACHE
            raise HTTPException(status_code=500, detail=f"Unexpected error fetching exercises meta: {str(e)}")
    return []


async def get_exercise_names_batch_async(exercise_ids: list[int]) -> dict[int, str]:
    if not exercise_ids:
        return {}
    
    tasks = []
    for exercise_id in exercise_ids:
        task = get_exercise_name_by_id_async(exercise_id)
        tasks.append((exercise_id, task))
    
    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
    
    exercise_names = {}
    for (exercise_id, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error(f"Failed to fetch name for exercise {exercise_id}: {result}")
            exercise_names[exercise_id] = "Unknown"
        else:
            exercise_names[exercise_id] = result
    
    return exercise_names


def get_exercise_name_by_id(exercise_id: int, max_retries: int = 3, retry_delay: float = 1.0) -> str:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, get_exercise_name_by_id_async(exercise_id, max_retries, retry_delay))
                return future.result()
        else:
            return asyncio.run(get_exercise_name_by_id_async(exercise_id, max_retries, retry_delay))
    except Exception:
        return _get_exercise_name_by_id_sync(exercise_id, max_retries, retry_delay)


def get_all_exercises_meta(max_retries: int = 3, retry_delay: float = 1.0) -> list:
    global _EX_META_CACHE, _EX_META_CACHE_TS
    now = time.time()

    if _EX_META_CACHE is not None and _EX_META_CACHE_TS is not None:
        if now - _EX_META_CACHE_TS < _EX_META_TTL_SECONDS:
            logger.info("Using cached exercises meta")
            return _EX_META_CACHE

    url = f"{EXERCISES_SERVICE_URL}/exercises/definitions/"
    logger.info(f"Fetching all exercises meta from: {url}")
    for attempt in range(max_retries):
        try:
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                _EX_META_CACHE = data
                _EX_META_CACHE_TS = now
                return data
            _EX_META_CACHE = []
            _EX_META_CACHE_TS = now
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} for URL {url}")
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after HTTP error")
                return _EX_META_CACHE
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from exercises-service: {e.response.text}",
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.error(f"Connection error to {url}: {str(e)}")
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after connection error")
                return _EX_META_CACHE
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(status_code=503, detail=f"Cannot connect to exercises-service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after unexpected error")
                return _EX_META_CACHE
            raise HTTPException(status_code=500, detail=f"Unexpected error fetching exercises meta: {str(e)}")
    return []


def _get_exercise_name_by_id_sync(exercise_id: int, max_retries: int = 3, retry_delay: float = 1.0) -> str:
    url = f"{EXERCISES_SERVICE_URL}/exercises/definitions/{exercise_id}"
    logger.info(f"Fetching exercise name from: {url}")

    for attempt in range(max_retries):
        try:
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
                detail=f"Error from exercises-service: {e.response.text}",
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.error(f"Connection error to {url}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(status_code=503, detail=f"Cannot connect to exercises-service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error fetching exercise name: {str(e)}")

    raise HTTPException(status_code=503, detail="Failed to fetch exercise name after retries")


async def cleanup_async_client():
    global _async_client
    if _async_client:
        await _async_client.aclose()
        _async_client = None
