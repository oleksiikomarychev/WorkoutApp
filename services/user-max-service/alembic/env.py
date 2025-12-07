import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


try:
    from user_max_service import models  # noqa: F401
    from user_max_service.database import DATABASE_URL, Base
except Exception:
    Base = None
    DATABASE_URL = os.getenv("USER_MAX_DATABASE_URL")


if Base is not None:
    target_metadata = Base.metadata


DB_URL = os.getenv("USER_MAX_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if DB_URL:
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
