import os

from backend_common.database import create_async_engine_and_session, ensure_asyncpg_url
from backend_common.dependencies import make_get_current_user_id, make_get_db_async
from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = os.getenv("PLANS_DATABASE_URL")


if DATABASE_URL:
    DATABASE_URL = ensure_asyncpg_url(DATABASE_URL)


engine, AsyncSessionLocal = create_async_engine_and_session(DATABASE_URL, pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,)

get_db: AsyncSession = make_get_db_async(AsyncSessionLocal)  # type: ignore[assignment]
get_current_user_id = make_get_current_user_id("plans-service")


def get_workout_service():
    from .workout_calculation import WorkoutCalculator

    return WorkoutCalculator()
