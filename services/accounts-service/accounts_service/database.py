import os
from collections.abc import AsyncGenerator

import structlog
from backend_common.database import (
    create_async_engine_and_session,
    ensure_async_driver_url,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from .config import settings

logger = structlog.get_logger(__name__)

Base = declarative_base()

raw_url = settings.ACCOUNTS_DATABASE_URL or os.getenv("DATABASE_URL")
if raw_url:
    DATABASE_URL = ensure_async_driver_url(raw_url)
    # Inside docker containers, localhost should route to host.docker.internal if indicated
    if (os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv")) and "localhost" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("localhost", "host.docker.internal")
    scheme = DATABASE_URL.split("://")[0]
    logger.info("Accounts DB configured", scheme=scheme)
else:
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    logger.warning("ACCOUNTS_DATABASE_URL not set; falling back to in-memory sqlite")

engine, AsyncSessionLocal = create_async_engine_and_session(DATABASE_URL, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
