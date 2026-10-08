
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_client = httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))

RPE_SERVICE_BASE = "http://rpe-service:8001"

RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=2, max=10),
    "retry": retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    "reraise": True,
}

# Simple in-memory cache for RPE computations
_rpe_cache: dict[tuple[str, float, float, float | None], float] = {}
_CACHE_MAX_SIZE = 1000

# Metrics
_cache_hits = 0
_cache_misses = 0
_rpc_calls = 0


def _cache_key(compute_type: str, a: float, b: float, c: float | None = None) -> tuple[str, float, float, float | None]:
    """Generate cache key for RPE computations."""
    if c is not None:
        return (compute_type, round(a, 2), round(b, 2), round(c, 2))
    return (compute_type, round(a, 2), round(b, 2), None)


def _get_from_cache(key: tuple[str, float, float, float | None]) -> float | None:
    """Get value from cache if exists."""
    global _cache_hits, _cache_misses
    value = _rpe_cache.get(key)
    if value is not None:
        _cache_hits += 1
    else:
        _cache_misses += 1
    return value


def _set_cache(key: tuple[str, float, float, float | None], value: float) -> None:
    """Set value in cache with LRU eviction."""
    if len(_rpe_cache) >= _CACHE_MAX_SIZE:
        # Simple FIFO eviction (remove first item)
        _rpe_cache.pop(next(iter(_rpe_cache)))
    _rpe_cache[key] = value


def get_rpe_metrics() -> dict[str, int]:
    """Get RPE cache and RPC metrics."""
    return {
        "cache_hits": _cache_hits,
        "cache_misses": _cache_misses,
        "rpc_calls": _rpc_calls,
        "cache_size": len(_rpe_cache),
    }


def reset_rpe_metrics() -> None:
    """Reset RPE metrics."""
    global _cache_hits, _cache_misses, _rpc_calls
    _cache_hits = 0
    _cache_misses = 0
    _rpc_calls = 0


async def get_rpe_table(headers: dict[str, str] | None = None):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{RPE_SERVICE_BASE}/rpe/table",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except Exception:
        return None


@retry(**RETRY_CONFIG)
async def get_volume(intensity: float, effort: float, headers: dict[str, str] | None = None) -> float:
    global _rpc_calls
    key = _cache_key("volume", intensity, effort)
    cached = _get_from_cache(key)
    if cached is not None:
        return cached

    _rpc_calls += 1
    payload = {"intensity": intensity, "effort": effort}
    response = await _client.post(
        f"{RPE_SERVICE_BASE}/rpe/compute",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    result = data["volume"]
    _set_cache(key, result)
    return result


@retry(**RETRY_CONFIG)
async def get_intensity(volume: float, effort: float, headers: dict[str, str] | None = None) -> float:
    global _rpc_calls
    key = _cache_key("intensity", volume, effort)
    cached = _get_from_cache(key)
    if cached is not None:
        return cached

    _rpc_calls += 1
    payload = {"volume": volume, "effort": effort}
    response = await _client.post(
        f"{RPE_SERVICE_BASE}/rpe/compute",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    result = data["intensity"]
    _set_cache(key, result)
    return result


@retry(**RETRY_CONFIG)
async def get_effort(volume: float, intensity: float, headers: dict[str, str] | None = None) -> float:
    global _rpc_calls
    key = _cache_key("effort", volume, intensity)
    cached = _get_from_cache(key)
    if cached is not None:
        return cached

    _rpc_calls += 1
    payload = {"volume": volume, "intensity": intensity}
    response = await _client.post(
        f"{RPE_SERVICE_BASE}/rpe/compute",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    result = data["effort"]
    _set_cache(key, result)
    return result
