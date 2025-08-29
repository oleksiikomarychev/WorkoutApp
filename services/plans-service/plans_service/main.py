from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import os
from .routers import calendar_plans, applied_calendar_plans
from .routers import (
    workouts,
    exercises,
    user_max,
    calendar_plan_instances,
    rpe,
    workout_sessions,
)
from .routers import mesocycles
from .database import engine
from .database import Base


Base.metadata.create_all(bind=engine)

tags_metadata = [
    {
        "name": "Workouts",
        "description": "Operations with workouts. Workouts contain multiple exercises and are the main training sessions.",
    },
    {
        "name": "Exercises",
        "description": "Manage exercises. Exercise definitions that can be added to workouts.",
    },
    {
        "name": "User Maxes",
        "description": "User personal records and maximum weights for exercises.",
    },
    {
        "name": "Applied Plans",
        "description": "Operations with applied workout plans. Manage user's applied workout plans and their progress.",
    },
    {
        "name": "Calendar Plan Instances",
        "description": "Operations with calendar plan instances.",
    },
    {
        "name": "Workout Sessions",
        "description": "Start, update, finish, and list workout sessions.",
    },
]

app = FastAPI(
    title="Workout Tracking App",
    description="A comprehensive API for tracking workouts, exercises, and user progressions",
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://10.0.2.2:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(
    applied_calendar_plans.router,
    prefix="/api/v1/applied-plans",
    tags=["Applied Plans"],
)
app.include_router(
    calendar_plans.router, prefix="/api/v1/calendar-plans", tags=["Calendar Plans"]
)
app.include_router(
    calendar_plan_instances.router,
    prefix="/api/v1/calendar-plan-instances",
    tags=["Calendar Plan Instances"],
)
app.include_router(workouts.router, prefix="/api/v1/workouts", tags=["Workouts"])
# Exercises router is deprecated in monolith and proxied via gateway to exercises-service.
# Enable it only for local fallback/testing by setting ENABLE_EXERCISES_ROUTER=true
if os.getenv("ENABLE_EXERCISES_ROUTER", "false").lower() in ("1", "true", "yes", "on"):
    app.include_router(
        exercises.router, prefix="/api/v1/exercises", tags=["Exercises (monolith)"]
    )
app.include_router(user_max.router, prefix="/api/v1/user-maxes", tags=["User Maxes"])
app.include_router(rpe.router, prefix="/api/v1", tags=["Utils"])
app.include_router(
    applied_calendar_plans.router,
    prefix="/api/v1/applied-calendar-plans",
    tags=["Applied Plans"],
)
app.include_router(workout_sessions.router, prefix="/api/v1", tags=["Workout Sessions"])
app.include_router(mesocycles.router, prefix="/api/v1", tags=["Mesocycles"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/")
async def root():
    return {"message": "Welcome to Workout Tracking App"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
