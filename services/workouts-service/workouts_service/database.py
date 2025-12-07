import logging
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from backend_common.database import create_async_engine_and_session, ensure_asyncpg_url
from sqlalchemy.orm import declarative_base

from . import models  # noqa: F401

DATABASE_URL = os.getenv("WORKOUTS_DATABASE_URL")
logger = logging.getLogger(__name__)

if not DATABASE_URL:
    raise ValueError("WORKOUTS_DATABASE_URL environment variable is not set")


if DATABASE_URL:
    DATABASE_URL = ensure_asyncpg_url(DATABASE_URL)


try:
    parsed = urlparse(DATABASE_URL)
    logger.info(f"Using DB URL scheme: {parsed.scheme}")
    logger.info(f"Effective DB URL (redacted): {parsed._replace(netloc='***').geturl()}")
    if parsed.scheme.startswith("postgresql+asyncpg"):
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        sslmode = (q.get("sslmode") or "").strip().lower()
        if "sslmode" in q:
            q.pop("sslmode", None)
            if sslmode in {"require", "verify-full", "verify-ca"}:
                q.setdefault("ssl", "true")
            elif sslmode in {"disable"}:
                q.setdefault("ssl", "false")

        ssl_val = q.get("ssl")
        if isinstance(ssl_val, str) and ssl_val.lower() not in {"true", "false"}:
            q["ssl"] = "true"

        removed_channel_binding = q.pop("channel_binding", None)
        new_query = urlencode(q, doseq=True)
        DATABASE_URL = urlunparse(parsed._replace(query=new_query))
except Exception:
    pass

engine_args = {}

engine, AsyncSessionLocal = create_async_engine_and_session(
    DATABASE_URL,
    autoflush=False,
    **engine_args,
)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
