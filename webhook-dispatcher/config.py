"""Configuration for Webhook Dispatcher Service."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Redis configuration
    redis_url: str = "redis://localhost:6378"
    
    # Database URLs for reading webhook subscriptions
    social_database_url: str = "postgresql://user:pass@localhost:5432/social"
    messaging_database_url: str = "postgresql://user:pass@localhost:5432/messaging"
    
    # Consumer configuration
    consumer_group_name: str = "webhook-dispatcher"
    consumer_name: str = "dispatcher-1"
    batch_size: int = 10
    block_time_ms: int = 5000  # 5 seconds
    
    # Delivery configuration
    delivery_timeout: int = 10  # seconds
    max_retries: int = 5
    retry_delays: list[int] = [60, 300, 900, 3600, 10800]  # 1m, 5m, 15m, 1h, 3h in seconds
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
