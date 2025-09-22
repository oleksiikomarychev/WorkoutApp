import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from exercises_service.database import Base

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

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = os.getenv("EXERCISES_DATABASE_URL", default_db_url)
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
    url = os.getenv("EXERCISES_DATABASE_URL", default_db_url)
    
    if not url:
        raise ValueError("EXERCISES_DATABASE_URL environment variable is not set")
        
    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
