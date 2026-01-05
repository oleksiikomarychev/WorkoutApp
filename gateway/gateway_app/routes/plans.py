from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from gateway_app import main as gateway_main  # type: ignore
from gateway_app import schemas
from gateway_app.http_client import ServiceClient

plans_applied_router = APIRouter(prefix="/api/v1/plans/applied-plans")
plans_calendar_router = APIRouter(prefix="/api/v1/plans/calendar-plans")
plans_instances_router = APIRouter(prefix="/api/v1/plans/calendar-plan-instances")
plans_mesocycles_router = APIRouter(prefix="/api/v1/plans/mesocycles")
plans_templates_router = APIRouter(prefix="/api/v1/plans/mesocycle-templates")
plans_adoption_router = APIRouter(prefix="/api/v1/plans/adoption")


@plans_applied_router.get("/active/workouts/summary", response_model=list[dict[str, Any]])
async def get_active_plan_workouts_summary(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)

    active_plan_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/applied-plans/active"

    async with ServiceClient() as client:
        plan = await client.get_json(
            active_plan_url,
            headers=headers,
            default=None,
        )

    if plan is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "No active plan found"},
        )

    if not isinstance(plan, dict):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Invalid upstream response"},
        )

    applied_plan_id = plan.get("id")
    if applied_plan_id is None:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Active plan payload missing id"},
        )

    current_workout_index = plan.get("current_workout_index")
    try:
        current_workout_index_int = int(current_workout_index) if current_workout_index is not None else None
    except (TypeError, ValueError):
        current_workout_index_int = None

    proxy_timeout = float(getattr(gateway_main, "_DEFAULT_PROXY_TIMEOUT", 45.0))
    connect_timeout = float(getattr(gateway_main, "_DEFAULT_CONNECT_TIMEOUT", 10.0))
    timeout = httpx.Timeout(
        connect=connect_timeout,
        read=proxy_timeout,
        write=proxy_timeout,
        pool=connect_timeout,
    )

    workouts_list: list[dict[str, Any]] = []
    try:
        list_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/?applied_plan_id={applied_plan_id}"
        async with httpx.AsyncClient(timeout=timeout) as http:
            res = await http.get(list_url, headers=headers)
        if res.status_code == 200:
            payload = res.json()
            if isinstance(payload, list):
                workouts_list = [item for item in payload if isinstance(item, dict)]
    except (httpx.ReadTimeout, httpx.TimeoutException):
        gateway_main.logger.error(
            "active_plan_workouts_summary_timeout",
            applied_plan_id=applied_plan_id,
            exc_info=True,
        )
    except Exception:
        gateway_main.logger.error(
            "active_plan_workouts_summary_failed",
            applied_plan_id=applied_plan_id,
            exc_info=True,
        )

    merged: list[dict[str, Any]] = []
    for w in workouts_list:
        raw_id = w.get("id")
        try:
            wid = int(raw_id)
        except (TypeError, ValueError):
            continue

        order_index_raw = w.get("plan_order_index")
        try:
            order_index = int(order_index_raw) if order_index_raw is not None else None
        except (TypeError, ValueError):
            order_index = None

        merged.append(
            {
                "id": wid,
                "order_index": order_index,
                "is_current": (
                    (order_index is not None)
                    and (current_workout_index_int is not None)
                    and (order_index == current_workout_index_int)
                ),
                "name": w.get("name"),
                "scheduled_for": w.get("scheduled_for"),
                "status": w.get("status"),
                "completed_at": w.get("completed_at"),
            }
        )

    merged.sort(key=lambda x: (x.get("order_index") is None, x.get("order_index") or 0, x.get("id") or 0))
    return JSONResponse(content=merged)


@plans_applied_router.post("/apply-async/{plan_id}")
async def proxy_apply_plan_async(request: Request, plan_id: int) -> Response:
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/applied-plans/apply-async/{plan_id}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_applied_router.post("/apply/{plan_id}")
async def proxy_apply_plan(request: Request, plan_id: int) -> Response:
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/applied-plans/apply/{plan_id}"
    headers = gateway_main._forward_headers(request)

    connect_timeout = float(getattr(gateway_main, "_DEFAULT_CONNECT_TIMEOUT", 10.0))
    apply_timeout = float(getattr(gateway_main, "_PLANS_APPLY_TIMEOUT", 180.0))
    timeout = httpx.Timeout(connect=connect_timeout, read=apply_timeout, write=apply_timeout, pool=connect_timeout)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            body = await request.body()
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
                params=request.query_params,
            )
    except (httpx.ReadTimeout, httpx.TimeoutException):
        gateway_main.logger.warning(
            "plans_apply_upstream_timeout",
            plan_id=plan_id,
        )
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"detail": "Upstream timeout"},
        )
    except httpx.RequestError:
        gateway_main.logger.warning(
            "plans_apply_upstream_request_error",
            plan_id=plan_id,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "Upstream connection error"},
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


@plans_applied_router.post("/{applied_plan_id}/apply-macros-async")
async def proxy_apply_plan_macros_async(request: Request, applied_plan_id: int) -> Response:
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/applied-plans/{applied_plan_id}/apply-macros-async"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_applied_router.get("/tasks/{task_id}")
async def proxy_plans_task_status(request: Request, task_id: str) -> Response:
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/applied-plans/tasks/{task_id}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_applied_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_applied(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/applied-plans{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_calendar_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_calendar(request: Request, path: str = "") -> Response:
    if not path:
        target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/calendar-plans/"
    else:
        suffix = path if path.startswith("/") else f"/{path}"
        target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/calendar-plans{suffix}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_calendar_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_calendar_plan(plan_data: schemas.CalendarPlanCreate, request: Request):
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/calendar-plans/"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_instances_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_instances(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/calendar-plan-instances{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_mesocycles_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_mesocycles(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/mesocycles{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_templates_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_templates(request: Request, path: str = "") -> Response:
    suffix = "" if not path else (path if path.startswith("/") else f"/{path}")
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/mesocycle-templates{suffix}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@plans_adoption_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_adoption(request: Request, path: str = "") -> Response:
    suffix = "" if not path else (path if path.startswith("/") else f"/{path}")
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/adoption{suffix}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)
