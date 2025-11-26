import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

try:
    from workouts_service.database import DATABASE_URL as SERVICE_DATABASE_URL
    from workouts_service.database import Base as ServiceBase
except Exception:
    ServiceBase = None
    SERVICE_DATABASE_URL = None

if ServiceBase is not None:
    target_metadata = ServiceBase.metadata
else:
    target_metadata = None

DB_URL = (
    SERVICE_DATABASE_URL
    or os.getenv("DATABASE_URL")
    or os.getenv("WORKOUTS_DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)
if DB_URL:
    config.set_main_option("sqlalchemy.url", DB_URL)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    db_url = os.getenv("WORKOUTS_DATABASE_URL")
    if not db_url:
        raise RuntimeError("WORKOUTS_DATABASE_URL environment variable is not set")

    # Ensure we're using synchronous driver for migrations
    if "+asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    elif "+psycopg2" not in db_url:
        # Add psycopg2 driver if not specified
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")

    # Normalize query params for psycopg2: it doesn't accept 'ssl=true', expects 'sslmode=require'
    try:
        from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

        parsed = urlparse(db_url)
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
            # Treat any non-false value as require
            if ssl_val in {"true", "1", "require"}:
                if not sslmode:
                    q["sslmode"] = "require"
                    changed = True
            # Remove 'ssl' param entirely for psycopg2
            q.pop("ssl", None)
            changed = True
        # Rebuild URL if changed
        if changed:
            db_url = urlunparse(parsed._replace(query=urlencode(q, doseq=True)))
    except Exception:
        # Best effort; if parsing fails, proceed with original db_url
        pass

    connectable = create_engine(db_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
