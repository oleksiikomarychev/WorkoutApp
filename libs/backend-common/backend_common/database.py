import os
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def get_required_env_url(env_name: str) -> str:
    url = os.getenv(env_name)
    if not url:
        raise RuntimeError(f"{env_name} environment variable is required")
    return url


def _sanitize_asyncpg_postgres_url(url: str) -> tuple[str, dict[str, Any]]:
    try:
        parsed = urlparse(url)
        if not parsed.scheme.startswith("postgresql+asyncpg"):
            return url, {}

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

        connect_args: dict[str, Any] = {}

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
        return urlunparse(parsed._replace(query=new_query)), connect_args
    except Exception:
        return url, {}


def ensure_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def ensure_async_driver_url(url: str) -> str:
    url = ensure_asyncpg_url(url)

    if url.startswith("sqlite+aiosqlite://") or url.startswith("sqlite+aiosqlite:"):
        return url

    if url.startswith("sqlite+pysqlite://"):
        return url.replace("sqlite+pysqlite://", "sqlite+aiosqlite://", 1)

    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    if url.startswith("sqlite:"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)

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
    database_url = ensure_async_driver_url(database_url)
    database_url, extracted_connect_args = _sanitize_asyncpg_postgres_url(database_url)
    if extracted_connect_args:
        existing_connect_args = engine_kwargs.get("connect_args")
        if existing_connect_args is None:
            engine_kwargs["connect_args"] = extracted_connect_args
        elif isinstance(existing_connect_args, dict):
            filtered_existing = dict(existing_connect_args)
            filtered_existing.pop("sslmode", None)

            merged = dict(extracted_connect_args)
            merged.update(filtered_existing)
            engine_kwargs["connect_args"] = merged
    engine = create_async_engine(database_url, echo=echo, future=future, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=expire_on_commit,
        autoflush=autoflush,
        class_=AsyncSession,
    )
    return engine, session_factory
