import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

try:
    from bot.models.database import DATABASE_URL as SERVICE_DATABASE_URL
    from bot.models.database import Base as ServiceBase
    import bot.models.all_models  # Ensure all models are imported
except Exception as e:
    print(f"Error importing models: {e}")
    ServiceBase = None
    SERVICE_DATABASE_URL = None

if ServiceBase is not None:
    target_metadata = ServiceBase.metadata
else:
    target_metadata = None

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url", SERVICE_DATABASE_URL)
    if not url:
        raise RuntimeError("DATABASE_URL not found")
        
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
    db_url = config.get_main_option("sqlalchemy.url", SERVICE_DATABASE_URL)
    if not db_url:
        raise RuntimeError("DATABASE_URL not found")

    if "sqlite+aiosqlite" in db_url:
        db_url = db_url.replace("sqlite+aiosqlite", "sqlite")

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
