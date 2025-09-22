import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import models to ensure they are registered with Base.metadata
from . import models

EXERCISES_DATABASE_URL = os.getenv("EXERCISES_DATABASE_URL")

# Ensure we are using an async driver
if EXERCISES_DATABASE_URL:
    if EXERCISES_DATABASE_URL.startswith("postgresql://"):
        EXERCISES_DATABASE_URL = EXERCISES_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(EXERCISES_DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)
