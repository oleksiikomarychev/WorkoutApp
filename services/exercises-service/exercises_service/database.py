import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = structlog.get_logger(__name__)

Base = declarative_base()

# Import models to ensure they are registered with Base.metadata

EXERCISES_DATABASE_URL = os.getenv("EXERCISES_DATABASE_URL")

# Ensure we are using an async driver and sanitize ssl params for asyncpg
if EXERCISES_DATABASE_URL:
    if EXERCISES_DATABASE_URL.startswith("postgresql://"):
        EXERCISES_DATABASE_URL = EXERCISES_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif EXERCISES_DATABASE_URL.startswith("postgres://"):
        EXERCISES_DATABASE_URL = EXERCISES_DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    # Map '?sslmode=require' (psycopg-style) to asyncpg-compatible 'ssl=true'
    try:
        parsed = urlparse(EXERCISES_DATABASE_URL)
        if parsed.scheme.startswith("postgresql+asyncpg"):
            q = dict(parse_qsl(parsed.query, keep_blank_values=True))
            sslmode = (q.get("sslmode") or "").strip().lower()

            # ALWAYS remove sslmode - asyncpg doesn't support it
            removed_sslmode = q.pop("sslmode", None)

            # Map sslmode to asyncpg's 'ssl' where applicable
            if sslmode in {"require", "verify-full", "verify-ca"}:
                q.setdefault("ssl", "true")
            elif sslmode in {"disable"}:
                q.setdefault("ssl", "false")
            # For 'allow', 'prefer' - just remove, don't set ssl

            # Drop unsupported asyncpg kwarg from some providers
            removed_channel_binding = q.pop("channel_binding", None)

            new_query = urlencode(q, doseq=True)
            EXERCISES_DATABASE_URL = urlunparse(parsed._replace(query=new_query))

            if removed_sslmode or removed_channel_binding:
                logger.info(
                    f"Sanitized DB URL: removed sslmode={removed_sslmode}, channel_binding={removed_channel_binding}"
                )
    except Exception as e:
        logger.error(f"Failed to sanitize DB URL: {e}", exc_info=True)
        # Keep original URL but this will likely fail
        pass

logger.info(f"Using DB URL scheme: {urlparse(EXERCISES_DATABASE_URL).scheme}")

engine = create_async_engine(EXERCISES_DATABASE_URL)
logger.info("Exercises database engine created successfully")

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
