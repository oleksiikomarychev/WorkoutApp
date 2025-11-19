from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import sys
from .routers import calendar_plans, applied_calendar_plans
from .routers import (
    mesocycles,
    macros,
    templates,
)

# Ensure INFO logs are emitted from application modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
# Reduce uvicorn access log noise if needed, but keep uvicorn/error at INFO
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
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
    {
        "name": "Plan Macros",
        "description": "Store and manage macro rules attached to calendar plans.",
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
app.include_router(macros.router, prefix="/plans", tags=["Plan Macros"])
app.include_router(templates.router, prefix="/plans", tags=["Mesocycle Templates"])


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
