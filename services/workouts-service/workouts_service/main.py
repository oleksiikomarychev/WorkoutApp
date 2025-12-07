import structlog
from backend_common.fastapi_app import create_service_app
from fastapi.responses import JSONResponse

from .exceptions import NotFoundException
from .logging_config import configure_logging
from .redis_client import close_redis, init_redis
from .routers.analytics import router as analytics_router
from .routers.sessions import router as sessions_router
from .routers.workout_generation import router as workout_generation_router
from .routers.workouts import router as workouts_router

configure_logging()
logger = structlog.get_logger(__name__)

app = create_service_app(
    title="workouts-service",
    version="0.1.0",
    enable_cors=False,
)


@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request, exc: NotFoundException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
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


app.include_router(workouts_router, prefix="/workouts")
app.include_router(sessions_router, prefix="/workouts")
app.include_router(workout_generation_router, prefix="/workouts")
app.include_router(analytics_router, prefix="/workouts")
