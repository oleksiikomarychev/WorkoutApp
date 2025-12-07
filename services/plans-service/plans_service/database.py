from dotenv import load_dotenv

from .config import get_settings
from .models.calendar import Base  # noqa: F401

load_dotenv()


settings = get_settings()
database_url = settings.PLANS_DATABASE_URL


if database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
