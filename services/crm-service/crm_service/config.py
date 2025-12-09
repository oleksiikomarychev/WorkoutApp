import os


class Settings:
    @property
    def workouts_service_url(self) -> str:
        return os.getenv("WORKOUTS_SERVICE_URL", "http://workouts-service:8004")

    @property
    def plans_service_url(self) -> str:
        return os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005")

    @property
    def exercises_service_url(self) -> str:
        return os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")

    @property
    def agent_service_url(self) -> str:
        return os.getenv("AGENT_SERVICE_URL", "http://agent-service:8006")

    @property
    def accounts_service_url(self) -> str:
        return os.getenv("ACCOUNTS_SERVICE_URL", "http://accounts-service:8007")


settings = Settings()
