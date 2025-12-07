from backend_common.logging import configure_logging as _configure_logging


def configure_logging() -> None:
    _configure_logging("crm-service")
