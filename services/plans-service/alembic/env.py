import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from plans_service.database import Base
from plans_service import models  # noqa: F401

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve DB URL: prefer DATABASE_URL, then PLANS_DATABASE_URL, then SQLite fallback
db_url = (
    os.getenv("DATABASE_URL")
    or os.getenv("PLANS_DATABASE_URL")
    or "sqlite:////app/data/plans.db"
)
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
