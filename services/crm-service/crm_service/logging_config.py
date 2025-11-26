import logging
import os
import sys

import sentry_sdk
import structlog
from asgi_correlation_id.context import correlation_id
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from structlog.contextvars import merge_contextvars


def add_service_and_env(logger, method_name, event_dict):
    event_dict["service"] = os.getenv("SERVICE_NAME", "crm-service")
    event_dict["env"] = os.getenv("APP_ENV", "local")
    return event_dict


def add_correlation_id(logger, method_name, event_dict):
    cid = correlation_id.get(None)
    if cid is not None:
        event_dict["correlation_id"] = cid
    return event_dict


def bind_correlation_id_to_sentry(logger, method_name, event_dict):
    cid = event_dict.get("correlation_id")
    if cid is not None:
        try:
            sentry_sdk.set_tag("correlation_id", cid)
        except Exception:
            pass
    return event_dict


service_name = os.getenv("SERVICE_NAME", "crm-service")
sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.ERROR,
)


def configure_logging() -> None:
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    app_env = os.getenv("APP_ENV", "local")
    is_dev = app_env in {"local", "dev"}

    if os.getenv("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            environment=app_env,
            integrations=[FastApiIntegration(), sentry_logging],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            send_default_pii=False,
        )
        sentry_sdk.set_tag("service", service_name)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors = [
        merge_contextvars,
        add_service_and_env,
        add_correlation_id,
        bind_correlation_id_to_sentry,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        timestamper,
    ]

    renderer = structlog.dev.ConsoleRenderer() if is_dev else structlog.processors.JSONRenderer()

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
