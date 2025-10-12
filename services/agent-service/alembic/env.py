import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from agent_service.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Set database URL based on environment
db_url = os.getenv("AGENT_DATABASE_URL")
if not db_url:
    raise ValueError("AGENT_DATABASE_URL environment variable not set")

config.set_main_option("sqlalchemy.url", db_url)

# Import all models to ensure they are attached to the Base.metadata
from agent_service import models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        file_template='%(rev)s_%(slug)s'
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            file_template='%(rev)s_%(slug)s'
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
