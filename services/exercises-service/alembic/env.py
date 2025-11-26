import os
from logging.config import fileConfig

from alembic import context
from exercises_service.database import Base
from sqlalchemy import create_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# Default SQLite database URL
default_db_url = os.getenv("EXERCISES_DATABASE_URL")


def _to_sync_url(url: str | None) -> str:
    """Normalize async SQLAlchemy URL to sync driver for Alembic runtime.

    Alembic's sync engine cannot connect using async drivers like
    'sqlite+aiosqlite' or 'postgresql+asyncpg'. Convert them to their
    sync equivalents for migrations.
    """
    if not url:
        raise ValueError("EXERCISES_DATABASE_URL environment variable is not set")
    # Normalize Postgres async -> sync
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    # Normalize SQLite async -> sync
    if url.startswith("sqlite+aiosqlite:"):
        return url.replace("sqlite+aiosqlite:", "sqlite:", 1)
    return url


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = _to_sync_url(os.getenv("EXERCISES_DATABASE_URL", default_db_url))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    url = _to_sync_url(os.getenv("EXERCISES_DATABASE_URL", default_db_url))

    # Normalize query params for psycopg2: it doesn't accept 'ssl=true', expects 'sslmode=require'
    try:
        from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

        parsed = urlparse(url)
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        ssl_val = (q.get("ssl") or "").strip().lower()
        sslmode = (q.get("sslmode") or "").strip().lower()
        changed = False
        # Drop unsupported channel_binding for psycopg2
        if "channel_binding" in q:
            q.pop("channel_binding", None)
            changed = True
        # Map asyncpg-style 'ssl' to psycopg2 'sslmode'
        if ssl_val:
            if ssl_val in {"true", "1", "require"} and not sslmode:
                q["sslmode"] = "require"
                changed = True
            # Remove 'ssl' param entirely for psycopg2
            q.pop("ssl", None)
            changed = True
        if changed:
            url = urlunparse(parsed._replace(query=urlencode(q, doseq=True)))
    except Exception:
        # Best effort; if parsing fails, proceed with original url
        pass

    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
