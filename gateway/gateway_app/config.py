import os


def _normalize_env_url(var_name: str) -> str | None:
    raw = (os.getenv(var_name) or "").strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    return raw.rstrip("/")


RPE_SERVICE_URL = _normalize_env_url("RPE_SERVICE_URL")
EXERCISES_SERVICE_URL = _normalize_env_url("EXERCISES_SERVICE_URL")
USER_MAX_SERVICE_URL = _normalize_env_url("USER_MAX_SERVICE_URL")
WORKOUTS_SERVICE_URL = _normalize_env_url("WORKOUTS_SERVICE_URL")
PLANS_SERVICE_URL = _normalize_env_url("PLANS_SERVICE_URL")
AGENT_SERVICE_URL = _normalize_env_url("AGENT_SERVICE_URL")
ACCOUNTS_SERVICE_URL = _normalize_env_url("ACCOUNTS_SERVICE_URL")
CRM_SERVICE_URL = _normalize_env_url("CRM_SERVICE_URL")

SOCIAL_API_URL_RAW = (os.getenv("SOCIAL_API_URL") or "").strip()
SOCIAL_API_URL = SOCIAL_API_URL_RAW.rstrip("/") if SOCIAL_API_URL_RAW else ""
MESSAGING_API_URL_RAW = (os.getenv("MESSAGING_API_URL") or "").strip()
MESSAGING_API_URL = MESSAGING_API_URL_RAW.rstrip("/") if MESSAGING_API_URL_RAW else ""
MESSENGER_APP_ID = (os.getenv("MESSENGER_APP_ID") or "").strip()
