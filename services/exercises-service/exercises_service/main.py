import structlog
import uvloop
from backend_common.fastapi_app import create_service_app

from exercises_service.database import AsyncSessionLocal
from exercises_service.logging_config import configure_logging
from exercises_service.redis_client import get_redis_client
from exercises_service.routers import (
    core_router,
    exercise_definition_router,
)
from exercises_service.services.exercise_definition_service import ExerciseDefinitionService
from exercises_service.services.exercise_service import ExerciseService

configure_logging()
logger = structlog.get_logger(__name__)

uvloop.install()

app = create_service_app(
    title="exercises-service",
    version="0.1.0",
    enable_cors=False,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    redis_client = await get_redis_client()
    if redis_client.is_connected():
        await preload_exercise_cache(redis_client)
    await ExerciseService.load_muscle_metadata()

async def preload_exercise_cache(redis_client):
    async with AsyncSessionLocal() as db:
        service = ExerciseDefinitionService(db, redis_client)
        structlog.get_logger(__name__).info("Preloading exercise cache")
        await service.list_definitions(ids=None)
        structlog.get_logger(__name__).info("Exercise cache preloaded")


@app.on_event("shutdown")
async def shutdown_event():
    redis_client = await get_redis_client()
    if redis_client.is_connected():
        await redis_client.close()


app.include_router(core_router.router, prefix="/exercises")
app.include_router(exercise_definition_router.router, prefix="/exercises")