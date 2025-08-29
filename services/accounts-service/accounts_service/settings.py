from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "accounts-service"
    environment: str = "dev"
    # Default to volume-mounted path in container; works locally too if cwd has data/
    database_url: str = "sqlite:////app/data/accounts.db"
    # When using SQLite with SQLAlchemy 2.x + asyncio isn't needed here; use sync engine for simplicity
    echo_sql: bool = False
    # Feature flag: when false, disable coach-related routers/endpoints in accounts-service
    enable_coach_routers: bool = True

    class Config:
        env_prefix = "ACCOUNTS_"
        env_file = ".env"

    # Allow DATABASE_URL fallback if ACCOUNTS_DATABASE_URL is not provided
    def model_post_init(self, __context):
        import os
        if not self.database_url or self.database_url.startswith("sqlite:////app/data/"):
            alt = os.getenv("DATABASE_URL")
            if alt:
                object.__setattr__(self, "database_url", alt)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
