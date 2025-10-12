import os
from dotenv import load_dotenv
from .config import get_settings
from .models.calendar import Base  # noqa: F401

load_dotenv()

# Get database URL from settings or environment
settings = get_settings()
database_url = settings.PLANS_DATABASE_URL

# Replace 'postgresql' with 'postgresql+asyncpg' for async support
if database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
