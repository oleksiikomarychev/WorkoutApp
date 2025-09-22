from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool
from alembic import context

# Alembic Config
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import service metadata and resolved DB URL
try:
    from user_max_service.database import Base
    from user_max_service.database import DATABASE_URL
except Exception:
    Base = None
    DATABASE_URL = os.getenv("USER_MAX_DATABASE_URL")

# target metadata
if Base is not None:
    target_metadata = Base.metadata

# Resolve URL: prefer service's resolved DATABASE_URL, then env DATABASE_URL, then USER_MAX_DATABASE_URL, then config
DB_URL = (
os.getenv("USER_MAX_DATABASE_URL")
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
