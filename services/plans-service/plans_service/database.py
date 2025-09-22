import os
from dotenv import load_dotenv
from .models.calendar import Base  # Изменяем импорт

load_dotenv()

database_url = os.getenv("DATABASE_URL")

# Replace 'postgresql' with 'postgresql+asyncpg' for async support
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Import all models to ensure they are registered with the Base metadata
from .models.calendar import Base  # noqa: F401
