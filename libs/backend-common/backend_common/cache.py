"""Generic Redis cache helpers for all backend services."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CacheMetrics:
    """Container for cache metric counters (prometheus Counter objects)."""

    hits: Any = None
    misses: Any = None
    errors: Any = None

    def inc_hit(self) -> None:
        if self.hits:
            self.hits.inc()

    def inc_miss(self) -> None:
        if self.misses:
            self.misses.inc()

    def inc_error(self) -> None:
        if self.errors:
            self.errors.inc()


class CacheHelper:
    """
    Generic async cache helper with metrics support.

    Usage:
        cache = CacheHelper(
            get_redis=get_redis,
            metrics=CacheMetrics(hits=MY_HITS, misses=MY_MISSES, errors=MY_ERRORS),
        )
        data = await cache.get(key)
        await cache.set(key, data, ttl=300)
    """

    def __init__(
        self,
        get_redis: Callable[[], Awaitable[Any]],
        metrics: CacheMetrics | None = None,
        default_ttl: int = 300,
    ):
        self._get_redis = get_redis
        self._metrics = metrics or CacheMetrics()
        self._default_ttl = default_ttl

    async def get(self, key: str) -> dict | list | None:
        """Get value from cache. Returns None on miss or error."""
        redis = await self._get_redis()
        if not redis:
            return None
        try:
            if cached := await redis.get(key):
                self._metrics.inc_hit()
                return json.loads(cached)
            self._metrics.inc_miss()
        except Exception:
            self._metrics.inc_error()
            logger.warning("cache_get_failed", key=key, exc_info=True)
        return None

    async def set(self, key: str, data: dict | list, ttl: int | None = None) -> None:
        """Set value in cache with TTL."""
        redis = await self._get_redis()
        if not redis:
            return
        try:
            await redis.set(key, json.dumps(data), ex=ttl or self._default_ttl)
        except Exception:
            self._metrics.inc_error()
            logger.warning("cache_set_failed", key=key, exc_info=True)
