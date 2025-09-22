from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    USER_MAX_SERVICE_URL: str = "http://user-max-service:8003"

settings = Settings()
