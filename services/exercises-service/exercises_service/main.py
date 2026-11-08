from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvloop
from backend_common.fastapi_app import create_service_app
from fastapi import FastAPI

from exercises_service.database import AsyncSessionLocal
from exercises_service.logging_config import configure_logging
from exercises_service.redis_client import RedisClient, get_redis_client
from exercises_service.routers import (
    core_router,
    exercise_definition_router,
)
from exercises_service.services.exercise_definition_service import ExerciseDefinitionService
from exercises_service.services.exercise_service import ExerciseService

configure_logging()
logger = structlog.get_logger(__name__)

uvloop.install()


async def preload_exercise_cache(redis_client: RedisClient) -> None:
    """Preload all exercise definitions into Redis cache on startup."""
    try:
        async with AsyncSessionLocal() as db:
            service = ExerciseDefinitionService(db, redis_client)
            logger.info("Preloading exercise cache")
            await service.list_definitions(ids=None)
            logger.info("Exercise cache preloaded")
    except Exception as e:
        logger.warning("Failed to preload exercise cache", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle events."""
    redis_client = await get_redis_client()
    if redis_client.is_connected():
        await preload_exercise_cache(redis_client)
    await ExerciseService.load_muscle_metadata()
    yield
    redis_client = await get_redis_client()
    if redis_client.is_connected():
        await redis_client.close()


app = create_service_app(
    title="exercises-service",
    version="0.1.0",
    enable_cors=False,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Root health check endpoint."""
    return {"status": "ok"}


app.include_router(exercise_definition_router.router, prefix="/exercises")
app.include_router(core_router.router, prefix="/exercises")
