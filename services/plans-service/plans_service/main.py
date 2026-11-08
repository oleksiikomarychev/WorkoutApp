from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from backend_common.fastapi_app import create_service_app
from fastapi import FastAPI
from sqlalchemy import text

from .database import engine
from .logging_config import configure_logging
from .models.calendar import Base
from .redis_client import close_redis, init_redis
from .routers import (
    applied_calendar_plans,
    calendar_plans,
    coach_eligibility,
    macros,
    mesocycles,
    templates,
)
from .routers.internal_purge import router as internal_purge_router

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle events."""
    logger.info("plans_service_starting")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(text("ALTER TABLE calendar_plans ALTER COLUMN root_plan_id DROP NOT NULL"))
            except Exception:
                pass
    except Exception:
        logger.warning("plans_database_init_skipped_or_failed", exc_info=True)

    await init_redis()
    yield
    logger.info("plans_service_stopping")
    await close_redis()


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

app = create_service_app(
    title="Workout Tracking App - Plans Service",
    version="1.0.0",
    description="Calendar plans microservice for tracking workout plans, mesocycles, and progressions",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    cors_allow_origins=["*"],
    cors_allow_credentials=True,
    cors_allow_methods=["*"],
    cors_allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root welcome endpoint."""
    return {"message": "Welcome to Workout Tracking App"}


app.include_router(applied_calendar_plans.router, prefix="/plans", tags=["Applied Plans"])
app.include_router(calendar_plans.router, prefix="/plans", tags=["Calendar Plans"])
app.include_router(coach_eligibility.router, prefix="/plans", tags=["Plan Adoption"])
app.include_router(mesocycles.router, prefix="/plans", tags=["Mesocycles"])
app.include_router(macros.router, prefix="/plans", tags=["Plan Macros"])
app.include_router(templates.router, prefix="/plans", tags=["Mesocycle Templates"])
app.include_router(internal_purge_router)
