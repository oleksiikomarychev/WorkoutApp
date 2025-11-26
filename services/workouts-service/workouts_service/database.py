import logging
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from . import models  # noqa: F401

DATABASE_URL = os.getenv("WORKOUTS_DATABASE_URL")
logger = logging.getLogger(__name__)

if not DATABASE_URL:
    raise ValueError("WORKOUTS_DATABASE_URL environment variable is not set")

# Adjust the URL to use asyncpg driver if it's a standard PostgreSQL URL
if DATABASE_URL:
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Map psycopg-style sslmode to asyncpg-compatible parameters
try:
    parsed = urlparse(DATABASE_URL)
    logger.info(f"Using DB URL scheme: {parsed.scheme}")
    logger.info(f"Effective DB URL (redacted): {parsed._replace(netloc='***').geturl()}")
    if parsed.scheme.startswith("postgresql+asyncpg"):
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        sslmode = (q.get("sslmode") or "").strip().lower()
        if "sslmode" in q:
            # Remove sslmode and map to asyncpg's 'ssl' where applicable
            q.pop("sslmode", None)
            if sslmode in {"require", "verify-full", "verify-ca"}:
                q.setdefault("ssl", "true")
            elif sslmode in {"disable"}:
                q.setdefault("ssl", "false")
        # Normalize 'ssl' to boolean values for asyncpg
        ssl_val = q.get("ssl")
        if isinstance(ssl_val, str) and ssl_val.lower() not in {"true", "false"}:
            # e.g. 'require' from some providers -> treat as true
            q["ssl"] = "true"

        # Drop unsupported asyncpg kwarg from some providers
        removed_channel_binding = q.pop("channel_binding", None)
        new_query = urlencode(q, doseq=True)
        DATABASE_URL = urlunparse(parsed._replace(query=new_query))
except Exception:
    # Best-effort sanitation
    pass

engine_args = {}

engine = create_async_engine(DATABASE_URL, **engine_args)
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
