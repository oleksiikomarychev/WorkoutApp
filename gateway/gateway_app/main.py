import asyncio
import base64
import json
import os
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog
from backend_common.fastapi_app import (
    add_correlation_id_middleware,
    configure_cors_from_env,
    instrument_with_metrics,
)
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from redis.asyncio import Redis
from sentry_sdk import set_tag, set_user
from starlette.middleware.base import BaseHTTPMiddleware

from gateway_app.logging_config import configure_logging
from gateway_app.routes.agent import agent_router
from gateway_app.routes.analytics import analytics_router
from gateway_app.routes.crm import crm_router
from gateway_app.routes.exercises import (
    exercises_core_router,
    exercises_definitions_router,
    exercises_instances_router,
)
from gateway_app.routes.plans import (
    plans_applied_router,
    plans_calendar_router,
    plans_instances_router,
    plans_mesocycles_router,
    plans_templates_router,
)
from gateway_app.routes.rpe import rpe_router
from gateway_app.routes.sessions import sessions_router
from gateway_app.routes.user_max import user_max_router
from gateway_app.routes.workouts import workout_metrics_router, workouts_router

configure_logging()
logger = structlog.get_logger(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")


def _normalize_env_url(var_name: str) -> str | None:
    raw = (os.getenv(var_name) or "").strip()
    if not raw:
        logger.error("env_var_missing", env_var=var_name)
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

try:
    import firebase_admin
    from firebase_admin import auth, credentials
    from firebase_admin import exceptions as firebase_exceptions
except ImportError:  # pragma: no cover
    firebase_admin = None  # type: ignore
    auth = None  # type: ignore
    credentials = None  # type: ignore
    firebase_exceptions = None  # type: ignore

_DEFAULT_PROXY_TIMEOUT = float(os.getenv("PROXY_REQUEST_TIMEOUT_SECONDS", "45"))
_DEFAULT_CONNECT_TIMEOUT = float(os.getenv("PROXY_CONNECT_TIMEOUT_SECONDS", "10"))
_PLANS_APPLY_TIMEOUT = float(os.getenv("PLANS_APPLY_TIMEOUT_SECONDS", str(max(_DEFAULT_PROXY_TIMEOUT, 90.0))))
_GET_RETRIES = int(os.getenv("PROXY_GET_RETRIES", "3"))
_GET_RETRY_BASE_DELAY = float(os.getenv("PROXY_GET_RETRY_BASE_DELAY_SECONDS", "0.3"))

app = FastAPI(
    title="WorkoutApp Gateway",
    version="1.0",
    servers=[{"url": "/api/v1", "description": "Gateway API base path"}],
)
app.router.redirect_slashes = False

instrument_with_metrics(app, endpoint="/metrics", include_in_schema=False)


_PROFILE_CACHE_TTL_SECONDS = int(os.getenv("PROFILE_AGGREGATES_CACHE_TTL_SECONDS", "900"))
_PROFILE_CACHE_MAX_KEYS = int(os.getenv("PROFILE_AGGREGATES_CACHE_MAX_KEYS", "256"))


class _ProfileCache:
    def __init__(self, max_keys: int, ttl_seconds: int) -> None:
        self._data: OrderedDict[str, dict] = OrderedDict()
        self._max_keys = max_keys
        self._ttl_seconds = ttl_seconds

    def get(self, key: str, now: datetime) -> dict | None:
        entry = self._data.get(key)
        if not entry:
            return None
        expires_at = entry.get("expires_at")
        if expires_at and expires_at <= now:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return entry

    def set(self, key: str, etag: str, content: dict[str, Any], now: datetime) -> None:
        expires_at = now + timedelta(seconds=self._ttl_seconds)
        self._data[key] = {"etag": etag, "content": content, "expires_at": expires_at}
        self._data.move_to_end(key)
        while len(self._data) > self._max_keys:
            self._data.popitem(last=False)

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def pop(self, key: str, default: Any | None = None) -> Any | None:
        return self._data.pop(key, default)


_PROFILE_CACHE = _ProfileCache(_PROFILE_CACHE_MAX_KEYS, _PROFILE_CACHE_TTL_SECONDS)


def _invalidate_profile_cache_for_user(uid: str | None) -> None:
    if not uid:
        return
    try:
        keys = list(_PROFILE_CACHE.keys())
        for k in keys:
            if k.startswith(f"{uid}:"):
                _PROFILE_CACHE.pop(k, None)
    except Exception as e:
        logger.warning("profile_cache_invalidation_failed", error=str(e))


def _bind_sentry_user(uid: str | None) -> None:
    if uid:
        set_user({"id": str(uid)})
        set_tag("service", SERVICE_NAME)
    else:
        set_user(None)


def _forward_headers(request: Request) -> dict[str, str]:
    allowed_header_names = {"traceparent", "x-request-id", "content-type", "accept"}
    forwarded: dict[str, str] = {k: v for k, v in request.headers.items() if k.lower() in allowed_header_names}

    user = getattr(request.state, "user", None)
    if user:
        uid = user.get("uid")
        if uid:
            forwarded["X-User-Id"] = str(uid)

    return forwarded


async def _proxy_request(request: Request, target_url: str, headers: dict[str, str]) -> Response:
    """Proxy HTTP request to a backend service and return the response."""
    timeout = httpx.Timeout(connect=_DEFAULT_CONNECT_TIMEOUT, read=_DEFAULT_PROXY_TIMEOUT, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        body = await request.body()
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body if body else None,
            params=request.query_params,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )


def _forward_messenger_headers(request: Request) -> dict[str, str]:
    headers = _forward_headers(request)
    authorization = request.headers.get("authorization")
    if authorization:
        headers["Authorization"] = authorization
    if MESSENGER_APP_ID:
        headers["X-App-Id"] = MESSENGER_APP_ID
    return headers


def _build_messenger_target(base_url: str, path: str) -> str:
    suffix = path or ""
    if suffix and not suffix.startswith("/"):
        suffix = f"/{suffix}"
    return f"{base_url.rstrip('/')}/{suffix.lstrip('/')}"


_FIREBASE_APP: firebase_admin.App | None = None if firebase_admin else None  # type: ignore
_FIREBASE_CHECK_REVOKED = True
_FIREBASE_AUDIENCE: str | None = os.getenv("FIREBASE_PROJECT_ID")
_FIREBASE_ISSUER: str | None = None
_PUBLIC_PATHS = {
    "/api/v1/health",
    "/openapi.json",
    "/docs",
    "/docs/",
    "/redoc",
    "/redoc/",
    "/metrics",
    "/payment/success",
    "/payment/cancel",
    "/stripe/connect/return",
    "/stripe/connect/refresh",
    "/api/v1/crm/billing/stripe/webhook",
}
_INTERNAL_GATEWAY_SECRET = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()

_RATE_LIMIT_ENABLED = (os.getenv("GATEWAY_RATE_LIMIT_ENABLED") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_RATE_LIMIT_REQUESTS = int(os.getenv("GATEWAY_RATE_LIMIT_REQUESTS", "60"))
_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("GATEWAY_RATE_LIMIT_WINDOW_SECONDS", "60"))

_GATEWAY_REDIS_HOST = os.getenv("GATEWAY_REDIS_HOST", "redis")
_GATEWAY_REDIS_PORT = int(os.getenv("GATEWAY_REDIS_PORT", "6379"))
_GATEWAY_REDIS_DB = int(os.getenv("GATEWAY_REDIS_DB", "0"))
_GATEWAY_REDIS_PASSWORD = (os.getenv("GATEWAY_REDIS_PASSWORD") or "").strip() or None

_rate_limit_redis: Redis | None = None
_rate_limit_redis_error_logged = False


async def _get_rate_limit_redis() -> Redis | None:
    global _rate_limit_redis, _rate_limit_redis_error_logged
    if not _RATE_LIMIT_ENABLED:
        return None
    if _rate_limit_redis is not None:
        return _rate_limit_redis
    try:
        client = Redis(
            host=_GATEWAY_REDIS_HOST,
            port=_GATEWAY_REDIS_PORT,
            db=_GATEWAY_REDIS_DB,
            password=_GATEWAY_REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        await client.ping()
        _rate_limit_redis = client
        try:
            logger.info(
                "gateway_rate_limit_redis_connected",
                host=_GATEWAY_REDIS_HOST,
                port=_GATEWAY_REDIS_PORT,
                db=_GATEWAY_REDIS_DB,
            )
        except Exception:
            pass
        return _rate_limit_redis
    except Exception as exc:
        if not _rate_limit_redis_error_logged:
            try:
                logger.error("gateway_rate_limit_redis_connection_failed", error=str(exc))
            except Exception:
                pass
            _rate_limit_redis_error_logged = True
        return None


def _initialize_firebase_app() -> None:
    global _FIREBASE_APP, _FIREBASE_CHECK_REVOKED
    if firebase_admin is None:
        raise RuntimeError("firebase_admin is not available")
    if _FIREBASE_APP is not None:
        return
    credentials_b64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")
    if not credentials_b64:
        raise RuntimeError("FIREBASE_CREDENTIALS_BASE64 must be set")
    try:
        decoded = base64.b64decode(credentials_b64).decode("utf-8")
        credential_data = json.loads(decoded)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("FIREBASE_CREDENTIALS_BASE64 is invalid") from exc

    env_pid = os.getenv("FIREBASE_PROJECT_ID")
    if env_pid:
        credential_data["project_id"] = env_pid
    project_id = credential_data.get("project_id")
    if project_id:
        global _FIREBASE_AUDIENCE, _FIREBASE_ISSUER
        _FIREBASE_AUDIENCE = project_id
        _FIREBASE_ISSUER = f"https://securetoken.google.com/{project_id}"
    emulator_host = os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
    if emulator_host:
        os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = emulator_host
        _FIREBASE_CHECK_REVOKED = False
    cert = credentials.Certificate(credential_data)
    _FIREBASE_APP = firebase_admin.initialize_app(cert)


def _is_public_route(method: str, path: str) -> bool:
    if method in ("GET", "HEAD"):
        if path in _PUBLIC_PATHS:
            return True

        if path.startswith("/api/v1/avatars/") and path.endswith(".png"):
            return True
    return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not _RATE_LIMIT_ENABLED:
            return await call_next(request)

        method = request.method.upper()
        path = request.url.path

        if method == "OPTIONS" or _is_public_route(method, path):
            return await call_next(request)

        internal_secret = request.headers.get("X-Internal-Secret")
        if _INTERNAL_GATEWAY_SECRET and internal_secret == _INTERNAL_GATEWAY_SECRET:
            return await call_next(request)

        redis = await _get_rate_limit_redis()
        if redis is None:
            return await call_next(request)

        user = getattr(request.state, "user", None)
        identifier: str
        uid = user.get("uid") if user else None
        if uid:
            identifier = f"user:{uid}"
        else:
            client = request.client
            client_host = getattr(client, "host", None) if client else None
            identifier = f"ip:{client_host or 'unknown'}"

        now = int(time.time())
        window = max(_RATE_LIMIT_WINDOW_SECONDS, 1)
        bucket = now // window
        key = f"gateway:ratelimit:{identifier}:{bucket}"
        ttl = window

        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, ttl)
        except Exception as exc:
            try:
                logger.warning("gateway_rate_limit_redis_operation_failed", error=str(exc))
            except Exception:
                pass
            return await call_next(request)

        if count > _RATE_LIMIT_REQUESTS:
            retry_after = bucket * window + window - now
            if retry_after < 1:
                retry_after = 1
            headers = {"Retry-After": str(retry_after)}
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests"},
                headers=headers,
            )

        return await call_next(request)


class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        path = request.url.path
        if method == "OPTIONS" or _is_public_route(method, path):
            return await call_next(request)
        internal_secret = request.headers.get("X-Internal-Secret")
        if _INTERNAL_GATEWAY_SECRET and internal_secret == _INTERNAL_GATEWAY_SECRET:
            x_user_id = request.headers.get("X-User-Id")
            if x_user_id:
                request.state.user = {
                    "uid": x_user_id,
                    "email": None,
                    "name": None,
                    "picture": None,
                    "claims": {},
                }
                _bind_sentry_user(x_user_id)
            return await call_next(request)
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.lower().startswith("bearer "):
            logger.info("missing_authorization_header", path=path, method=method)
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Not authenticated"})
        token = authorization.split(" ", 1)[1].strip()
        if not token:
            logger.info("empty_bearer_token", path=path, method=method)
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Not authenticated"})
        try:
            if _FIREBASE_APP is None:
                _initialize_firebase_app()
            check_revoked = _FIREBASE_CHECK_REVOKED
            decoded = auth.verify_id_token(token, check_revoked=check_revoked, app=_FIREBASE_APP)
        except auth.RevokedIdTokenError:  # type: ignore[attr-defined]
            logger.info("firebase_token_revoked", path=path, method=method)
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Token revoked"})
        except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, ValueError):  # type: ignore[attr-defined]
            logger.info("invalid_firebase_token", path=path, method=method)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication credentials"},
            )
        except Exception as exc:
            if firebase_exceptions and isinstance(exc, firebase_exceptions.FirebaseError):  # type: ignore[attr-defined]
                logger.error("Firebase verification error", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": "Authentication service unavailable"},
                )
            if isinstance(exc, RuntimeError):
                logger.error("Firebase initialization failed", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "Authentication backend misconfigured"},
                )
            logger.error("Unexpected authentication error", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication error"},
            )
        if not decoded.get("uid"):
            logger.info("missing_uid_in_token", path=path, method=method)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication credentials"},
            )
        if _FIREBASE_AUDIENCE and decoded.get("aud") not in {
            _FIREBASE_AUDIENCE,
            f"project-{_FIREBASE_AUDIENCE}",
        }:
            logger.info("firebase_token_audience_mismatch", path=path, method=method)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication credentials"},
            )
        if _FIREBASE_ISSUER and decoded.get("iss") != _FIREBASE_ISSUER:
            logger.info("firebase_token_issuer_mismatch", path=path, method=method)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication credentials"},
            )
        filtered_claims = {
            k: v for k, v in decoded.items() if k not in {"uid", "sub", "aud", "iss", "iat", "exp", "auth_time"}
        }
        uid = decoded["uid"]
        request.state.user = {
            "uid": uid,
            "email": decoded.get("email"),
            "name": decoded.get("name"),
            "picture": decoded.get("picture"),
            "claims": filtered_claims,
        }
        _bind_sentry_user(uid)
        return await call_next(request)


configure_cors_from_env(app)
add_correlation_id_middleware(app, header_name="X-Request-ID")
app.add_middleware(RateLimitMiddleware)
app.add_middleware(FirebaseAuthMiddleware)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/upstreams/health")
async def upstreams_health(request: Request) -> dict:
    headers = _forward_headers(request)
    services = {
        "rpe": RPE_SERVICE_URL,
        "exercises": EXERCISES_SERVICE_URL,
        "user_max": USER_MAX_SERVICE_URL,
        "workouts": WORKOUTS_SERVICE_URL,
        "plans": PLANS_SERVICE_URL,
        "agent": AGENT_SERVICE_URL,
        "accounts": ACCOUNTS_SERVICE_URL,
    }
    timeout = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)
    results: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        for name, base in services.items():
            if not base:
                results[name] = {"ok": False, "error": "not_configured"}
                continue
            url = f"{base}/health"
            try:
                r = await client.get(url, headers=headers, follow_redirects=True)
                ok = 200 <= r.status_code < 300
                results[name] = {
                    "ok": ok,
                    "status": r.status_code,
                    "body": (r.text[:200] if not ok else "ok"),
                    "url": url,
                }
            except Exception as exc:
                results[name] = {"ok": False, "error": type(exc).__name__, "url": url}
    return {"services": results}


@app.get("/api/v1/auth/me")
async def get_authenticated_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "name": user.get("name"),
        "picture": user.get("picture"),
        "claims": user.get("claims") or {},
    }


@app.get("/payment/success", response_class=HTMLResponse, include_in_schema=False)
async def payment_success_page() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Payment successful</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont,
        'Segoe UI', sans-serif;
      padding: 2rem;
      text-align: center;
    }
    .status { font-size: 1.4rem; margin-bottom: 0.5rem; }
    .hint { color: #555; font-size: 0.95rem; }
  </style>
</head>
<body>
  <div class=\"status\">Payment completed successfully.</div>
  <div class=\"hint\">You can close this page and return to the app.</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/payment/cancel", response_class=HTMLResponse, include_in_schema=False)
async def payment_cancel_page() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Payment cancelled</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont,
        'Segoe UI', sans-serif;
      padding: 2rem;
      text-align: center;
    }
    .status { font-size: 1.4rem; margin-bottom: 0.5rem; }
    .hint { color: #555; font-size: 0.95rem; }
  </style>
</head>
<body>
  <div class=\"status\">Payment was cancelled.</div>
  <div class=\"hint\">You can close this page and return to the app to try again.</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/stripe/connect/return", response_class=HTMLResponse, include_in_schema=False)
async def stripe_connect_return_page() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Stripe Connect onboarding</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont,
        'Segoe UI', sans-serif;
      padding: 2rem;
      text-align: center;
    }
    .status { font-size: 1.4rem; margin-bottom: 0.5rem; }
    .hint { color: #555; font-size: 0.95rem; }
  </style>
</head>
<body>
  <div class=\"status\">Stripe Connect onboarding completed.</div>
  <div class=\"hint\">You can close this page and return to the app.</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/stripe/connect/refresh", response_class=HTMLResponse, include_in_schema=False)
async def stripe_connect_refresh_page() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Stripe Connect onboarding</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont,
        'Segoe UI', sans-serif;
      padding: 2rem;
      text-align: center;
    }
    .status { font-size: 1.4rem; margin-bottom: 0.5rem; }
    .hint { color: #555; font-size: 0.95rem; }
  </style>
</head>
<body>
  <div class=\"status\">Stripe Connect onboarding needs to be refreshed.</div>
  <div class=\"hint\">You can close this page and restart onboarding from the app.</div>
</body>
</html>"""
    return HTMLResponse(content=html)


async def fetch_service_spec(url: str) -> dict:
    timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(10):
            try:
                r = await client.get(f"{url}/openapi.json", headers={"Accept": "application/json"})
                if r.status_code == 200:
                    return r.json()
                body_preview = r.text[:200] if r.text else ""
                logger.warning(
                    "openapi_fetch_non_200",
                    attempt=attempt + 1,
                    url=url,
                    status_code=r.status_code,
                    body_preview=body_preview,
                )
            except Exception as exc:
                logger.warning(
                    "openapi_fetch_error",
                    attempt=attempt + 1,
                    url=url,
                    error=str(exc),
                )
            await asyncio.sleep(2)
        logger.error("openapi_fetch_failed", url=url, attempts=attempt + 1)
        return {}


def merge_openapi_schemas(specs: list[dict], services: dict) -> dict:
    merged = {
        "openapi": "3.0.3",
        "info": {
            "title": "WorkoutApp Gateway",
            "version": "1.0",
            "description": "Aggregated API Documentation",
        },
        "paths": {},
        "components": {"schemas": {}},
    }

    service_prefixes = {
        "rpe": "/api/v1",
        "exercises": "/api/v1",
        "user_max": "/api/v1",
        "workouts": "/api/v1",
        "sessions": "/api/v1",
        "plans": "/api/v1",
    }

    for service_name, spec in zip(services.keys(), specs):
        if not spec or "paths" not in spec:
            continue
        prefix = service_prefixes.get(service_name, "")
        for path, methods in spec["paths"].items():
            full_path = f"{prefix}{path}"
            if full_path not in merged["paths"]:
                merged["paths"][full_path] = methods
            else:
                for method, operation in methods.items():
                    if method in merged["paths"][full_path]:
                        pass
                    else:
                        merged["paths"][full_path][method] = operation
        if "components" in spec and "schemas" in spec["components"]:
            merged["components"]["schemas"].update(spec["components"]["schemas"])

    return merged


@app.on_event("startup")
async def aggregate_openapi():
    fetch_on_start = os.getenv("FETCH_OPENAPI_ON_STARTUP", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not fetch_on_start:
        try:
            logger.info("Skipping OpenAPI aggregation on startup (FETCH_OPENAPI_ON_STARTUP=false)")
        except Exception:
            pass
        return
    services = {
        "rpe": RPE_SERVICE_URL,
        "exercises": EXERCISES_SERVICE_URL,
        "user_max": USER_MAX_SERVICE_URL,
        "workouts": WORKOUTS_SERVICE_URL,
        "plans": PLANS_SERVICE_URL,
    }
    try:
        logger.info(
            "upstream_urls",
            rpe=RPE_SERVICE_URL,
            exercises=EXERCISES_SERVICE_URL,
            user_max=USER_MAX_SERVICE_URL,
            workouts=WORKOUTS_SERVICE_URL,
            plans=PLANS_SERVICE_URL,
            agent=AGENT_SERVICE_URL,
        )
    except Exception:
        pass

    specs = await asyncio.gather(*[fetch_service_spec(url) for url in services.values() if url])

    merged_spec = merge_openapi_schemas(specs, services)
    for service_name, spec in zip(services.keys(), specs):
        if spec:
            logger.info("openapi_spec_fetch_success", service=service_name)
        else:
            logger.warning("openapi_spec_fetch_failed", service=service_name)
    app.openapi_schema = merged_spec


@app.post("/api/v1/openapi/refresh")
async def refresh_openapi(request: Request) -> JSONResponse:
    bg = str(request.query_params.get("background", "true")).strip().lower() in {"1", "true", "yes"}
    if bg:
        try:
            asyncio.create_task(aggregate_openapi())
        except Exception:
            await aggregate_openapi()
        return JSONResponse({"status": "scheduled"})
    else:
        await aggregate_openapi()
        return JSONResponse({"status": "ok"})


@app.post("/api/v1/profile/photo/apply")
async def apply_profile_photo(request: Request) -> JSONResponse:
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    uid = str(uid)

    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty body")

    headers = _forward_headers(request)
    headers["Content-Type"] = "image/png"

    headers["X-User-Id"] = uid
    target_url = f"{ACCOUNTS_SERVICE_URL}/avatars/apply"
    try:
        timeout = httpx.Timeout(
            connect=_DEFAULT_CONNECT_TIMEOUT,
            read=_DEFAULT_PROXY_TIMEOUT,
            write=_DEFAULT_PROXY_TIMEOUT,
            pool=_DEFAULT_PROXY_TIMEOUT,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(target_url, headers=headers, content=data, follow_redirects=True)
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to store avatar")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    xf_proto = request.headers.get("x-forwarded-proto")
    xf_host = request.headers.get("x-forwarded-host")
    host = xf_host or request.headers.get("host")
    scheme = (xf_proto or request.url.scheme or "http").split(",")[0].strip()
    public_path = f"/api/v1/avatars/{uid}.png"
    version = int(datetime.utcnow().timestamp())
    if host:
        photo_url = f"{scheme}://{host}{public_path}?v={version}"
    else:
        base_url = str(request.base_url).rstrip("/")
        photo_url = f"{base_url}{public_path}?v={version}"

    try:
        if ACCOUNTS_SERVICE_URL:
            profile_url = f"{ACCOUNTS_SERVICE_URL}/profile/me"
            profile_headers = dict(headers)
            profile_headers["Content-Type"] = "application/json"
            payload = json.dumps({"photo_url": photo_url})
            async with httpx.AsyncClient(timeout=timeout) as client:
                await client.patch(profile_url, headers=profile_headers, content=payload, follow_redirects=True)
    except Exception as e:
        logger.warning("avatar_update_profile_patch_failed", error=str(e))

    try:
        if auth is not None:
            auth.update_user(uid, photo_url=photo_url, app=_FIREBASE_APP)
    except Exception as e:
        logger.warning("avatar_update_firebase_failed", error=str(e))

    return JSONResponse({"photo_url": photo_url})


@app.post("/api/v1/avatars/generate")
async def proxy_generate_avatar(request: Request) -> Response:
    if AGENT_SERVICE_URL is None:
        raise HTTPException(status_code=503, detail="Agent service URL is not configured")

    headers = _forward_headers(request)
    target_url = f"{AGENT_SERVICE_URL}/avatars/generate"
    return await _proxy_request(request, target_url, headers)


@app.get("/api/v1/avatars/{uid}.png")
async def proxy_avatar(uid: str, request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/avatars/{uid}.png"
    return await _proxy_request(request, target_url, headers)


def _date_key_from_iso(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return iso_str[:10]
    return dt.date().isoformat()


async def _fetch_target_profile(user_id: str) -> dict:
    if not ACCOUNTS_SERVICE_URL:
        raise HTTPException(status_code=503, detail="Accounts service unavailable")
    target_url = f"{ACCOUNTS_SERVICE_URL}/profile/{user_id}"
    async with httpx.AsyncClient(timeout=_DEFAULT_PROXY_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(target_url)
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="User profile not found")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch target profile")
    data = resp.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Invalid profile response format")
    return data


app.include_router(rpe_router)
app.include_router(exercises_core_router)
app.include_router(exercises_definitions_router)
app.include_router(exercises_instances_router)
app.include_router(user_max_router)
app.include_router(workouts_router)
app.include_router(workout_metrics_router)
app.include_router(sessions_router)
app.include_router(plans_applied_router)
app.include_router(plans_calendar_router)
app.include_router(plans_instances_router)
app.include_router(plans_mesocycles_router)
app.include_router(plans_templates_router)
app.include_router(analytics_router)
app.include_router(crm_router)
app.include_router(agent_router)
