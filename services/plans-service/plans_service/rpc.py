import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .config import settings
from typing import Optional

_client = httpx.AsyncClient(
    timeout=10.0,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)

RPE_SERVICE_BASE = "http://rpe-service:8001"

RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=2, max=10),
    "retry": retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    "reraise": True
}

async def get_rpe_table():
    """Fetch RPE table from RPE service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{RPE_SERVICE_BASE}/rpe/table")
            response.raise_for_status()
            return response.json()
    except Exception:
        return None

@retry(**RETRY_CONFIG)
async def get_volume(intensity: float, effort: float) -> float:
    """Fetch volume from RPE service"""
    async with httpx.AsyncClient() as client:
        payload = {"intensity": intensity, "effort": effort}
        response = await client.post(f"{RPE_SERVICE_BASE}/rpe/compute", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["volume"]

@retry(**RETRY_CONFIG)
async def get_intensity(volume: float, effort: float) -> float:
    """Fetch intensity from RPE service"""
    async with httpx.AsyncClient() as client:
        payload = {"volume": volume, "effort": effort}
        response = await client.post(f"{RPE_SERVICE_BASE}/rpe/compute", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["intensity"]

@retry(**RETRY_CONFIG)
async def get_effort(volume: float, intensity: float) -> float:
    """Fetch effort from RPE service"""
    async with httpx.AsyncClient() as client:
        payload = {"volume": volume, "intensity": intensity}
        response = await client.post(f"{RPE_SERVICE_BASE}/rpe/compute", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["effort"]
