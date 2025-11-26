# For local development, use a simple SQLite database if no DATABASE_URL is provided
import os

from fastapi import HTTPException, Request, status
from sentry_sdk import set_tag, set_user
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Try to load from environment first
DATABASE_URL = os.getenv("PLANS_DATABASE_URL")

# Convert to async driver if needed
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Rest of the database setup remains the same
engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_current_user_id(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header required")
    set_user({"id": str(user_id)})
    set_tag("service", "plans-service")
    return user_id


def get_workout_service():
    from .workout_calculation import WorkoutCalculator

    return WorkoutCalculator()
