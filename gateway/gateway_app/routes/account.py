from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request, Response, status

from gateway_app.config import ACCOUNTS_SERVICE_URL

logger = structlog.get_logger(__name__)

account_router = APIRouter(prefix="/api/v1/account")


def _mask_uid(uid: str) -> str:
    import hashlib

    digest = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:12]
    return f"uid:{digest}"


def _get_uid(request: Request) -> str:
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if isinstance(user, dict) else None
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return str(uid)


async def _revoke_firebase_refresh_tokens(uid: str) -> dict[str, Any]:
    if gateway_main.firebase_admin is None or gateway_main.auth is None:
        return {"ok": False, "error": "firebase_admin_not_available"}

    try:
        if gateway_main._FIREBASE_APP is None:
            gateway_main._initialize_firebase_app()
        gateway_main.auth.revoke_refresh_tokens(uid, app=gateway_main._FIREBASE_APP)
        return {"ok": True}
    except Exception as exc:
        try:
            logger.warning("purge_revoke_tokens_failed", user_id=_mask_uid(uid), error=str(exc))
        except Exception:
            pass
        return {"ok": False, "error": str(exc)}


async def _call_internal_purge(
    *,
    service_name: str,
    base_url: str | None,
    uid: str,
    headers_base: dict[str, str],
) -> dict[str, Any]:
    if not base_url:
        return {"ok": False, "error": "not_configured"}

    secret = getattr(gateway_main, "_INTERNAL_GATEWAY_SECRET", "") or ""
    if not secret:
        return {"ok": False, "error": "internal_secret_not_configured"}

    url = f"{base_url.rstrip('/')}/internal/users/{uid}/purge"
    headers = dict(headers_base)
    headers["X-Internal-Secret"] = secret
    headers["X-User-Id"] = uid

    timeout = httpx.Timeout(connect=5.0, read=60.0, write=60.0, pool=60.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.post(url, headers=headers)
            ok = 200 <= resp.status_code < 300
            if not ok:
                return {"ok": False, "status": resp.status_code, "body": resp.text[:500]}
            payload: Any = None
            try:
                payload = resp.json()
            except Exception:
                payload = None
            return {"ok": True, "status": resp.status_code, "data": payload}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


async def _run_purge(uid: str, headers_base: dict[str, str]) -> dict[str, Any]:
    tasks = {
        "accounts": _call_internal_purge(
            service_name="accounts",
            base_url=gateway_main.ACCOUNTS_SERVICE_URL,
            uid=uid,
            headers_base=headers_base,
        ),
        "workouts": _call_internal_purge(
            service_name="workouts",
            base_url=gateway_main.WORKOUTS_SERVICE_URL,
            uid=uid,
            headers_base=headers_base,
        ),
        "exercises": _call_internal_purge(
            service_name="exercises",
            base_url=gateway_main.EXERCISES_SERVICE_URL,
            uid=uid,
            headers_base=headers_base,
        ),
        "user_max": _call_internal_purge(
            service_name="user_max",
            base_url=gateway_main.USER_MAX_SERVICE_URL,
            uid=uid,
            headers_base=headers_base,
        ),
        "agent": _call_internal_purge(
            service_name="agent",
            base_url=gateway_main.AGENT_SERVICE_URL,
            uid=uid,
            headers_base=headers_base,
        ),
        "plans": _call_internal_purge(
            service_name="plans",
            base_url=gateway_main.PLANS_SERVICE_URL,
            uid=uid,
            headers_base=headers_base,
        ),
        "crm": _call_internal_purge(
            service_name="crm",
            base_url=gateway_main.CRM_SERVICE_URL,
            uid=uid,
            headers_base=headers_base,
        ),
    }

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    data: dict[str, Any] = {}
    ok_all = True
    for (name, _), res in zip(tasks.items(), results, strict=False):
        if isinstance(res, Exception):
            ok_all = False
            data[name] = {"ok": False, "error": str(res)}
        else:
            data[name] = res
            if not res.get("ok"):
                ok_all = False

    return {"ok": ok_all, "services": data}


@account_router.post("/purge", status_code=status.HTTP_202_ACCEPTED)
async def purge_account(request: Request) -> dict[str, Any]:
    uid = _get_uid(request)

    try:
        gateway_main._invalidate_profile_cache_for_user(uid)
    except Exception:
        pass

    revoke_result = await _revoke_firebase_refresh_tokens(uid)

    headers_base = gateway_main._forward_headers(request)

    try:
        asyncio.create_task(_run_purge(uid, headers_base))
    except Exception:
        await _run_purge(uid, headers_base)

    return {"status": "scheduled", "user_id": uid, "revoke": revoke_result}


@account_router.api_route("/users", methods=["GET"])
async def proxy_users(
    request: Request,
):
    """Proxy requests to Accounts Service users endpoint."""
    if not ACCOUNTS_SERVICE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Accounts service is not configured"
        )

    try:
        async with httpx.AsyncClient() as client:
            headers = dict(request.headers)
            headers.pop("host", None)

            response = await client.request(
                method=request.method,
                url=f"{ACCOUNTS_SERVICE_URL}/users",
                headers=headers,
                params=request.query_params,
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

    except httpx.RequestError as e:
        logger.error(f"Error proxying to accounts service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Accounts service is temporarily unavailable"
        )
