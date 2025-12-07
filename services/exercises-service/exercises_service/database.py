import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import structlog
from backend_common.database import create_async_engine_and_session
from sqlalchemy.ext.declarative import declarative_base

logger = structlog.get_logger(__name__)

Base = declarative_base()


EXERCISES_DATABASE_URL = os.getenv("EXERCISES_DATABASE_URL")


if EXERCISES_DATABASE_URL:
    if EXERCISES_DATABASE_URL.startswith("postgresql://"):
        EXERCISES_DATABASE_URL = EXERCISES_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif EXERCISES_DATABASE_URL.startswith("postgres://"):
        EXERCISES_DATABASE_URL = EXERCISES_DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

    try:
        parsed = urlparse(EXERCISES_DATABASE_URL)
        if parsed.scheme.startswith("postgresql+asyncpg"):
            q = dict(parse_qsl(parsed.query, keep_blank_values=True))
            sslmode = (q.get("sslmode") or "").strip().lower()

            removed_sslmode = q.pop("sslmode", None)

            if sslmode in {"require", "verify-full", "verify-ca"}:
                q.setdefault("ssl", "true")
            elif sslmode in {"disable"}:
                q.setdefault("ssl", "false")

            removed_channel_binding = q.pop("channel_binding", None)

            new_query = urlencode(q, doseq=True)
            EXERCISES_DATABASE_URL = urlunparse(parsed._replace(query=new_query))

            if removed_sslmode or removed_channel_binding:
                logger.info(
                    f"Sanitized DB URL: removed sslmode={removed_sslmode}, channel_binding={removed_channel_binding}"
                )
    except Exception as e:
        logger.error(f"Failed to sanitize DB URL: {e}", exc_info=True)

        pass

logger.info(f"Using DB URL scheme: {urlparse(EXERCISES_DATABASE_URL).scheme}")

engine, AsyncSessionLocal = create_async_engine_and_session(EXERCISES_DATABASE_URL, expire_on_commit=False)
logger.info("Exercises database engine created successfully")
