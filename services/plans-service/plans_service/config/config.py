from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from . import prompts


class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )



@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
LLM_PROMPT = prompts.LLM_PROMPT
