from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict
import logging
import sys

from .exceptions import NotFoundException
from .routers.workouts import router as workouts_router
from .routers.sessions import router as sessions_router
from .routers.workout_generation import router as workout_generation_router
from .routers.analytics import router as analytics_router

app = FastAPI(title="workouts-service", version="0.1.0")

# Ensure INFO logs are emitted from application modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)


@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request, exc: NotFoundException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(workouts_router, prefix="/workouts")
app.include_router(sessions_router, prefix="/workouts")
app.include_router(workout_generation_router, prefix="/workouts")
app.include_router(analytics_router, prefix="/workouts")
