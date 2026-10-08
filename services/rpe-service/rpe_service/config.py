try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore[assignment]

    def SettingsConfigDict(**kwargs: object) -> dict[str, object]:
        return kwargs


class Settings(BaseSettings):
    """Configuration settings for rpe-service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    USER_MAX_SERVICE_URL: str = "http://user-max-service:8003"
    INTERNAL_GATEWAY_SECRET: str = ""
    RPE_TABLE_PATH: str | None = None
    RPE_TABLE_JSON: str | None = None
    SERVICE_PORT: int = 8001
    GRPC_PORT: int = 50051


settings = Settings()

