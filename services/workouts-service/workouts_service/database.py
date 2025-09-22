import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("WORKOUTS_DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("WORKOUTS_DATABASE_URL environment variable is not set")

# Adjust the URL to use asyncpg driver if it's a standard PostgreSQL URL
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine_args = {"echo": True}

engine = create_async_engine(DATABASE_URL, **engine_args)
AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()

# Явный импорт моделей для Alembic
from . import models  # noqa: F401

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
