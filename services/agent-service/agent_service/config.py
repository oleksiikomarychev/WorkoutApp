import os


class Settings:
    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "gemini").lower()

    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", "gemini-2.0-flash")

    @property
    def staged_llm_provider(self) -> str:
        return os.getenv("STAGED_LLM_PROVIDER", self.llm_provider).lower()

    @property
    def staged_llm_model(self) -> str:
        return os.getenv("GENAI_STAGED_MODEL", self.llm_model)

    @property
    def genai_max_attempts(self) -> int:
        try:
            return max(1, int(os.getenv("GENAI_MAX_ATTEMPTS", "3")))
        except Exception:
            return 3

    @property
    def genai_base_delay(self) -> float:
        try:
            return max(0.1, float(os.getenv("GENAI_BASE_DELAY", "1.5")))
        except Exception:
            return 1.5

    @property
    def genai_rate_limit_per_minute(self) -> int:
        try:
            return max(1, int(os.getenv("GENAI_RATE_LIMIT_PER_MINUTE", "9")))
        except Exception:
            return 9

    @property
    def genai_rate_limit_window_seconds(self) -> float:
        try:
            return max(1.0, float(os.getenv("GENAI_RATE_LIMIT_WINDOW_SECONDS", "60")))
        except Exception:
            return 60.0

    @property
    def genai_rate_limit_concurrency(self) -> int:
        try:
            return max(1, int(os.getenv("GENAI_RATE_LIMIT_CONCURRENCY", "1")))
        except Exception:
            return 1

    @property
    def user_max_service_url(self):
        return os.getenv("USER_MAX_SERVICE_URL", "http://user-max-service:8003")

    @property
    def exercises_service_url(self):
        return os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")

    @property
    def plans_service_url(self):
        return os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005")

    @property
    def workouts_service_url(self):
        return os.getenv("WORKOUTS_SERVICE_URL", "http://workouts-service:8004")

    @property
    def crm_service_url(self):
        return os.getenv("CRM_SERVICE_URL", "http://crm-service:8008")

    @property
    def rpe_service_url(self):
        return os.getenv("RPE_SERVICE_URL", "http://rpe-service:8001")

    @property
    def agent_database_url(self):
        return os.getenv("AGENT_DATABASE_URL")

    @property
    def celery_task_timeout_seconds(self) -> int:
        try:
            return max(30, int(os.getenv("CELERY_TASK_TIMEOUT_SECONDS", "600")))
        except Exception:
            return 600


settings = Settings()
