import os

import structlog
from backend_common.database import create_async_engine_and_session, ensure_async_driver_url
from dotenv import load_dotenv
from sqlalchemy.orm import declarative_base

logger = structlog.get_logger(__name__)

Base = declarative_base()

load_dotenv()

raw_url = os.getenv("EXERCISES_DATABASE_URL") or os.getenv("DATABASE_URL")
if raw_url:
    EXERCISES_DATABASE_URL = ensure_async_driver_url(raw_url)
    scheme = EXERCISES_DATABASE_URL.split("://")[0]
    logger.info("Exercises DB configured", scheme=scheme)
else:
    EXERCISES_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    logger.warning("EXERCISES_DATABASE_URL not set; falling back to in-memory sqlite")

engine, AsyncSessionLocal = create_async_engine_and_session(EXERCISES_DATABASE_URL, expire_on_commit=False)
logger.info("Exercises database engine created successfully")
