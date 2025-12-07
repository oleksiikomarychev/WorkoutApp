import os
import uuid
from collections.abc import Sequence
from typing import Any

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator


def instrument_with_metrics(
    app: FastAPI,
    *,
    endpoint: str = "/metrics",
    include_in_schema: bool = False,
) -> None:
    Instrumentator().instrument(app).expose(
        app,
        endpoint=endpoint,
        include_in_schema=include_in_schema,
    )


def add_correlation_id_middleware(
    app: FastAPI,
    *,
    header_name: str = "X-Request-ID",
) -> None:
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name=header_name,
        generator=lambda: str(uuid.uuid4()),
        update_request_header=True,
    )


def configure_cors_from_env(
    app: FastAPI,
    *,
    origins_env: str = "CORS_ORIGINS",
    allow_credentials_env: str = "CORS_ALLOW_CREDENTIALS",
) -> None:
    cors_origins = os.getenv(origins_env, "*")
    allow_origins = [o.strip() for o in cors_origins.split(",")] if cors_origins != "*" else ["*"]

    env_allow_credentials = os.getenv(allow_credentials_env, "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    allow_credentials = False if allow_origins == ["*"] else env_allow_credentials

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_service_app(
    *,
    title: str,
    version: str = "0.1.0",
    description: str | None = None,
    enable_metrics: bool = True,
    metrics_endpoint: str = "/metrics",
    include_metrics_in_schema: bool = False,
    enable_cors: bool = True,
    cors_allow_origins: Sequence[str] | None = ("*",),
    cors_allow_credentials: bool = True,
    cors_allow_methods: Sequence[str] = ("*",),
    cors_allow_headers: Sequence[str] = ("*",),
    cors_expose_headers: Sequence[str] | None = None,
    enable_correlation_id: bool = True,
    correlation_header_name: str = "X-Request-ID",
    **fastapi_kwargs: Any,
) -> FastAPI:
    app = FastAPI(title=title, version=version, description=description, **fastapi_kwargs)

    if enable_metrics:
        instrument_with_metrics(
            app,
            endpoint=metrics_endpoint,
            include_in_schema=include_metrics_in_schema,
        )

    if enable_cors and cors_allow_origins is not None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_allow_origins),
            allow_credentials=cors_allow_credentials,
            allow_methods=list(cors_allow_methods),
            allow_headers=list(cors_allow_headers),
            expose_headers=list(cors_expose_headers) if cors_expose_headers is not None else None,
        )

    if enable_correlation_id:
        add_correlation_id_middleware(app, header_name=correlation_header_name)

    return app
