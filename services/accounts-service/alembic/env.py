import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic Config
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import service metadata and DB URL
try:
    from accounts_service.database import DATABASE_URL, Base  # type: ignore
except Exception:
    Base = None
    DATABASE_URL = os.getenv("ACCOUNTS_DATABASE_URL")

# target metadata
if Base is not None:
    target_metadata = Base.metadata
else:
    target_metadata = None

# Resolve URL: prefer env ACCOUNTS_DATABASE_URL, then alembic.ini
DB_URL = os.getenv("ACCOUNTS_DATABASE_URL") or DATABASE_URL or config.get_main_option("sqlalchemy.url")
if DB_URL:
    # Alembic должен использовать sync-драйвер, даже если приложение async
    # Меняем asyncpg -> psycopg2 при необходимости
    try:
        if DB_URL.startswith("postgresql+asyncpg://"):
            DB_URL = DB_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        elif DB_URL.startswith("postgresql://") and "+psycopg2" not in DB_URL:
            DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    except Exception:
        pass

    # Нормализуем query-параметры для psycopg2 (ssl/sslmode и т.п.)
    try:
        from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

        parsed = urlparse(DB_URL)
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        ssl_val = (q.get("ssl") or "").strip().lower()
        sslmode = (q.get("sslmode") or "").strip().lower()
        changed = False

        if "channel_binding" in q:
            q.pop("channel_binding", None)
            changed = True

        if ssl_val:
            if ssl_val in {"true", "1", "require"} and not sslmode:
                q["sslmode"] = "require"
                changed = True
            q.pop("ssl", None)
            changed = True

        if changed:
            DB_URL = urlunparse(parsed._replace(query=urlencode(q, doseq=True)))
    except Exception:
        pass

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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

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
