import os

import structlog
from backend_common.database import create_async_engine_and_session, ensure_async_driver_url
from dotenv import load_dotenv
from sqlalchemy.ext.declarative import declarative_base

logger = structlog.get_logger(__name__)

Base = declarative_base()

load_dotenv()

EXERCISES_DATABASE_URL = os.getenv("EXERCISES_DATABASE_URL")

if EXERCISES_DATABASE_URL:
    EXERCISES_DATABASE_URL = ensure_async_driver_url(EXERCISES_DATABASE_URL)
    logger.info(f"Using DB URL scheme: {os.path.splitext(EXERCISES_DATABASE_URL.split('://')[0])[0]}://")
else:
    raise RuntimeError("EXERCISES_DATABASE_URL environment variable is required")

engine, AsyncSessionLocal = create_async_engine_and_session(EXERCISES_DATABASE_URL, expire_on_commit=False)
logger.info("Exercises database engine created successfully")
