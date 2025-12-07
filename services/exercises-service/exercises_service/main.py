import structlog
from backend_common.fastapi_app import create_service_app

from exercises_service.logging_config import configure_logging
from exercises_service.redis_client import close_redis, init_redis
from exercises_service.routers import (
    core_router,
    exercise_definition_router,
    exercise_instance_router,
)
from exercises_service.services.exercise_service import ExerciseService

configure_logging()
logger = structlog.get_logger(__name__)

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
    await init_redis()


@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()


ExerciseService.load_muscle_metadata()

app.include_router(core_router.router, prefix="/exercises")
app.include_router(exercise_definition_router.router, prefix="/exercises")
app.include_router(exercise_instance_router.router, prefix="/exercises")
