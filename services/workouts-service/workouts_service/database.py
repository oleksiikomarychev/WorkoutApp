from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import structlog
from backend_common.database import create_async_engine_and_session, ensure_async_driver_url
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from .config import settings

logger = structlog.get_logger(__name__)

Base = declarative_base()

raw_url = settings.WORKOUTS_DATABASE_URL or os.getenv("DATABASE_URL")

if raw_url:
    DATABASE_URL = ensure_async_driver_url(raw_url)
    in_docker = os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv")
    if in_docker and "localhost" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("localhost", "host.docker.internal")
    elif not in_docker and "host.docker.internal" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("host.docker.internal", "localhost")
else:
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    logger.warning("WORKOUTS_DATABASE_URL not set; falling back to in-memory sqlite")

connect_args: dict[str, object] = {}

try:
    parsed = urlparse(DATABASE_URL)
    if parsed.scheme.startswith("postgresql+asyncpg"):
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        sslmode_raw = (q.pop("sslmode", "") or "").strip().lower()
        ssl_raw = (q.pop("ssl", "") or "").strip().lower()
        q.pop("channel_binding", None)

        def _normalize_sslmode(val: str) -> str:
            if val in {"true", "1", "yes", "on"}:
                return "require"
            if val in {"false", "0", "no", "off"}:
                return "disable"
            return val

        sslmode = _normalize_sslmode(sslmode_raw)
        if sslmode:
            connect_args["ssl"] = False if sslmode == "disable" else True
        elif ssl_raw:
            ssl_val = _normalize_sslmode(ssl_raw)
            connect_args["ssl"] = False if ssl_val == "disable" else True

        new_query = urlencode(q, doseq=True)
        DATABASE_URL = urlunparse(parsed._replace(query=new_query))
except Exception:
    pass

engine_args: dict[str, object] = {"connect_args": connect_args} if connect_args else {}
if not DATABASE_URL.startswith("sqlite"):
    engine_args.setdefault("pool_pre_ping", True)
    engine_args.setdefault("pool_recycle", settings.DB_POOL_RECYCLE_SECONDS)

engine, AsyncSessionLocal = create_async_engine_and_session(
    DATABASE_URL,
    autoflush=False,
    expire_on_commit=False,
    **engine_args,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
