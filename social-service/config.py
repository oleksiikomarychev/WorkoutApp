"""Configuration for Social Service."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "postgresql://user:pass@postgres-social:5432/social"
    
    @property
    def effective_database_url(self) -> str:
        """Get database URL from environment or default."""
        import os
        return os.getenv("DATABASE_URL", self.database_url)
    
    # Redis
    redis_url: str = "redis://redis:6379"
    
    # Webhook
    webhook_hmac_secret: str = "change-me-in-production"
    
    # Service
    service_name: str = "social-service"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
