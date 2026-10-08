import logging
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from backend_common.database import create_async_engine_and_session, ensure_asyncpg_url
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("WORKOUTS_DATABASE_URL")
logger = logging.getLogger(__name__)

if not DATABASE_URL:
    raise ValueError("WORKOUTS_DATABASE_URL environment variable is not set")

# Replace localhost with host.docker.internal for Docker environment
DATABASE_URL = DATABASE_URL.replace("localhost", "host.docker.internal")

if DATABASE_URL:
    DATABASE_URL = ensure_asyncpg_url(DATABASE_URL)


connect_args: dict[str, object] = {}

try:
    parsed = urlparse(DATABASE_URL)
    logger.info(f"Using DB URL scheme: {parsed.scheme}")
    logger.info(f"Effective DB URL (redacted): {parsed._replace(netloc='***').geturl()}")
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
            if sslmode == "disable":
                connect_args["ssl"] = False
            else:
                connect_args["ssl"] = True
        elif ssl_raw:
            ssl_val = _normalize_sslmode(ssl_raw)
            if ssl_val == "disable":
                connect_args["ssl"] = False
            else:
                connect_args["ssl"] = True

        new_query = urlencode(q, doseq=True)
        DATABASE_URL = urlunparse(parsed._replace(query=new_query))
except Exception:
    pass

engine_args = {"connect_args": connect_args} if connect_args else {}

engine_args.setdefault("pool_pre_ping", True)
engine_args.setdefault("pool_recycle", int(os.getenv("DB_POOL_RECYCLE_SECONDS", "300")))

engine, AsyncSessionLocal = create_async_engine_and_session(
    DATABASE_URL,
    autoflush=False,
    **engine_args,
)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
