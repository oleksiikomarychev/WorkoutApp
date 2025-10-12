from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from .routers import calendar_plans, applied_calendar_plans
from .routers import (
    mesocycles,
)
from .dependencies import engine
from .models.calendar import Base


def create_tables():
    Base.metadata.create_all(bind=engine)


tags_metadata = [
    {
        "name": "Applied Plans",
        "description": "Operations with applied workout plans. Manage user's applied workout plans and their progress.",
    },
    {
        "name": "Calendar Plans",
        "description": "Manage calendar plans that define the structure of training over time.",
    },
    {
        "name": "Mesocycles",
        "description": "Manage mesocycles which are blocks of training within a calendar plan.",
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

# Add startup event handler for async database initialization
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

app.include_router(applied_calendar_plans.router,prefix="/plans",tags=["Applied Plans"])
app.include_router(calendar_plans.router, prefix="/plans", tags=["Calendar Plans"])
app.include_router(mesocycles.router, prefix="/plans", tags=["Mesocycles"])


@app.get("/health")
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
