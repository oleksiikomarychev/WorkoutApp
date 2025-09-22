from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from .database import database_url
from .workout_calculation import WorkoutCalculator

# Create an async database engine
engine = create_async_engine(database_url)

# Create an async sessionmaker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

def get_workout_service() -> WorkoutCalculator:
    return WorkoutCalculator()
