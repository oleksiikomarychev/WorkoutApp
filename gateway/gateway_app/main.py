import asyncio
import base64
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis
from sentry_sdk import set_tag, set_user
from starlette.middleware.base import BaseHTTPMiddleware

from gateway_app import schemas
from gateway_app.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")


def _normalize_env_url(var_name: str) -> Optional[str]:
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
except Exception:  # pragma: no cover
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

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# In-memory cache for profile aggregates
_PROFILE_CACHE: dict[str, dict] = {}
_PROFILE_CACHE_TTL_SECONDS = int(os.getenv("PROFILE_AGGREGATES_CACHE_TTL_SECONDS", "900"))


def _invalidate_profile_cache_for_user(uid: Optional[str]) -> None:
    """Invalidate profile aggregates cache entries for a given user."""
    if not uid:
        return
    try:
        keys = list(_PROFILE_CACHE.keys())
        for k in keys:
            if k.startswith(f"{uid}:"):
                _PROFILE_CACHE.pop(k, None)
    except Exception:
        # Best-effort invalidation; ignore errors
        pass


def _bind_sentry_user(uid: Optional[str]) -> None:
    if uid:
        set_user({"id": str(uid)})
        set_tag("service", SERVICE_NAME)
    else:
        set_user(None)


def _forward_headers(request: Request) -> Dict[str, str]:
    """Build downstream headers, ensuring X-User-Id is injected from the authenticated user."""

    allowed_header_names = {"traceparent", "x-request-id", "content-type", "accept"}
    forwarded: Dict[str, str] = {k: v for k, v in request.headers.items() if k.lower() in allowed_header_names}

    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        uid = user.get("uid")
        if uid:
            forwarded["X-User-Id"] = str(uid)

    return forwarded


def _forward_messenger_headers(request: Request) -> Dict[str, str]:
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


_FIREBASE_APP: Optional[firebase_admin.App] = None if firebase_admin else None  # type: ignore
_FIREBASE_CHECK_REVOKED = True
_FIREBASE_AUDIENCE: Optional[str] = os.getenv("FIREBASE_PROJECT_ID")
_FIREBASE_ISSUER: Optional[str] = None
_PUBLIC_PATHS = {
    "/api/v1/health",
    "/openapi.json",
    "/docs",
    "/docs/",
    "/redoc",
    "/redoc/",
    "/metrics",
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

_rate_limit_redis: Optional[Redis] = None
_rate_limit_redis_error_logged = False


async def _get_rate_limit_redis() -> Optional[Redis]:
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
    except Exception as exc:
        raise RuntimeError("FIREBASE_CREDENTIALS_BASE64 is invalid") from exc
    # Always prefer explicit env project id to avoid mismatches with service account JSON
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
        # Public avatar images do not require auth
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
        if isinstance(user, dict) and user.get("uid"):
            identifier = f"user:{user['uid']}"
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


# First attach CORS (outer)
_cors_origins = os.getenv("CORS_ORIGINS", "*")
_allow_origins = [o.strip() for o in _cors_origins.split(",")] if _cors_origins != "*" else ["*"]
_env_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# If wildcard origin is used, Starlette cannot send Access-Control-Allow-Origin with credentials enabled.
# To ensure browsers get ACAO "*", disable credentials when origins is wildcard.
_allow_credentials = False if _allow_origins == ["*"] else _env_allow_credentials

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Request-ID",
    generator=lambda: str(uuid.uuid4()),
    update_request_header=True,
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(FirebaseAuthMiddleware)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/upstreams/health")
async def upstreams_health(request: Request) -> dict:
    """Ping /health of all configured upstream services and return their statuses."""
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
    if not user or not isinstance(user, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "name": user.get("name"),
        "picture": user.get("picture"),
        "claims": user.get("claims") or {},
    }


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

    # Map service names to their gateway prefixes
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
            # Ensure the path starts with a slash and combine with the prefix
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
    # Allow disabling spec fetch on startup via ENV
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

    # Fetch OpenAPI specs from all services
    specs = await asyncio.gather(*[fetch_service_spec(url) for url in services.values() if url])

    merged_spec = merge_openapi_schemas(specs, services)
    for service_name, spec in zip(services.keys(), specs):
        if spec:
            logger.info("openapi_spec_fetch_success", service=service_name)
        else:
            logger.warning("openapi_spec_fetch_failed", service=service_name)
    app.openapi_schema = merged_spec


# On-demand OpenAPI aggregation endpoint
@app.post("/api/v1/openapi/refresh")
async def refresh_openapi(request: Request) -> JSONResponse:
    """Trigger OpenAPI aggregation on-demand.
    If query param background=true (default), runs in background.
    """
    bg = str(request.query_params.get("background", "true")).strip().lower() in {"1", "true", "yes"}
    if bg:
        try:
            asyncio.create_task(aggregate_openapi())
        except Exception:
            # Fallback to inline if scheduling fails
            await aggregate_openapi()
        return JSONResponse({"status": "scheduled"})
    else:
        await aggregate_openapi()
        return JSONResponse({"status": "ok"})


@app.post("/api/v1/profile/photo/apply")
async def apply_profile_photo(request: Request) -> JSONResponse:
    user = getattr(request.state, "user", None)
    if not user or not isinstance(user, dict) or not user.get("uid"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    uid: str = str(user["uid"])

    # Read raw body bytes (expecting image/png)
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty body")

    # Forward to accounts-service to store in Postgres
    headers = _forward_headers(request)
    headers["Content-Type"] = "image/png"
    # Ensure user id is forwarded for accounts-service dependency
    if isinstance(user, dict) and user.get("uid"):
        headers["X-User-Id"] = str(user["uid"])
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
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to store avatar")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    # Public URL proxied via gateway (add cache-busting param)
    # Use forwarded headers to construct external URL (works behind proxies/CF)
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

    # Best-effort sync of profile.photo_url in accounts-service
    try:
        if ACCOUNTS_SERVICE_URL:
            profile_url = f"{ACCOUNTS_SERVICE_URL}/profile/me"
            profile_headers = dict(headers)
            profile_headers["Content-Type"] = "application/json"
            payload = json.dumps({"photo_url": photo_url})
            async with httpx.AsyncClient(timeout=timeout) as client:
                await client.patch(profile_url, headers=profile_headers, content=payload, follow_redirects=True)
    except Exception:
        # Non-fatal; avatar remains usable even if profile update fails
        pass

    # Update Firebase user photoURL if admin SDK is available
    try:
        if auth is not None:
            auth.update_user(uid, photo_url=photo_url, app=_FIREBASE_APP)
    except Exception:
        # Non-fatal; still return the URL we saved
        pass

    return JSONResponse({"photo_url": photo_url})


@app.get("/api/v1/avatars/{uid}.png")
async def proxy_avatar(uid: str, request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/avatars/{uid}.png"
    return await _proxy_request(request, target_url, headers)


# Create routers for each service
rpe_router = APIRouter(prefix="/api/v1/rpe")
exercises_core_router = APIRouter(prefix="/api/v1/exercises")
exercises_definitions_router = APIRouter(prefix="/api/v1/exercises/definitions")
exercises_instances_router = APIRouter(prefix="/api/v1/exercises/instances")
user_max_router = APIRouter(prefix="/api/v1/user-max")
workouts_router = APIRouter(prefix="/api/v1/workouts")
sessions_router = APIRouter(prefix="/api/v1/sessions")
plans_applied_router = APIRouter(prefix="/api/v1/plans/applied-plans")
plans_calendar_router = APIRouter(prefix="/api/v1/plans/calendar-plans")
plans_instances_router = APIRouter(prefix="/api/v1/plans/calendar-plan-instances")
plans_mesocycles_router = APIRouter(prefix="/api/v1/plans/mesocycles")
plans_templates_router = APIRouter(prefix="/api/v1/plans/mesocycle-templates")
analytics_router = APIRouter(prefix="/api/v1")
crm_router = APIRouter(prefix="/api/v1/crm")


def _date_key_from_iso(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return iso_str[:10]
    return dt.date().isoformat()


async def _fetch_instances_for_workout(workout_id: int, headers: dict) -> list[dict]:
    url = f"{EXERCISES_SERVICE_URL}/exercises/instances/workouts/{workout_id}/instances"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers, follow_redirects=True)
        if res.status_code == 200:
            data = res.json() or []
            return data if isinstance(data, list) else []
    return []


def _build_set_volume_index(instances: list[dict]) -> tuple[dict[int, float], float]:
    set_volume: dict[int, float] = {}
    total = 0.0
    for inst in instances or []:
        for s in inst.get("sets", []) or []:
            sid = s.get("id")

            # Prefer computed volume (reps * weight) when weight is provided
            reps_raw = s.get("reps")
            weight_raw = s.get("weight")
            volume_raw = s.get("volume")

            reps = 0.0
            weight = None
            try:
                if reps_raw is not None:
                    reps = float(reps_raw)
            except Exception:
                reps = 0.0
            try:
                if weight_raw is not None:
                    weight = float(weight_raw)
            except Exception:
                weight = None

            volume: float | None = None
            if weight is not None and reps > 0:
                volume = round(reps * weight, 2)

            if volume is None:
                try:
                    volume = float(volume_raw)
                except Exception:
                    volume = None

            if volume is None and reps > 0 and weight is None:
                volume = round(reps, 2)

            v = volume if volume is not None else 0.0

            if isinstance(sid, int):
                set_volume[sid] = v
            total += v
    return set_volume, total


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
        raise HTTPException(status_code=502, detail="Invalid profile response")
    return data


@analytics_router.get("/profile/aggregates", response_model=schemas.ProfileAggregatesResponse)
async def get_profile_aggregates(
    request: Request,
    weeks: int = Query(48, ge=1, le=104),
    limit: int = Query(20, ge=1, le=100),
    user_id: str | None = Query(
        None,
        description="Optional target user id. Defaults to current user.",
    ),
):
    headers = _forward_headers(request)
    now = datetime.utcnow()
    grid_end = datetime(now.year, now.month, now.day)
    grid_start = grid_end - timedelta(days=weeks * 7 - 1)

    # Determine target uid
    user = getattr(request.state, "user", None)
    requester_uid = (user or {}).get("uid") if isinstance(user, dict) else None
    target_uid = user_id or requester_uid
    if target_uid is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # If requesting someone else's data, ensure their profile is public
    if user_id and user_id != requester_uid:
        profile_data = await _fetch_target_profile(user_id)
        if not profile_data.get("is_public", False):
            raise HTTPException(status_code=403, detail="Profile is private")

    # Check cache/ETag
    cache_key = f"{target_uid}:{weeks}:{limit}"
    inm = request.headers.get("if-none-match")
    cached = _PROFILE_CACHE.get(cache_key)
    if cached:
        # serve 304 if etag matches and cache not expired
        if cached.get("expires_at") and cached["expires_at"] > now and inm and inm == cached.get("etag"):
            return Response(status_code=304)
        # serve cached content if still fresh
        if cached.get("expires_at") and cached["expires_at"] > now and cached.get("content"):
            return JSONResponse(content=cached["content"], headers={"ETag": cached.get("etag", "")})

    # 1) Fetch all sessions
    sessions_url = f"{WORKOUTS_SERVICE_URL}/workouts/sessions/history/all"
    headers_for_sessions = dict(headers)
    headers_for_sessions["X-User-Id"] = target_uid
    async with httpx.AsyncClient() as client:
        resp = await client.get(sessions_url, headers=headers_for_sessions, follow_redirects=True)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch sessions history")
        sessions_raw = resp.json() or []
        if not isinstance(sessions_raw, list):
            sessions_raw = [sessions_raw]

    # 2) Filter completed sessions and date window
    completed: list[dict] = []
    for s in sessions_raw:
        status_val = str(s.get("status") or "").lower()
        finished_at = s.get("finished_at")
        started_at = s.get("started_at")
        if not started_at:
            continue
        # Parse date for filtering
        try:
            sdt = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        except Exception:
            continue
        if sdt < grid_start or sdt > grid_end + timedelta(days=1):
            # keep only for totals if needed later, but not recent window
            pass
        # consider completed
        if status_val == "completed" or finished_at is not None:
            completed.append(s)

    if not completed:
        return schemas.ProfileAggregatesResponse(
            generated_at=now,
            weeks=weeks,
            total_workouts=0,
            total_volume=0.0,
            active_days=0,
            max_day_volume=0.0,
            activity_map={},
            completed_sessions=[],
        )

    # 3) Sort desc by started_at and clip recent window for activity
    def _parse_started(s: dict) -> datetime:
        try:
            return datetime.fromisoformat(str(s.get("started_at")).replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    completed.sort(key=_parse_started, reverse=True)

    # 4) Build set-volume index per workout (with limited concurrency)
    unique_wids: list[int] = []
    seen: set[int] = set()
    for s in completed:
        wid = s.get("workout_id")
        if isinstance(wid, int) and wid not in seen:
            seen.add(wid)
            unique_wids.append(wid)

    wid_to_index: dict[int, dict[int, float]] = {}
    wid_to_total: dict[int, float] = {}

    headers_for_instances = dict(headers)
    headers_for_instances["X-User-Id"] = target_uid

    sem = asyncio.Semaphore(6)

    async def _build_for_wid(wid: int):
        async with sem:
            instances = await _fetch_instances_for_workout(wid, headers_for_instances)
            set_idx, total = _build_set_volume_index(instances)
            wid_to_index[wid] = set_idx
            wid_to_total[wid] = total

    await asyncio.gather(*[_build_for_wid(wid) for wid in unique_wids])

    # 5) Aggregate per day
    activity_map: dict[str, dict] = {}
    total_volume = 0.0
    unique_days: set[str] = set()

    for s in completed:
        started_at = s.get("started_at")
        day_key = _date_key_from_iso(str(started_at))
        unique_days.add(day_key)
        # Only count into activity window
        day_date = datetime.fromisoformat(day_key)
        if not (grid_start.date() <= day_date.date() <= grid_end.date()):
            continue

        wid = s.get("workout_id")
        progress = s.get("progress") or {}
        completed_map = progress.get("completed") or {}
        session_volume = 0.0

        if isinstance(wid, int):
            set_lookup = wid_to_index.get(wid) or {}
            # If nothing completed explicitly, fallback to total workout volume
            if not isinstance(completed_map, dict) or not any(
                isinstance(v, list) and v for v in completed_map.values()
            ):
                session_volume = wid_to_total.get(wid, 0.0)
            else:
                for v in completed_map.values():
                    if isinstance(v, list):
                        for sid in v:
                            if isinstance(sid, int):
                                session_volume += float(set_lookup.get(sid, 0.0))

        total_volume += session_volume
        cur = activity_map.get(day_key)
        if not cur:
            activity_map[day_key] = {"session_count": 1, "volume": session_volume}
        else:
            cur["session_count"] += 1
            cur["volume"] += session_volume

    # 6) Compute max_day_volume
    max_day_volume = 0.0
    for v in activity_map.values():
        vol = float(v.get("volume", 0.0))
        if vol > max_day_volume:
            max_day_volume = vol

    # 7) Build response sessions (last N)
    last_sessions: list[schemas.SessionLite] = []
    for s in completed[:limit]:
        last_sessions.append(
            schemas.SessionLite(
                id=int(s.get("id")),
                workout_id=int(s.get("workout_id")),
                started_at=datetime.fromisoformat(str(s.get("started_at")).replace("Z", "+00:00")),
                finished_at=(
                    datetime.fromisoformat(str(s.get("finished_at")).replace("Z", "+00:00"))
                    if s.get("finished_at")
                    else None
                ),
                status=str(s.get("status") or ""),
            )
        )

    # 8) Cast activity map into schema type
    typed_activity: dict[str, schemas.DayActivity] = {
        k: schemas.DayActivity(session_count=int(v.get("session_count", 0)), volume=float(v.get("volume", 0.0)))
        for k, v in activity_map.items()
    }

    # Build final content dict for stable ETag
    content_model = schemas.ProfileAggregatesResponse(
        generated_at=now,
        weeks=weeks,
        total_workouts=len(completed),
        total_volume=float(total_volume),
        active_days=len({k for k in (_date_key_from_iso(str(s.get("started_at"))) for s in completed)}),
        max_day_volume=float(max_day_volume),
        activity_map=typed_activity,
        completed_sessions=last_sessions,
    )
    # Encode datetimes and nested models to JSON-serializable structures
    content = jsonable_encoder(content_model, custom_encoder={datetime: lambda v: v.isoformat()})

    # Compute ETag and cache
    try:
        etag = hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    except Exception:
        etag = ""
    _PROFILE_CACHE[cache_key] = {
        "etag": etag,
        "content": content,
        "expires_at": now + timedelta(seconds=_PROFILE_CACHE_TTL_SECONDS),
    }
    # Handle If-None-Match post-compute
    if inm and inm == etag:
        return Response(status_code=304)
    return JSONResponse(content=content, headers={"ETag": etag})


# Agent-service proxies
@app.post("/api/v1/agent/plan-mass-edit")
async def agent_plan_mass_edit(request: Request) -> Response:
    """Proxy LLM-driven plan mass edit to agent-service.

    Gateway path:   /api/v1/agent/plan-mass-edit
    Upstream path:  {AGENT_SERVICE_URL}/agent/plan-mass-edit
    """

    headers = _forward_headers(request)
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("uid"):
        # agent-service relies on this header in some endpoints
        headers["X-User-Id"] = str(user["uid"])
    target_url = f"{AGENT_SERVICE_URL}/agent/plan-mass-edit"
    return await _proxy_request(request, target_url, headers)


# Avatars proxy to agent-service
@app.post("/api/v1/avatars/generate")
async def avatars_generate(request: Request) -> Response:
    headers = _forward_headers(request)
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("uid"):
        headers["X-User-Id"] = str(user["uid"])  # needed by agent-service
    target_url = f"{AGENT_SERVICE_URL}/avatars/generate"
    return await _proxy_request(request, target_url, headers)


@app.api_route(
    "/api/v1/social{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy_social(request: Request, path: str = "") -> Response:
    if not SOCIAL_API_URL:
        raise HTTPException(status_code=503, detail="Social API is not configured")
    target_url = _build_messenger_target(SOCIAL_API_URL, path)
    headers = _forward_messenger_headers(request)
    return await _proxy_request(request, target_url, headers)


@app.api_route(
    "/api/v1/messaging{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy_messaging(request: Request, path: str = "") -> Response:
    if not MESSAGING_API_URL:
        raise HTTPException(status_code=503, detail="Messaging API is not configured")
    target_url = _build_messenger_target(MESSAGING_API_URL, path)
    headers = _forward_messenger_headers(request)
    return await _proxy_request(request, target_url, headers)


async def _proxy_request(request: Request, target_url: str, headers: dict) -> Response:
    method = request.method
    params = dict(request.query_params)

    timeout_seconds = _DEFAULT_PROXY_TIMEOUT
    if "plans/applied-plans/apply" in target_url:
        timeout_seconds = _PLANS_APPLY_TIMEOUT

    timeout = httpx.Timeout(
        connect=_DEFAULT_CONNECT_TIMEOUT,
        read=timeout_seconds,
        write=timeout_seconds,
        pool=timeout_seconds,
    )

    # Retry only for idempotent methods (GET/HEAD) on connection/timeout errors
    attempts = 1
    max_attempts = _GET_RETRIES if method in ("GET", "HEAD") else 1
    while attempts <= max_attempts:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method in ("POST", "PUT", "PATCH"):
                    body = await request.body()
                    r = await client.request(
                        method,
                        target_url,
                        params=params,
                        headers=headers,
                        content=body,
                        follow_redirects=True,
                    )
                else:
                    r = await client.request(
                        method,
                        target_url,
                        params=params,
                        headers=headers,
                        follow_redirects=True,
                    )
            break
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            if attempts >= max_attempts:
                if isinstance(exc, httpx.TimeoutException):
                    logger.error(
                        "Proxy request timed out",
                        logger.error(
                            "proxy_request_timed_out",
                            target_url=target_url,
                            method=method,
                            params=params,
                            attempt=attempts,
                            exc_info=True,
                        ),
                    )
                raise HTTPException(status_code=504, detail="Upstream service timeout") from exc
            logger.error(
                "proxy_request_failed_before_response",
                target_url=target_url,
                method=method,
                params=params,
                attempt=attempts,
                exc_info=True,
            )
            raise HTTPException(status_code=502, detail="Upstream service error") from exc
        except httpx.HTTPError as exc:
            # Non-retryable httpx errors
            logger.error(
                "proxy_request_failed_before_response",
                target_url=target_url,
                method=method,
                params=params,
                exc_info=True,
            )
            raise HTTPException(status_code=502, detail="Upstream service error") from exc

    if r.status_code >= 400:
        body_preview = r.text
        if len(body_preview) > 1000:
            body_preview = f"{body_preview[:1000]}..."
        logger.error(
            "proxy_request_failed",
            target_url=target_url,
            status_code=r.status_code,
            response_body=body_preview,
            method=method,
            params=params,
        )

    ct = r.headers.get("content-type", "application/json")
    if r.status_code == 204:
        return Response(status_code=204)
    if "application/json" in ct.lower():
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return Response(content=r.content, status_code=r.status_code, media_type=ct)
    # Non-JSON: pass through raw content (e.g., image/png)
    return Response(content=r.content, status_code=r.status_code, media_type=ct)


async def _derive_exercise_instances_from_plan(
    *,
    applied_plan_id: int | None,
    plan_order_index: int | None,
    workout_name: str | None,
    workout_id: int,
    headers: dict,
) -> list[dict]:
    """Build exercise_instances for a generated workout from the applied plan structure.

    Strategy:
    1) Fetch applied plan details from plans-service.
    2) Flatten plan workouts in a deterministic global order (meso->micro->plan_workouts by order_index, id).
    3) Prefer matching by plan_order_index; if missing, attempt to match by day label parsed from workout name.
    """
    try:
        if not applied_plan_id:
            return []

        plan_url = f"{PLANS_SERVICE_URL}/plans/applied-plans/{applied_plan_id}"
        async with httpx.AsyncClient() as client:
            res = await client.get(plan_url, headers=headers)
            if res.status_code != 200:
                logger.warning(
                    "plan_fetch_failed",
                    status_code=res.status_code,
                    body=res.text,
                    url=plan_url,
                )
                return []
            plan = res.json()

        calendar_plan = (plan or {}).get("calendar_plan") or {}
        mesocycles = calendar_plan.get("mesocycles") or []

        def _sort_meso(m: dict):
            return (m.get("order_index", 0), m.get("id", 0))

        def _sort_micro(mc: dict):
            return (mc.get("order_index", 0), mc.get("id", 0))

        def _sort_workout(pw: dict):
            return (pw.get("order_index", 0), pw.get("id", 0))

        # Optionally parse day label from workout name, e.g. "M1-MC2-D2: Day 2" or "... - Workout 1"
        day_label_target: str | None = None
        if not isinstance(plan_order_index, int) and workout_name:
            m = re.search(r":\s*(Day\s*\d+)", workout_name)
            if m:
                day_label_target = m.group(1)

        current_index = -1
        for meso in sorted(mesocycles, key=_sort_meso):
            for micro in sorted((meso.get("microcycles") or []), key=_sort_micro):
                for pw in sorted((micro.get("plan_workouts") or []), key=_sort_workout):
                    current_index += 1

                    # If matching by day label when plan_order_index is not available
                    if plan_order_index is None and day_label_target and pw.get("day_label") != day_label_target:
                        continue

                    # Build instances for this plan workout
                    instances = []
                    for ex in pw.get("exercises") or []:
                        sets = []
                        for s in ex.get("sets") or []:
                            sets.append(
                                {
                                    "id": None,
                                    "reps": s.get("volume"),
                                    "weight": s.get("working_weight"),  # may be None
                                    "rpe": s.get("effort"),
                                    "effort": s.get("effort"),
                                    "effort_type": "RPE",
                                    "intensity": s.get("intensity"),
                                    "order": None,
                                }
                            )
                        instances.append(
                            {
                                "id": None,
                                "exercise_list_id": ex.get("exercise_definition_id"),
                                "sets": sets,
                                "notes": None,
                                "order": None,
                                "workout_id": workout_id,
                                "user_max_id": None,
                            }
                        )

                    # Return on first match by index or by day label
                    if isinstance(plan_order_index, int):
                        if current_index == plan_order_index:
                            return instances
                    else:
                        # If matching by day label, return the first day's instances
                        if day_label_target:
                            return instances

    except Exception as exc:
        logger.warning("plan_instance_derivation_failed", error=str(exc), applied_plan_id=applied_plan_id)
    return []


# -------- Shared workout assembler (BFF) --------
def _parse_include_expand(request: Request) -> set[str]:
    """Parse include/expand query params into a set of dot-paths."""
    tokens: set[str] = set()
    include = request.query_params.get("include")
    expand = request.query_params.get("expand")
    for raw in (include, expand):
        if not raw:
            continue
        for part in raw.split(","):
            part = part.strip()
            if part:
                tokens.add(part)
    return tokens


async def _assemble_workout_for_client(
    *,
    workout_data: dict,
    workout_id: int,
    headers: dict,
    include: set[str],
) -> dict:
    """Ensure workout_data has exercise_instances and optional enrichments.

    Strategy:
    1) Try to fetch real instances from exercises-service.
    2) Else map workouts-service 'exercises' → 'exercise_instances'.
    3) Else derive from plan via _derive_exercise_instances_from_plan.
    4) Enrich with exercise definitions when requested via include/expand.
    5) Remove raw 'exercises' field from output.
    """
    # 1) Try real instances first
    instances_data: list[dict] = []
    instances_url = f"{EXERCISES_SERVICE_URL}/exercises/instances/workouts/{workout_id}/instances"
    try:
        async with httpx.AsyncClient() as client:
            logger.debug("instances_fetch_start", url=instances_url)
            instances_res = await client.get(instances_url, headers=headers, follow_redirects=True)
            logger.debug("instances_fetch_response", status_code=instances_res.status_code)
            if instances_res.status_code == 200:
                instances_data = instances_res.json() or []
            else:
                logger.warning(
                    "instances_fetch_non_200",
                    status_code=instances_res.status_code,
                    body=instances_res.text,
                    url=instances_url,
                )
    except Exception as exc:
        logger.warning("instances_fetch_failed", workout_id=workout_id, error=str(exc))

    # 2) Fallbacks only when instances are unavailable
    if not instances_data:
        # Determine workout type to scope fallbacks
        workout_type = str(workout_data.get("workout_type") or "").lower()
        if workout_type == "generated":
            # 2a) Map from workouts-service embedded exercises (generated path)
            exercises = workout_data.get("exercises") or []
            if exercises:
                mapped_instances: list[dict] = []
                for ex in exercises:
                    sets = []
                    for s in ex.get("sets", []):
                        # Keep compact client schema but include effort as a separate field for consistency
                        sets.append(
                            {
                                "id": None,
                                "reps": s.get("volume"),
                                "weight": s.get("working_weight")
                                if s.get("working_weight") is not None
                                else s.get("weight"),
                                "rpe": s.get("effort"),
                                "effort": s.get("effort"),
                                "effort_type": "RPE",
                                "intensity": s.get("intensity"),
                                "order": None,
                            }
                        )
                    mapped_instances.append(
                        {
                            "id": None,
                            "exercise_list_id": ex.get("exercise_id"),
                            "sets": sets,
                            "notes": ex.get("notes"),
                            "order": None,
                            "workout_id": workout_id,
                            "user_max_id": None,
                        }
                    )
                workout_data["exercise_instances"] = mapped_instances
            else:
                # 2b) Plan-based fallback for generated workouts
                plan_instances = await _derive_exercise_instances_from_plan(
                    applied_plan_id=workout_data.get("applied_plan_id"),
                    plan_order_index=workout_data.get("plan_order_index"),
                    workout_name=workout_data.get("name"),
                    workout_id=workout_id,
                    headers=headers,
                )
                if plan_instances:
                    workout_data["exercise_instances"] = plan_instances
                else:
                    workout_data["exercise_instances"] = workout_data.get("exercise_instances", [])
        else:
            # Manual workouts: do NOT overwrite instances with embedded plan/exercises snapshot
            # Keep existing instances as-is (or empty) to avoid showing stale values after refresh
            workout_data["exercise_instances"] = workout_data.get("exercise_instances", [])
    else:
        workout_data["exercise_instances"] = instances_data

    # 4) Optional enrichments
    if any("exercise_instances.exercise_definition" in inc or inc == "exercise_definition" for inc in include):
        try:
            ids = [i.get("exercise_list_id") for i in workout_data.get("exercise_instances", [])]
            ids = [int(i) for i in ids if isinstance(i, (int, str)) and str(i).isdigit()]
            if ids:
                q = ",".join(str(i) for i in sorted(set(ids)))
                defs_url = f"{EXERCISES_SERVICE_URL}/exercises/definitions"
                async with httpx.AsyncClient() as client:
                    defs_res = await client.get(defs_url, headers=headers, params={"ids": q}, follow_redirects=True)
                    if defs_res.status_code == 200:
                        defs_list = defs_res.json() or []
                        by_id = {int(d.get("id")): d for d in defs_list if d and d.get("id") is not None}
                        for inst in workout_data.get("exercise_instances", []):
                            ex_id = inst.get("exercise_list_id")
                            if isinstance(ex_id, (int, str)) and str(ex_id).isdigit():
                                inst["exercise_definition"] = by_id.get(int(ex_id))
        except Exception as exc:
            logger.warning("exercise_definition_enrich_failed", error=str(exc))

    # 5) Do not expose raw workouts-service 'exercises' to clients
    workout_data.pop("exercises", None)
    return workout_data


# RPE routes
@rpe_router.api_route("{path:path}", methods=["GET", "POST"])
async def proxy_rpe(request: Request, path: str = "") -> Response:
    target_url = f"{RPE_SERVICE_URL}/rpe{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


@workouts_router.put("/sessions/{session_id}/instances/{instance_id}/sets/{set_id}/completion")
async def complete_set_for_session(session_id: int, instance_id: int, set_id: int, request: Request) -> Response:
    """BFF: Toggle set completion and return updated WorkoutSession.

    Steps:
    1) Forward set field updates to exercises-service (allows {reps, weight, rpe, order, completed}).
    2) Fetch exercise instance to obtain workout_id.
    3) Fetch active session by workout_id from workouts-service.
    4) Update session.progress.completed for the instance/set and return the session JSON.
    """
    headers = _forward_headers(request)
    body_bytes = await request.body()
    payload = {}
    try:
        if body_bytes:
            payload = await request.json()
    except Exception:
        payload = {}

    # 1) Forward to exercises-service to persist set changes
    ex_url = f"{EXERCISES_SERVICE_URL}/exercises/instances/{instance_id}/sets/{set_id}"
    async with httpx.AsyncClient() as client:
        ex_res = await client.put(ex_url, headers=headers, content=body_bytes)
        # Even if update fails, bubble up error
        if ex_res.status_code not in (200, 201):
            try:
                return JSONResponse(status_code=ex_res.status_code, content=ex_res.json())
            except Exception:
                return Response(
                    status_code=ex_res.status_code,
                    content=ex_res.content,
                    media_type=ex_res.headers.get("content-type", "application/json"),
                )

    # 2) Fetch instance to derive workout_id
    workout_id: int | None = None
    try:
        inst_url = f"{EXERCISES_SERVICE_URL}/exercises/instances/{instance_id}"
        async with httpx.AsyncClient() as client:
            inst_res = await client.get(inst_url, headers=headers)
            if inst_res.status_code == 200:
                inst_data = inst_res.json() or {}
                if isinstance(inst_data, dict):
                    wid = inst_data.get("workout_id")
                    if isinstance(wid, int):
                        workout_id = wid
    except Exception:
        pass

    # 3) Persist progress in workouts-service and return that session
    desired_completed = bool(payload.get("completed", True))
    try:
        ws_prog_url = f"{WORKOUTS_SERVICE_URL}/workouts/sessions/{session_id}/progress"
        prog_payload = {
            "instance_id": instance_id,
            "set_id": set_id,
            "completed": desired_completed,
        }
        async with httpx.AsyncClient() as client:
            prog_res = await client.put(ws_prog_url, headers=headers, json=prog_payload)
            if prog_res.status_code in (200, 201):
                session_data = prog_res.json()
                # Ensure started_at non-null ISO string
                if not session_data.get("started_at"):
                    import datetime as _dt

                    session_data["started_at"] = _dt.datetime.utcnow().isoformat()
                return JSONResponse(content=session_data)
    except Exception:
        pass

    # Fallback: fetch active session, merge locally and return
    session_data = None
    if isinstance(workout_id, int):
        try:
            ws_url = f"{WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/active"
            async with httpx.AsyncClient() as client:
                ws_res = await client.get(ws_url, headers=headers)
                if ws_res.status_code == 200:
                    session_data = ws_res.json()
        except Exception:
            session_data = None

    if not isinstance(session_data, dict):
        session_data = {
            "id": session_id,
            "workout_id": workout_id,
            "started_at": None,
            "ended_at": None,
            "status": "active",
            "duration_seconds": None,
            "progress": {},
        }

    progress = session_data.get("progress") or {}
    if not isinstance(progress, dict):
        progress = {}
    completed_map = progress.get("completed") or {}
    if not isinstance(completed_map, dict):
        completed_map = {}
    key = str(instance_id)
    current_list = completed_map.get(key)
    if not isinstance(current_list, list):
        current_list = []
    if desired_completed:
        if set_id not in current_list:
            current_list.append(set_id)
    else:
        current_list = [sid for sid in current_list if sid != set_id]
    completed_map[key] = current_list
    progress["completed"] = completed_map
    session_data["progress"] = progress
    try:
        if not session_data.get("started_at"):
            import datetime as _dt

            session_data["started_at"] = _dt.datetime.utcnow().isoformat()
    except Exception:
        pass
    return JSONResponse(content=session_data)


# Exercises core routes
@exercises_core_router.api_route("{path:path}", methods=["GET"])
async def proxy_exercises_core(request: Request, path: str = "") -> Response:
    target_url = f"{EXERCISES_SERVICE_URL}/exercises{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Exercises definitions routes
@exercises_definitions_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_exercises_definitions(request: Request, path: str = "") -> Response:
    target_url = f"{EXERCISES_SERVICE_URL}/exercises/definitions{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Exercises instances routes
@exercises_instances_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_exercises_instances(request: Request, path: str = "") -> Response:
    target_url = f"{EXERCISES_SERVICE_URL}/exercises/instances{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# User Max routes
@user_max_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_user_max(request: Request, path: str = "") -> Response:
    target_url = f"{USER_MAX_SERVICE_URL}/user-max{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Workouts routes
@workouts_router.post("/", response_model=schemas.WorkoutResponseWithExercises, status_code=status.HTTP_201_CREATED)
async def create_workout(workout_data: schemas.WorkoutCreateWithExercises, request: Request):
    headers = _forward_headers(request)

    try:
        # Создание тренировки
        workout_url = f"{WORKOUTS_SERVICE_URL}/workouts/"
        async with httpx.AsyncClient() as client:
            workout_payload = workout_data.model_dump_json(exclude={"exercise_instances"})
            workout_resp = await client.post(workout_url, content=workout_payload, headers=headers)
            workout_resp.raise_for_status()

            workout = workout_resp.json()
            workout_id = workout["id"]

            # Создание инстансов
            if workout_data.exercise_instances:
                instances_url = f"{EXERCISES_SERVICE_URL}/exercises/instances/workouts/{workout_id}/instances"
                created_instances = []

                for instance in workout_data.exercise_instances:
                    instance_data = instance.model_dump_json()
                    instance_resp = await client.post(
                        instances_url, content=instance_data, headers=headers, follow_redirects=True
                    )

                    if instance_resp.status_code != 201:
                        # Compensation: delete workout if instance creation fails
                        await client.delete(f"{workout_url}{workout_id}", headers=headers, follow_redirects=True)
                        return JSONResponse(
                            content={
                                "detail": "Failed to create exercise instance",
                                "error": instance_resp.json(),
                            },
                            status_code=instance_resp.status_code,
                        )
                    created_instances.append(instance_resp.json())

                # Add instances to workout response
                workout["exercise_instances"] = created_instances

        return JSONResponse(content=workout, status_code=201)
    except httpx.HTTPStatusError as e:
        # Если создание инстансов провалилось, удаляем тренировку
        if "workout_id" in locals():
            async with httpx.AsyncClient() as cleanup_client:
                await cleanup_client.delete(f"{workout_url}{workout_id}/", headers=headers)
        return JSONResponse(content={"detail": str(e)}, status_code=e.response.status_code)


@workouts_router.get("/", response_model=List[schemas.WorkoutResponse])
async def list_workouts(request: Request, skip: int = 0, limit: int = 100) -> Response:
    # Forward all original query params (including applied_plan_id, type, etc.)
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


@workouts_router.get("/{workout_id}", response_model=schemas.WorkoutResponseWithExercises)
async def get_workout(workout_id: int, request: Request):
    headers = _forward_headers(request)

    # Get workout
    workout_url = f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
    async with httpx.AsyncClient() as client:
        workout_res = await client.get(workout_url, headers=headers)
        logger.debug(
            "workout_fetch_response",
            url=workout_url,
            status_code=workout_res.status_code,
        )
        if workout_res.status_code != 200:
            return JSONResponse(content=workout_res.json(), status_code=workout_res.status_code)
        workout_data = workout_res.json()

    include = _parse_include_expand(request)
    workout_data = await _assemble_workout_for_client(
        workout_data=workout_data,
        workout_id=workout_id,
        headers=headers,
        include=include,
    )
    logger.debug("workout_fetch_completed", workout_id=workout_id)
    return JSONResponse(content=workout_data)


@workouts_router.get("/sessions/{workout_id}/history")
async def get_workout_session_history(workout_id: int, request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/history"
    return await _proxy_request(request, target_url, headers)


@workouts_router.get("/sessions/history/all")
async def get_all_workouts_sessions_history(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/sessions/history/all"
    return await _proxy_request(request, target_url, headers)


@workouts_router.post("/schedule/shift-in-plan")
async def shift_schedule_in_plan_proxy(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/schedule/shift-in-plan"
    return await _proxy_request(request, target_url, headers)


@workouts_router.post("/schedule/shift-in-plan-async")
async def shift_schedule_in_plan_async_proxy(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/schedule/shift-in-plan-async"
    return await _proxy_request(request, target_url, headers)


@workouts_router.get("/schedule/tasks/{task_id}")
async def get_schedule_task_status_proxy(task_id: str, request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/schedule/tasks/{task_id}"
    return await _proxy_request(request, target_url, headers)


@analytics_router.get("/profile/me")
async def proxy_profile_me(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/profile/me"
    return await _proxy_request(request, target_url, headers)


@analytics_router.patch("/profile/me")
async def proxy_update_profile_me(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/profile/me"
    return await _proxy_request(request, target_url, headers)


@analytics_router.patch("/profile/me/coaching")
async def proxy_update_profile_coaching(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/profile/me/coaching"
    return await _proxy_request(request, target_url, headers)


@analytics_router.get("/users/all")
async def proxy_users_all(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/users/all"
    return await _proxy_request(request, target_url, headers)


@analytics_router.get("/profile/{user_id}")
async def proxy_profile_by_id(user_id: str, request: Request) -> Response:
    """Proxy to accounts-service to fetch profile by arbitrary user_id.

    Gateway path: /api/v1/profile/{user_id}
    Upstream:     {ACCOUNTS_SERVICE_URL}/profile/{user_id}
    """
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/profile/{user_id}"
    return await _proxy_request(request, target_url, headers)


@analytics_router.get("/profile/settings")
async def proxy_profile_settings(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/profile/settings"
    return await _proxy_request(request, target_url, headers)


@analytics_router.patch("/profile/settings")
async def proxy_update_profile_settings(request: Request) -> Response:
    headers = _forward_headers(request)
    target_url = f"{ACCOUNTS_SERVICE_URL}/profile/settings"
    return await _proxy_request(request, target_url, headers)


@crm_router.api_route("/relationships{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_crm_relationships(path: str = "", request: Request = None) -> Response:  # type: ignore[assignment]
    if request is None:
        raise HTTPException(status_code=500, detail="Request context missing")
    headers = _forward_headers(request)
    target_url = f"{CRM_SERVICE_URL}/crm/relationships{path}"
    return await _proxy_request(request, target_url, headers)


@crm_router.api_route("/coach{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_crm_coach(path: str = "", request: Request = None) -> Response:  # type: ignore[assignment]
    if request is None:
        raise HTTPException(status_code=500, detail="Request context missing")
    headers = _forward_headers(request)
    target_url = f"{CRM_SERVICE_URL}/crm/coach{path}"
    return await _proxy_request(request, target_url, headers)


@crm_router.api_route("/analytics{path:path}", methods=["GET", "POST"])
async def proxy_crm_analytics(path: str = "", request: Request = None) -> Response:  # type: ignore[assignment]
    if request is None:
        raise HTTPException(status_code=500, detail="Request context missing")
    headers = _forward_headers(request)
    target_url = f"{CRM_SERVICE_URL}/crm/analytics{path}"
    return await _proxy_request(request, target_url, headers)


@analytics_router.get("/workout-metrics")
async def get_workout_metrics(
    request: Request,
    plan_id: int | None = None,
    metric_x: str = Query(..., description="One of: volume, effort, kpsh, reps, 1rm"),
    metric_y: str = Query(..., description="One of: volume, effort, kpsh, reps, 1rm"),
    date_from: str | None = Query(None, description="ISO8601 start date"),
    date_to: str | None = Query(None, description="ISO8601 end date"),
):
    """
    Aggregate workout metrics for analytics.
    - volume (kg): sum(weight * reps) per workout
    - effort (RPE): average set effort, fallback to session rpe
    - kpsh: total reps for barbell exercises only
    - reps: total reps across all sets
    - 1rm: time series based on user-max records (max verified/true/estimated per date)
    """
    headers = _forward_headers(request)
    allowed = {"volume", "effort", "kpsh", "reps", "1rm"}

    def _norm_metric(m: str) -> str:
        m = (m or "").strip().lower()
        return "1rm" if m in {"1rm", "one_rm", "one-rm"} else m

    def _is_implement(equip: str | None) -> bool:
        if not equip:
            return False
        e = equip.strip().lower()
        return e not in {"", "bodyweight", "bw", "none", "no_equipment"}

    mx = _norm_metric(metric_x)
    my = _norm_metric(metric_y)
    if not mx or not my or mx not in allowed or my not in allowed:
        return JSONResponse(
            status_code=400,
            content={"detail": f"metric_x and metric_y must be in {sorted(list(allowed))}"},
        )

    # Date range: default last 90 days
    def _parse_dt(s: str | None) -> datetime | None:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    end_dt = _parse_dt(date_to) or datetime.utcnow()
    start_dt = _parse_dt(date_from) or (end_dt - timedelta(days=90))

    # 1) Fetch workouts list scoped by plan (and filter by date on scheduled_for)
    list_params: Dict[str, str | int] = {"skip": 0, "limit": 1000}
    if isinstance(plan_id, int):
        list_params["applied_plan_id"] = plan_id

    workouts_summary: List[dict] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
            r = await client.get(f"{WORKOUTS_SERVICE_URL}/workouts/", headers=headers, params=list_params)
            if r.status_code == 200:
                workouts_summary = r.json() or []
    except Exception:
        workouts_summary = []

    # Preselect by scheduled_for when available
    def _within(d: str | None) -> bool:
        if not d:
            return True
        try:
            dt = datetime.fromisoformat(d)
            return start_dt <= dt <= end_dt
        except Exception:
            return True

    preselected = [w for w in workouts_summary if _within(w.get("scheduled_for"))]
    workout_ids = [w.get("id") for w in preselected if isinstance(w.get("id"), int)]

    # 2) Fetch details and instances for each workout in parallel
    details: Dict[int, dict] = {}
    instances_by_workout: Dict[int, List[dict]] = {}
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:

        async def fetch_detail(wid: int):
            try:
                res = await client.get(f"{WORKOUTS_SERVICE_URL}/workouts/{wid}", headers=headers)
                if res.status_code == 200:
                    details[wid] = res.json()
            except Exception:
                pass

        async def fetch_instances(wid: int):
            try:
                res = await client.get(
                    f"{EXERCISES_SERVICE_URL}/exercises/instances/workouts/{wid}/instances",
                    headers=headers,
                )
                if res.status_code == 200 and isinstance(res.json(), list):
                    instances_by_workout[wid] = res.json()
            except Exception:
                pass

        await asyncio.gather(*[fetch_detail(wid) for wid in workout_ids])
        await asyncio.gather(*[fetch_instances(wid) for wid in workout_ids])

    # 3) Fetch exercise definitions once for equipment detection
    exercise_ids: set[int] = set()
    for d in details.values():
        for ex in d.get("exercises") or []:
            ex_id = ex.get("exercise_id")
            if isinstance(ex_id, int):
                exercise_ids.add(ex_id)
    # Include from instances as well
    for inst_list in instances_by_workout.values():
        for inst in inst_list or []:
            ex_id = inst.get("exercise_list_id")
            if isinstance(ex_id, int):
                exercise_ids.add(ex_id)

    equipment_by_ex_id: Dict[int, str] = {}
    if exercise_ids:
        ids_query = ",".join(str(i) for i in sorted(exercise_ids))
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
                res = await client.get(
                    f"{EXERCISES_SERVICE_URL}/exercises/definitions",
                    headers=headers,
                    params={"ids": ids_query},
                    follow_redirects=True,
                )
                if res.status_code == 200:
                    defs = res.json() or []
                    for d in defs:
                        if isinstance(d, dict) and isinstance(d.get("id"), int):
                            equipment_by_ex_id[int(d["id"])] = (d.get("equipment") or "").lower()
        except Exception:
            pass

    # 4) Compute metrics per workout/date
    def _pick_date(d: dict) -> datetime | None:
        for k in ("completed_at", "started_at", "scheduled_for"):
            v = d.get(k)
            if v:
                try:
                    return datetime.fromisoformat(v)
                except Exception:
                    continue
        return None

    items: List[dict] = []
    for wid, d in details.items():
        dt = _pick_date(d)
        if dt and (dt < start_dt or dt > end_dt):
            continue

        # From workouts-service data
        total_reps = 0
        total_eff_list: List[float] = []
        volume_kg_ws = 0.0
        kpsh = 0

        for ex in d.get("exercises") or []:
            ex_id = ex.get("exercise_id")
            equip = equipment_by_ex_id.get(ex_id, "") if isinstance(ex_id, int) else ""
            is_impl = _is_implement(equip)
            for s in ex.get("sets") or []:
                reps = s.get("volume") or 0
                w = s.get("working_weight")
                try:
                    reps = int(reps)
                except Exception:
                    reps = 0
                total_reps += reps
                if isinstance(s.get("effort"), (int, float)):
                    total_eff_list.append(float(s["effort"]))
                if isinstance(w, (int, float)) and reps:
                    volume_kg_ws += float(w) * reps
                # КПШ: считаем подъемы для любого снаряда (не bodyweight/none),
                # а также если явно указан вес у сета
                if is_impl or isinstance(w, (int, float)):
                    kpsh += reps

        # From exercise instances (fallback when no working_weight present)
        volume_kg_inst = 0.0
        if wid in instances_by_workout:
            for inst in instances_by_workout.get(wid, []) or []:
                equip = equipment_by_ex_id.get(inst.get("exercise_list_id"), "")
                is_impl = _is_implement(equip)
                for s in inst.get("sets") or []:
                    reps = s.get("reps") or s.get("volume") or 0
                    weight = s.get("weight")
                    try:
                        reps = int(reps)
                    except Exception:
                        reps = 0
                    if isinstance(weight, (int, float)) and reps:
                        volume_kg_inst += float(weight) * reps
                    # КПШ: любой снаряд либо явное наличие веса
                    if is_impl or isinstance(weight, (int, float)):
                        kpsh += reps

        avg_effort = None
        if total_eff_list:
            avg_effort = sum(total_eff_list) / len(total_eff_list)
        elif isinstance(d.get("rpe_session"), (int, float)):
            avg_effort = float(d["rpe_session"])  # session-level fallback

        volume_final = volume_kg_ws if volume_kg_ws > 0 else volume_kg_inst

        _d = _pick_date(d)
        items.append(
            {
                "date": (_d.date().isoformat() if _d else None),
                "workout_id": wid,
                "values": {
                    "volume": round(volume_final, 2) if volume_final is not None else None,
                    "effort": round(avg_effort, 2) if avg_effort is not None else None,
                    "kpsh": int(kpsh),
                    "reps": int(total_reps),
                },
            }
        )

    # 5) Optional: 1RM series from user-max-service
    one_rm_series: List[dict] = []
    if mx == "1rm" or my == "1rm":
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
                r = await client.get(
                    f"{USER_MAX_SERVICE_URL}/user-max/",
                    headers=headers,
                    params={"skip": 0, "limit": 10000},
                )
                if r.status_code == 200:
                    data = r.json() or []
                else:
                    data = []
        except Exception:
            data = []

        # Group by date (YYYY-MM-DD) and take max verified/true/estimated 1RM per date
        by_day: Dict[str, float] = {}
        for um in data:
            try:
                dstr = um.get("date")
                if not dstr:
                    continue
                d_dt = datetime.fromisoformat(dstr)
                if d_dt < start_dt or d_dt > end_dt:
                    continue
                v = None
                if isinstance(um.get("verified_1rm"), (int, float)):
                    v = float(um["verified_1rm"])
                elif isinstance(um.get("true_1rm"), (int, float)):
                    v = float(um["true_1rm"])
                else:
                    # Estimate via Epley as a fallback
                    mw = um.get("max_weight")
                    rp = um.get("rep_max")
                    if isinstance(mw, (int, float)) and isinstance(rp, int):
                        v = float(mw) * (1.0 + (rp / 30.0))
                if v is None:
                    continue
                day_key = d_dt.date().isoformat()
                current = by_day.get(day_key)
                by_day[day_key] = max(current, v) if current is not None else v
            except Exception:
                continue
        one_rm_series = [{"date": k, "value": round(v, 2)} for k, v in sorted(by_day.items())]

    return JSONResponse(
        content={
            "plan_id": plan_id,
            "range": {"from": start_dt.isoformat(), "to": end_dt.isoformat()},
            "items": items,
            "one_rm": one_rm_series,
            "allowed_metrics": sorted(list(allowed)),
            "requested": {"x": mx, "y": my},
        }
    )


@workouts_router.get("/{workout_id}/next", response_model=schemas.WorkoutResponseWithExercises)
async def get_next_workout_in_plan(workout_id: int, request: Request):
    headers = _forward_headers(request)

    # Fetch next workout from workouts-service
    next_url = f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}/next"
    async with httpx.AsyncClient() as client:
        next_res = await client.get(next_url, headers=headers)
        logger.debug(
            "next_workout_fetch_response",
            url=next_url,
            status_code=next_res.status_code,
        )
        if next_res.status_code != 200:
            return JSONResponse(content=next_res.json(), status_code=next_res.status_code)
        next_data = next_res.json()

    # Determine the actual next workout id (may differ from the current path param)
    next_id = next_data.get("id", workout_id)

    # Always try to fetch exercise instances for the next workout
    instances_data = []
    instances_url = f"{EXERCISES_SERVICE_URL}/exercises/instances/workouts/{next_id}/instances"
    async with httpx.AsyncClient() as client:
        instances_res = await client.get(instances_url, headers=headers, follow_redirects=True)
        logger.debug(
            "next_instances_fetch_response",
            url=instances_url,
            status_code=instances_res.status_code,
        )
        instances_data = instances_res.json() if instances_res.status_code == 200 else []

    # Combine data: prefer real instances, otherwise map exercises
    if instances_data:
        next_data["exercise_instances"] = instances_data
    else:
        # Prefer mapping from workouts-service exercises when present
        exercises = next_data.get("exercises") or []
        if exercises:
            logger.debug("next_workout_mapping_exercises", workout_id=next_id)
            mapped_instances = []
            for ex in exercises:
                sets = []
                for s in ex.get("sets", []):
                    sets.append(
                        {
                            "id": None,
                            "reps": s.get("volume"),
                            "weight": s.get("working_weight")
                            if s.get("working_weight") is not None
                            else s.get("weight"),
                            "rpe": s.get("effort"),
                            "effort": s.get("effort"),
                            "effort_type": "RPE",
                            "intensity": s.get("intensity"),
                            "order": None,
                        }
                    )
                mapped_instances.append(
                    {
                        "id": None,
                        "exercise_list_id": ex.get("exercise_id"),
                        "sets": sets,
                        "notes": ex.get("notes"),
                        "order": None,
                        "workout_id": next_id,
                        "user_max_id": None,
                    }
                )
            next_data["exercise_instances"] = mapped_instances
        else:
            # Only then try plan-based fallback
            plan_instances = await _derive_exercise_instances_from_plan(
                applied_plan_id=next_data.get("applied_plan_id"),
                plan_order_index=next_data.get("plan_order_index"),
                workout_name=next_data.get("name"),
                workout_id=next_id,
                headers=headers,
            )
            if plan_instances:
                logger.debug("next_workout_plan_based_fallback", workout_id=next_id)
                next_data["exercise_instances"] = plan_instances
            else:
                next_data["exercise_instances"] = next_data.get("exercise_instances", [])
    # Do not expose raw workouts-service 'exercises' field to clients
    next_data.pop("exercises", None)
    logger.debug("next_workout_response_ready", workout_id=next_id)
    return JSONResponse(content=next_data)


@workouts_router.get("/generated/next", response_model=schemas.WorkoutResponse)
async def get_next_generated_workout(request: Request):
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/generated/next"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


@workouts_router.get("/generated/first", response_model=schemas.WorkoutResponse)
async def get_first_generated_workout(request: Request):
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/generated/first"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


@workouts_router.put("/{workout_id}", response_model=schemas.WorkoutResponseWithExercises)
async def update_workout(workout_id: int, request: Request):
    """Update workout and ensure exercise_instances are properly mapped in response"""
    headers = _forward_headers(request)
    include = _parse_include_expand(request)

    # Forward the PUT request to workouts-service
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
    body = await request.body()

    async with httpx.AsyncClient() as client:
        workout_res = await client.put(target_url, headers=headers, content=body)
        logger.debug(
            "workout_update_response",
            workout_id=workout_id,
            status_code=workout_res.status_code,
        )
        if workout_res.status_code != 200:
            return JSONResponse(content=workout_res.json(), status_code=workout_res.status_code)
        workout_data = workout_res.json()

    workout_data = await _assemble_workout_for_client(
        workout_data=workout_data,
        workout_id=workout_id,
        headers=headers,
        include=include,
    )
    logger.debug(
        "workout_update_completed",
        workout_id=workout_id,
        exercise_instances=len(workout_data.get("exercise_instances", [])),
    )
    return JSONResponse(content=workout_data)


@workouts_router.post("/{workout_id}/start", response_model=schemas.WorkoutResponseWithExercises)
async def start_workout(workout_id: int, request: Request):
    """Start a session for a workout and return aggregated workout.
    Orchestrates sessions start + (optional) workout status update, then assembles response.
    Supports include/expand for enrichments.
    """
    headers = _forward_headers(request)
    include = _parse_include_expand(request)

    # 1) Start session in workouts-service
    body = await request.body()
    session_url = f"{WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/start"
    async with httpx.AsyncClient() as client:
        session_res = await client.post(session_url, headers=headers, content=body)
        logger.debug("session_start_response", workout_id=workout_id, status_code=session_res.status_code)
        if session_res.status_code not in (200, 201):
            # Bubble up the error from downstream
            return JSONResponse(content=session_res.json(), status_code=session_res.status_code)
        session_data = session_res.json()

    # 2) Best-effort: update workout status/started_at
    try:
        put_payload = {"status": "in_progress"}
        if isinstance(session_data, dict) and session_data.get("started_at"):
            put_payload["started_at"] = session_data["started_at"]
        workout_put_url = f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
        async with httpx.AsyncClient() as client:
            put_res = await client.put(workout_put_url, headers=headers, json=put_payload)
            logger.debug(
                "workout_update_after_start",
                workout_id=workout_id,
                status_code=put_res.status_code,
            )
            # Ignore errors; final GET below will reflect actual state
    except Exception as exc:
        logger.warning("workout_update_after_start_failed", workout_id=workout_id, error=str(exc))

    # 3) Fetch workout and assemble for client
    async with httpx.AsyncClient() as client:
        workout_res = await client.get(f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}", headers=headers)
        if workout_res.status_code != 200:
            return JSONResponse(content=workout_res.json(), status_code=workout_res.status_code)
        workout_data = workout_res.json()

    workout_data = await _assemble_workout_for_client(
        workout_data=workout_data,
        workout_id=workout_id,
        headers=headers,
        include=include,
    )
    return JSONResponse(content=workout_data)


@workouts_router.get("/sessions/{workout_id}/active")
async def get_active_workout_session(workout_id: int, request: Request) -> Response:
    """Proxy: GET /api/v1/workouts/sessions/{workout_id}/active -> workouts-service.

    This matches the Flutter client call and forwards to
    {WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/active.
    """
    headers = _forward_headers(request)
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/active"
    return await _proxy_request(request, target_url, headers)


@workouts_router.post("/{workout_id}/finish", response_model=schemas.WorkoutResponseWithExercises)
async def finish_workout(workout_id: int, request: Request):
    """Finish active session for a workout and return aggregated workout.
    Orchestrates sessions finish + (optional) workout status update, then assembles response.
    Supports include/expand for enrichments.
    """
    headers = _forward_headers(request)
    include = _parse_include_expand(request)

    # 1) Find active session
    async with httpx.AsyncClient() as client:
        active_res = await client.get(f"{WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/active", headers=headers)
        logger.debug("session_active_fetch", workout_id=workout_id, status_code=active_res.status_code)
        if active_res.status_code != 200:
            # No active session; proceed to return current workout state
            workout_res = await client.get(f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}", headers=headers)
            if workout_res.status_code != 200:
                return JSONResponse(content=workout_res.json(), status_code=workout_res.status_code)
            workout_data = workout_res.json()
            workout_data = await _assemble_workout_for_client(
                workout_data=workout_data,
                workout_id=workout_id,
                headers=headers,
                include=include,
            )
            return JSONResponse(content=workout_data)

        active = active_res.json()
        session_id = active.get("id")

    # 2) Finish the session (forward body if provided)
    body = await request.body()
    async with httpx.AsyncClient() as client:
        finish_res = await client.post(
            f"{WORKOUTS_SERVICE_URL}/workouts/sessions/{session_id}/finish",
            headers=headers,
            content=body,
        )
        logger.debug("session_finish_response", workout_id=workout_id, status_code=finish_res.status_code)
        if finish_res.status_code not in (200, 201):
            return JSONResponse(content=finish_res.json(), status_code=finish_res.status_code)
        finish_data = finish_res.json()

    # 3) Best-effort: update workout status/completed_at/duration
    try:
        put_payload = {"status": "completed"}
        if isinstance(finish_data, dict):
            # Prefer new field name 'finished_at', fallback to legacy 'ended_at'
            completed_ts = finish_data.get("finished_at") or finish_data.get("ended_at")
            if completed_ts:
                put_payload["completed_at"] = completed_ts
            if finish_data.get("duration_seconds") is not None:
                put_payload["duration_seconds"] = finish_data["duration_seconds"]
        workout_put_url = f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
        async with httpx.AsyncClient() as client:
            put_res = await client.put(workout_put_url, headers=headers, json=put_payload)
            logger.debug(
                "workout_update_after_finish",
                workout_id=workout_id,
                status_code=put_res.status_code,
            )
    except Exception as exc:
        logger.warning("workout_update_after_finish_failed", workout_id=workout_id, error=str(exc))

    # 3b) Invalidate profile aggregates cache for this user to reflect fresh activity immediately
    try:
        user = getattr(request.state, "user", None)
        uid = (user or {}).get("uid") if isinstance(user, dict) else None
        _invalidate_profile_cache_for_user(uid)
    except Exception:
        pass

    # 4) Fetch workout and assemble for client
    async with httpx.AsyncClient() as client:
        workout_res = await client.get(f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}", headers=headers)
        if workout_res.status_code != 200:
            return JSONResponse(content=workout_res.json(), status_code=workout_res.status_code)
        workout_data = workout_res.json()

    workout_data = await _assemble_workout_for_client(
        workout_data=workout_data,
        workout_id=workout_id,
        headers=headers,
        include=include,
    )
    return JSONResponse(content=workout_data)


@workouts_router.api_route("{path:path}", methods=["POST", "PUT", "DELETE"])
async def proxy_workouts(request: Request, path: str = "") -> Response:
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Sessions routes
@sessions_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_sessions(request: Request, path: str = "") -> Response:
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/sessions{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Plans applied routes


@plans_applied_router.post("/apply-async/{plan_id}")
async def proxy_apply_plan_async(request: Request, plan_id: int) -> Response:
    """Proxy Celery-based plan application (enqueue task)."""

    target_url = f"{PLANS_SERVICE_URL}/plans/applied-plans/apply-async/{plan_id}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


@plans_applied_router.post("/{applied_plan_id}/apply-macros-async")
async def proxy_apply_plan_macros_async(request: Request, applied_plan_id: int) -> Response:
    """Proxy Celery-based macro application (enqueue task)."""

    target_url = f"{PLANS_SERVICE_URL}/plans/applied-plans/{applied_plan_id}/apply-macros-async"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


@plans_applied_router.get("/tasks/{task_id}")
async def proxy_plans_task_status(request: Request, task_id: str) -> Response:
    """Proxy task status polling to plans-service."""

    target_url = f"{PLANS_SERVICE_URL}/plans/applied-plans/tasks/{task_id}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


@plans_applied_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_applied(request: Request, path: str = "") -> Response:
    target_url = f"{PLANS_SERVICE_URL}/plans/applied-plans{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Plans calendar routes
@plans_calendar_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_calendar(request: Request, path: str = "") -> Response:
    suffix = "" if not path else (path if path.startswith("/") else f"/{path}")
    target_url = f"{PLANS_SERVICE_URL}/plans/calendar-plans{suffix}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


@plans_calendar_router.post("/", status_code=201)
async def create_calendar_plan(plan_data: schemas.CalendarPlanCreate, request: Request):
    target_url = f"{PLANS_SERVICE_URL}/plans/calendar-plans/"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Plans instances routes
@plans_instances_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_instances(request: Request, path: str = "") -> Response:
    target_url = f"{PLANS_SERVICE_URL}/plans/calendar-plan-instances{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Plans mesocycles routes
@plans_mesocycles_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_mesocycles(request: Request, path: str = "") -> Response:
    target_url = f"{PLANS_SERVICE_URL}/plans/mesocycles{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Plans mesocycle templates routes
@plans_templates_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_templates(request: Request, path: str = "") -> Response:
    suffix = "" if not path else (path if path.startswith("/") else f"/{path}")
    target_url = f"{PLANS_SERVICE_URL}/plans/mesocycle-templates{suffix}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)


# Include routers in the app
app.include_router(rpe_router)
app.include_router(exercises_core_router)
app.include_router(exercises_definitions_router)
app.include_router(exercises_instances_router)
app.include_router(user_max_router)
app.include_router(workouts_router)
app.include_router(sessions_router)
app.include_router(plans_applied_router)
app.include_router(plans_calendar_router)
app.include_router(plans_instances_router)
app.include_router(plans_mesocycles_router)
app.include_router(plans_templates_router)
app.include_router(analytics_router)
app.include_router(crm_router)
