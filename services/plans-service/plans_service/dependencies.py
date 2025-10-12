from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


# For local development, use a simple SQLite database if no DATABASE_URL is provided
import os

# Try to load from environment first
DATABASE_URL = os.getenv('PLANS_DATABASE_URL')

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

def get_workout_service():
    from .workout_calculation import WorkoutCalculator
    return WorkoutCalculator()
