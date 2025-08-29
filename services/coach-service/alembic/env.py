from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool
from alembic import context

# this is the Alembic Config object, which provides access to
# the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import service metadata and resolved DB URL
try:
    from coach_service.database import Base as ServiceBase
    from coach_service.database import DATABASE_URL as SERVICE_DATABASE_URL
except Exception:  # pragma: no cover
    ServiceBase = None
    SERVICE_DATABASE_URL = None

# add your model's MetaData object here for 'autogenerate' support
if ServiceBase is not None:
    target_metadata = ServiceBase.metadata
else:  # pragma: no cover
    target_metadata = None

# Resolve URL: prefer service's resolved DATABASE_URL, then env DATABASE_URL, then COACH_DATABASE_URL, then config
DB_URL = (
    SERVICE_DATABASE_URL
    or os.getenv("DATABASE_URL")
    or os.getenv("COACH_DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)
if DB_URL:
    config.set_main_option("sqlalchemy.url", DB_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
