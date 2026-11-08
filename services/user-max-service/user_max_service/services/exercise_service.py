"""Integration client for exercises-service."""

import asyncio
import logging
import time
from typing import Any

import httpx
from fastapi import HTTPException

from ..config import settings

logger = logging.getLogger(__name__)


def _get_exercises_base_url() -> str:
    url = (settings.EXERCISES_SERVICE_URL or settings.GATEWAY_URL or "http://exercises-service:8002").strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url.rstrip("/")


_EX_META_CACHE: list[dict[str, Any]] | None = None
_EX_META_CACHE_TS: float | None = None
_EX_META_TTL_SECONDS: float = settings.EX_META_TTL_SECONDS

_async_client: httpx.AsyncClient | None = None


def get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=5.0)
    return _async_client


async def get_exercise_name_by_id_async(
    exercise_id: int, max_retries: int = 3, retry_delay: float = 1.0
) -> str:
    """Fetch exercise name by ID asynchronously with retries."""
    base_url = _get_exercises_base_url()
    url = f"{base_url}/exercises/definitions/{exercise_id}"
    logger.info("Fetching exercise name from: %s", url)

    client = get_async_client()

    for attempt in range(max_retries):
        try:
            response = await client.get(url, timeout=3.0)
            response.raise_for_status()
            exercise = response.json()
            return exercise.get("name", "Unknown")
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error %s for URL %s", e.response.status_code, url)
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from exercises-service: {e.response.text}",
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.error("Connection error to %s: %s", url, e)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to exercises-service: {e}",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching exercise name: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error fetching exercise name: {e}",
            )

    raise HTTPException(status_code=503, detail="Failed to fetch exercise name after retries")


async def get_all_exercises_meta_async(
    max_retries: int = 3, retry_delay: float = 1.0
) -> list[dict[str, Any]]:
    """Fetch metadata for all exercises asynchronously with caching."""
    global _EX_META_CACHE, _EX_META_CACHE_TS
    now = time.time()

    if _EX_META_CACHE is not None and _EX_META_CACHE_TS is not None:
        if now - _EX_META_CACHE_TS < _EX_META_TTL_SECONDS:
            logger.info("Using cached exercises meta")
            return _EX_META_CACHE

    base_url = _get_exercises_base_url()
    url = f"{base_url}/exercises/definitions/"
    logger.info("Fetching all exercises meta from: %s", url)

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
            logger.error("HTTP error %s for URL %s", e.response.status_code, url)
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
            logger.error("Connection error to %s: %s", url, e)
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after connection error")
                return _EX_META_CACHE
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to exercises-service: {e}",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching exercises meta: %s", e)
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after unexpected error")
                return _EX_META_CACHE
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error fetching exercises meta: {e}",
            )
    return []


async def get_exercise_names_batch_async(exercise_ids: list[int]) -> dict[int, str]:
    """Fetch names for multiple exercise IDs concurrently."""
    if not exercise_ids:
        return {}

    tasks = [(ex_id, get_exercise_name_by_id_async(ex_id)) for ex_id in exercise_ids]
    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

    exercise_names: dict[int, str] = {}
    for (exercise_id, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error("Failed to fetch name for exercise %s: %s", exercise_id, result)
            exercise_names[exercise_id] = "Unknown"
        else:
            exercise_names[exercise_id] = str(result)

    return exercise_names


def _get_exercise_name_by_id_sync(
    exercise_id: int, max_retries: int = 3, retry_delay: float = 1.0
) -> str:
    base_url = _get_exercises_base_url()
    url = f"{base_url}/exercises/definitions/{exercise_id}"
    logger.info("Fetching exercise name from: %s", url)

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(url)
                response.raise_for_status()
                exercise = response.json()
                return exercise.get("name", "Unknown")
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error %s for URL %s", e.response.status_code, url)
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from exercises-service: {e.response.text}",
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.error("Connection error to %s: %s", url, e)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to exercises-service: {e}",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching exercise name: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error fetching exercise name: {e}",
            )

    raise HTTPException(status_code=503, detail="Failed to fetch exercise name after retries")


def get_exercise_name_by_id(
    exercise_id: int, max_retries: int = 3, retry_delay: float = 1.0
) -> str:
    """Fetch exercise name synchronously (with event loop compatibility)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                asyncio.run,
                get_exercise_name_by_id_async(exercise_id, max_retries, retry_delay),
            )
            return future.result()

    try:
        return asyncio.run(
            get_exercise_name_by_id_async(exercise_id, max_retries, retry_delay)
        )
    except Exception:
        return _get_exercise_name_by_id_sync(exercise_id, max_retries, retry_delay)


def get_all_exercises_meta(
    max_retries: int = 3, retry_delay: float = 1.0
) -> list[dict[str, Any]]:
    """Fetch all exercises metadata synchronously."""
    global _EX_META_CACHE, _EX_META_CACHE_TS
    now = time.time()

    if _EX_META_CACHE is not None and _EX_META_CACHE_TS is not None:
        if now - _EX_META_CACHE_TS < _EX_META_TTL_SECONDS:
            logger.info("Using cached exercises meta")
            return _EX_META_CACHE

    base_url = _get_exercises_base_url()
    url = f"{base_url}/exercises/definitions/"
    logger.info("Fetching all exercises meta from: %s", url)

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
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
            logger.error("HTTP error %s for URL %s", e.response.status_code, url)
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
            logger.error("Connection error to %s: %s", url, e)
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after connection error")
                return _EX_META_CACHE
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to exercises-service: {e}",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching exercises meta: %s", e)
            if _EX_META_CACHE is not None:
                logger.warning("Using stale cached exercises meta after unexpected error")
                return _EX_META_CACHE
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error fetching exercises meta: {e}",
            )
    return []


async def cleanup_async_client() -> None:
    """Close the shared async HTTP client if initialized."""
    global _async_client
    if _async_client:
        await _async_client.aclose()
        _async_client = None
