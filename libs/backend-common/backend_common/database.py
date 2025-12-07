import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def get_required_env_url(env_name: str) -> str:
    url = os.getenv(env_name)
    if not url:
        raise RuntimeError(f"{env_name} environment variable is required")
    return url


def ensure_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def create_async_engine_and_session(
    database_url: str,
    *,
    echo: bool = False,
    future: bool = True,
    expire_on_commit: bool = True,
    autoflush: bool = True,
    **engine_kwargs: Any,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url, echo=echo, future=future, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=expire_on_commit,
        autoflush=autoflush,
        class_=AsyncSession,
    )
    return engine, session_factory
