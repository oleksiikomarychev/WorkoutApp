from backend_common.logging import configure_logging as _configure_logging
from sentry_sdk.integrations.httpx import HttpxIntegration


def configure_logging() -> None:
    _configure_logging("api-gateway", extra_sentry_integrations=[HttpxIntegration()])
