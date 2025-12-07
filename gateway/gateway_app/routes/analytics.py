from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from gateway_app import main as gateway_main  # type: ignore
from gateway_app import schemas
from gateway_app.http_client import ServiceClient

analytics_router = APIRouter(prefix="/api/v1")


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
    headers = gateway_main._forward_headers(request)
    now = datetime.utcnow()

    grid_end = datetime(now.year, now.month, now.day)
    grid_end - timedelta(days=weeks * 7 - 1)

    user = getattr(request.state, "user", None)
    requester_uid = (user or {}).get("uid") if isinstance(user, dict) else None
    target_uid = user_id or requester_uid
    if target_uid is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if user_id and user_id != requester_uid:
        profile_data = await gateway_main._fetch_target_profile(user_id)
        if not profile_data.get("is_public", False):
            raise HTTPException(status_code=403, detail="Profile is private")

    cache_key = f"{target_uid}:{weeks}:{limit}"
    inm = request.headers.get("if-none-match")
    cached = gateway_main._PROFILE_CACHE.get(cache_key, now)
    if cached:
        cached_etag = cached.get("etag", "")
        if inm and cached_etag and inm == cached_etag:
            return Response(status_code=304)
        return JSONResponse(content=cached.get("content") or {}, headers={"ETag": cached_etag})

    analytics_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/analytics/profile/aggregates"
    headers_for_analytics = dict(headers)
    headers_for_analytics["X-User-Id"] = target_uid
    params = {"weeks": weeks, "limit": limit}

    async with ServiceClient(timeout=45.0) as client:
        resp = await client.get(
            analytics_url,
            headers=headers_for_analytics,
            params=params,
            user_id=target_uid,
        )
    if not resp.success:
        raise HTTPException(status_code=resp.status_code or 502, detail="Failed to fetch profile aggregates")

    content: dict[str, Any] = resp.data or {}

    etag = (resp.headers or {}).get("ETag", "")
    if not etag:
        try:
            import hashlib
            import json

            etag = hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        except Exception:
            etag = ""

    gateway_main._PROFILE_CACHE.set(cache_key, etag, content, now)

    if inm and etag and inm == etag:
        return Response(status_code=304)
    return JSONResponse(content=content, headers={"ETag": etag})


@analytics_router.get("/profile/me")
async def proxy_profile_me(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.ACCOUNTS_SERVICE_URL}/profile/me"
    return await _proxy_request_analytics(request, target_url, headers)


@analytics_router.patch("/profile/me")
async def proxy_update_profile_me(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.ACCOUNTS_SERVICE_URL}/profile/me"
    return await _proxy_request_analytics(request, target_url, headers)


@analytics_router.patch("/profile/me/coaching")
async def proxy_update_profile_coaching(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.ACCOUNTS_SERVICE_URL}/profile/me/coaching"
    return await _proxy_request_analytics(request, target_url, headers)


@analytics_router.get("/users/all")
async def proxy_users_all(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.ACCOUNTS_SERVICE_URL}/users/all"
    return await _proxy_request_analytics(request, target_url, headers)


@analytics_router.get("/profile/{user_id}")
async def proxy_profile_by_id(user_id: str, request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.ACCOUNTS_SERVICE_URL}/profile/{user_id}"
    return await _proxy_request_analytics(request, target_url, headers)


@analytics_router.get("/profile/settings")
async def proxy_profile_settings(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.ACCOUNTS_SERVICE_URL}/profile/settings"
    return await _proxy_request_analytics(request, target_url, headers)


@analytics_router.patch("/profile/settings")
async def proxy_update_profile_settings(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.ACCOUNTS_SERVICE_URL}/profile/settings"
    return await _proxy_request_analytics(request, target_url, headers)


async def _proxy_request_analytics(request: Request, target_url: str, headers: dict) -> Response:
    return await gateway_main._proxy_request(request, target_url, headers)
