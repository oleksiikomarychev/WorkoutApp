from backend_common.database import (
    create_async_engine_and_session,
    ensure_asyncpg_url,
    get_required_env_url,
)
from sqlalchemy.orm import declarative_base

DATABASE_URL = get_required_env_url("ACCOUNTS_DATABASE_URL")

# Ensure we use an async driver for SQLAlchemy's asyncio extension
DATABASE_URL = ensure_asyncpg_url(DATABASE_URL)

engine, AsyncSessionLocal = create_async_engine_and_session(DATABASE_URL, expire_on_commit=False)
Base = declarative_base()
