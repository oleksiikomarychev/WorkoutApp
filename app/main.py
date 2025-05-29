from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
import time
from fastapi.openapi.utils import get_openapi

from app.routers import workouts, exercises, progressions, user_max
from app.database import engine, Base

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
        "name": "Progressions",
        "description": "Workout progression management. Track and manage exercise progressions over time.",
    },
    {
        "name": "User Maxes",
        "description": "User personal records and maximum weights for exercises.",
    }
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
     "*"
 ]
app.add_middleware(
     CORSMiddleware,
     allow_origins=origins,
     allow_credentials=True,
     allow_methods=["*"],
     allow_headers=["*"],
 )

app.include_router(workouts.router, prefix="/api/v1", tags=["Workouts"])
app.include_router(exercises.router, prefix="/api/v1", tags=["Exercises"])
app.include_router(progressions.router, prefix="/api", tags=["Progressions"])
app.include_router(user_max.router, prefix="/api", tags=["User Maxes"])



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