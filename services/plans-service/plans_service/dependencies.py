from __future__ import annotations

from backend_common.dependencies import make_get_current_user_id, make_get_db_async

from .database import DATABASE_URL, AsyncSessionLocal, engine, get_db
from .workout_calculation import WorkoutCalculator

# For backwards compatibility with direct dependency injection
get_db = make_get_db_async(AsyncSessionLocal)
get_current_user_id = make_get_current_user_id("plans-service")


def get_workout_service() -> WorkoutCalculator:
    return WorkoutCalculator()


__all__ = [
    "DATABASE_URL",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "get_current_user_id",
    "get_workout_service",
]
