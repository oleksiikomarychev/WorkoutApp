from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from gateway_app import main as gateway_main  # type: ignore
from gateway_app import schemas

plans_applied_router = APIRouter(prefix="/api/v1/plans/applied-plans")
plans_calendar_router = APIRouter(prefix="/api/v1/plans/calendar-plans")
plans_instances_router = APIRouter(prefix="/api/v1/plans/calendar-plan-instances")
plans_mesocycles_router = APIRouter(prefix="/api/v1/plans/mesocycles")
plans_templates_router = APIRouter(prefix="/api/v1/plans/mesocycle-templates")


@plans_applied_router.post("/apply-async/{plan_id}")
async def proxy_apply_plan_async(request: Request, plan_id: int) -> Response:
    target_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/applied-plans/apply-async/{plan_id}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


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
    suffix = "" if not path else (path if path.startswith("/") else f"/{path}")
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
