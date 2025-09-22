from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict

from .exceptions import NotFoundException
from .routers.workouts import router as workouts_router
from .routers.sessions import router as sessions_router
from .routers.workout_generation import router as workout_generation_router

app = FastAPI(title="workouts-service", version="0.1.0")


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
