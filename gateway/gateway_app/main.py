import os
from typing import Dict

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

RPE_SERVICE_URL = os.getenv("RPE_SERVICE_URL", "http://rpe-service:8001")
EXERCISES_SERVICE_URL = os.getenv("EXERCISES_SERVICE_URL", "http://exercises-service:8002")
USER_MAX_SERVICE_URL = os.getenv("USER_MAX_SERVICE_URL", "http://user-max-service:8003")
WORKOUTS_SERVICE_URL = os.getenv("WORKOUTS_SERVICE_URL", "http://workouts-service:8004")
PLANS_SERVICE_URL = os.getenv("PLANS_SERVICE_URL", "http://plans-service:8005")
# When true, proxy workouts endpoints to plans-service instead of workouts-service (useful in monolith/local where
# workouts are generated and stored by plans-service).
MONO_WORKOUTS = os.getenv("MONO_WORKOUTS", "false").lower() in ("1", "true", "yes", "on")

app = FastAPI(title="api-gateway", version="0.1.0")

# CORS for Flutter/Web clients
_cors_origins = os.getenv("CORS_ORIGINS", "*")
_allow_origins = [o.strip() for o in _cors_origins.split(",")] if _cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Avoid automatic 307 redirects for missing/extra trailing slashes
app.router.redirect_slashes = False


@app.get("/api/v1/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/api/v1/rpe")
async def proxy_get_rpe() -> Response:
    url = f"{RPE_SERVICE_URL}/api/v1/rpe"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())

@app.post("/api/v1/rpe/compute")
async def proxy_compute_rpe(request: Request) -> Response:
    body = await request.json()
    url = f"{RPE_SERVICE_URL}/api/v1/rpe/compute"
    headers = {}
    # propagate basic trace headers if present
    for h in ("traceparent", "x-request-id"):
        if h in request.headers:
            headers[h] = request.headers[h]
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(url, json=body, headers=headers)
        return JSONResponse(status_code=r.status_code, content=r.json())

@app.api_route("/api/v1/exercises{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def proxy_exercises(request: Request, path: str = "") -> Response:
    """Proxy for exercises endpoints.
    If MONO_WORKOUTS=true, forward to plans-service to keep ExerciseInstance updates
    in the same store as where workouts/instances are created. Otherwise, forward
    to dedicated exercises-service.
    """
    if MONO_WORKOUTS:
        return await proxy_plans(request, path=f"/exercises{path}")

    target_url = f"{EXERCISES_SERVICE_URL}/api/v1/exercises{path}"
    # propagate trace headers
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("traceparent", "x-request-id", "content-type")}
    method = request.method
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=5.0) as client:
        if method in ("POST", "PUT"):
            body = await request.body()
            r = await client.request(method, target_url, params=params, headers=headers, content=body, follow_redirects=True)
        else:
            r = await client.request(method, target_url, params=params, headers=headers, follow_redirects=True)
    ct = r.headers.get("content-type", "application/json")
    if r.status_code == 204:
        return Response(status_code=204)
    if "application/json" in ct.lower():
        # Best-effort JSON
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return Response(content=r.content, status_code=r.status_code, media_type=ct)

@app.api_route("/api/v1/user-maxes{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def proxy_user_maxes_alias(request: Request, path: str = "") -> Response:
    """Alias proxy to support clients hitting /api/v1/user-maxes directly."""
    # Reuse the existing proxy to ensure consistent behavior
    return await proxy_user_max(request, path=path)

 

@app.api_route("/api/v1/plans{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def proxy_plans(request: Request, path: str = "") -> Response:
    """Proxy for plans endpoints to plans-service."""
    target_url = f"{PLANS_SERVICE_URL}/api/v1{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("traceparent", "x-request-id", "content-type")}
    method = request.method
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=5.0) as client:
        if method in ("POST", "PUT"):
            body = await request.body()
            r = await client.request(method, target_url, params=params, headers=headers, content=body, follow_redirects=True)
        else:
            r = await client.request(method, target_url, params=params, headers=headers, follow_redirects=True)
    ct = r.headers.get("content-type", "application/json")
    if r.status_code == 204:
        return Response(status_code=204)
    if "application/json" in ct.lower():
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return Response(content=r.content, status_code=r.status_code, media_type=ct)
    return Response(content=r.content, status_code=r.status_code, media_type=ct)

@app.api_route("/api/v1/user-max{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def proxy_user_max(request: Request, path: str = "") -> Response:
    """Proxy for user max endpoints to user-max-service."""
    target_url = f"{USER_MAX_SERVICE_URL}/api/v1/user-maxes{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("traceparent", "x-request-id", "content-type")}
    method = request.method
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=5.0) as client:
        if method in ("POST", "PUT"):
            body = await request.body()
            r = await client.request(method, target_url, params=params, headers=headers, content=body, follow_redirects=True)
        else:
            r = await client.request(method, target_url, params=params, headers=headers, follow_redirects=True)
    ct = r.headers.get("content-type", "application/json")
    if r.status_code == 204:
        return Response(status_code=204)
    if "application/json" in ct.lower():
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return Response(content=r.content, status_code=r.status_code, media_type=ct)
    return Response(content=r.content, status_code=r.status_code, media_type=ct)

 

 

 

@app.api_route("/api/v1/sessions{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def proxy_sessions(request: Request, path: str = "") -> Response:
    """Proxy for workout session endpoints.
    If MONO_WORKOUTS=true, forward to plans-service to keep sessions in the same store
    as workouts generated by plans-service. Otherwise, forward to workouts-service.
    """
    if MONO_WORKOUTS:
        return await proxy_plans(request, path=f"/sessions{path}")

    target_url = f"{WORKOUTS_SERVICE_URL}/api/v1/sessions{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("traceparent", "x-request-id", "content-type")}
    method = request.method
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=5.0) as client:
        if method in ("POST", "PUT"):
            body = await request.body()
            r = await client.request(method, target_url, params=params, headers=headers, content=body, follow_redirects=True)
        else:
            r = await client.request(method, target_url, params=params, headers=headers, follow_redirects=True)
    ct = r.headers.get("content-type", "application/json")
    if r.status_code == 204:
        return Response(status_code=204)
    if "application/json" in ct.lower():
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return Response(content=r.content, status_code=r.status_code, media_type=ct)
    return Response(content=r.content, status_code=r.status_code, media_type=ct)


# Explicit non-redirecting base routes for clean Swagger UI
@app.api_route("/api/v1/user-max", methods=["GET", "POST"])
async def proxy_user_max_base(request: Request) -> Response:
    return await proxy_user_max(request, path="/")

@app.api_route("/api/v1/user-maxes", methods=["GET", "POST"])
async def proxy_user_maxes_base(request: Request) -> Response:
    return await proxy_user_max(request, path="/")

@app.api_route("/api/v1/user-max/by_exercise/{exercise_id}", methods=["GET"])
async def proxy_user_max_by_exercise(request: Request, exercise_id: int) -> Response:
    """Proxy for getting user maxes by exercise ID."""
    return await proxy_user_max(request, path=f"/by_exercise/{exercise_id}")


@app.api_route("/api/v1/user-max/{user_max_id}", methods=["GET", "PUT", "DELETE"])
async def proxy_user_max_detail(request: Request, user_max_id: int) -> Response:
    """Proxy for detail view (GET, PUT, DELETE) of a user max."""
    return await proxy_user_max(request, path=f"/{user_max_id}")


@app.api_route("/api/v1/workouts", methods=["GET", "POST"])
async def proxy_workouts_base(request: Request) -> Response:
    """Proxy for listing and creating workouts.

    If MONO_WORKOUTS=true, forward to plans-service instead of workouts-service.
    """
    if MONO_WORKOUTS:
        # Reuse plans proxy to ensure identical behavior and headers handling
        return await proxy_plans(request, path="/workouts")
    return await proxy_workouts(request, path="")


@app.api_route("/api/v1/exercises", methods=["GET"])
async def proxy_exercises_base(request: Request) -> Response:
    """Proxy for listing exercises."""
    return await proxy_exercises(request, path="")


@app.api_route("/api/v1/calendar-plans", methods=["GET", "POST"])
async def proxy_calendar_plans_base(request: Request) -> Response:
    """Proxy for listing and creating calendar plans."""
    return await proxy_plans(request, path="/calendar-plans")


@app.api_route("/api/v1/calendar-plans/{plan_id}", methods=["GET", "PUT", "DELETE"])
async def proxy_calendar_plan_detail(request: Request, plan_id: int) -> Response:
    """Proxy for detail view (GET, PUT, DELETE) of a calendar plan."""
    return await proxy_plans(request, path=f"/calendar-plans/{plan_id}")


@app.api_route("/api/v1/calendar-plans/favorites", methods=["GET"])
async def proxy_calendar_plan_favorites(request: Request) -> Response:
    """Proxy for listing favorite calendar plans."""
    return await proxy_plans(request, path="/calendar-plans/favorites")


@app.api_route("/api/v1/calendar-plans/{plan_id}/favorite", methods=["POST", "DELETE"])
async def proxy_calendar_plan_favorite_mutation(request: Request, plan_id: int) -> Response:
    """Proxy for adding/removing a favorite calendar plan."""
    return await proxy_plans(request, path=f"/calendar-plans/{plan_id}/favorite")


@app.api_route("/api/v1/calendar-plans/{plan_id}/workouts", methods=["GET"])
async def proxy_calendar_plan_workouts(request: Request, plan_id: int) -> Response:
    """Proxy for listing workouts generated from a calendar plan."""
    return await proxy_plans(request, path=f"/calendar-plans/{plan_id}/workouts")


@app.api_route("/api/v1/applied-calendar-plans/user", methods=["GET"])
async def proxy_applied_calendar_plans_user(request: Request) -> Response:
    """Proxy for listing user's applied calendar plans."""
    return await proxy_plans(request, path="/applied-calendar-plans/user")


@app.api_route("/api/v1/applied-calendar-plans/active", methods=["GET"])
async def proxy_applied_calendar_plans_active(request: Request) -> Response:
    """Proxy for getting the active applied calendar plan.

    If the upstream returns JSON null (no active plan), forward it as-is so clients
    that expect optional values can handle it correctly.
    """
    target_url = f"{PLANS_SERVICE_URL}/api/v1/applied-calendar-plans/active"
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("traceparent", "x-request-id", "content-type")}
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(target_url, params=params, headers=headers, follow_redirects=True)
    ct = r.headers.get("content-type", "application/json")
    if r.status_code == 204:
        return Response(status_code=204)
    if "application/json" in ct.lower():
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return Response(content=r.content, status_code=r.status_code, media_type=ct)
    return Response(content=r.content, status_code=r.status_code, media_type=ct)


@app.api_route("/api/v1/applied-calendar-plans/apply/{plan_id}", methods=["POST"])
async def proxy_applied_calendar_plans_apply(request: Request, plan_id: int) -> Response:
    """Proxy for applying a calendar plan."""
    return await proxy_plans(request, path=f"/applied-calendar-plans/apply/{plan_id}")


@app.api_route("/api/v1/calendar-plan-instances", methods=["GET", "POST"])
async def proxy_calendar_plan_instances_base(request: Request) -> Response:
    """Proxy for listing calendar plan instances."""
    return await proxy_plans(request, path="/calendar-plan-instances")


@app.api_route("/api/v1/calendar-plan-instances/{instance_id}", methods=["GET", "PUT", "DELETE"])
async def proxy_calendar_plan_instance_detail(request: Request, instance_id: int) -> Response:
    """Proxy for detail view (GET, PUT, DELETE) of a calendar plan instance."""
    return await proxy_plans(request, path=f"/calendar-plan-instances/{instance_id}")


@app.api_route("/api/v1/calendar-plan-instances/from-plan/{plan_id}", methods=["POST"])
async def proxy_calendar_plan_instance_from_plan(request: Request, plan_id: int) -> Response:
    """Proxy for creating an instance from a calendar plan."""
    return await proxy_plans(request, path=f"/calendar-plan-instances/from-plan/{plan_id}")


@app.api_route("/api/v1/calendar-plan-instances/{instance_id}/apply", methods=["POST"])
async def proxy_calendar_plan_instance_apply(request: Request, instance_id: int) -> Response:
    """Proxy for applying a calendar plan instance."""
    return await proxy_plans(request, path=f"/calendar-plan-instances/{instance_id}/apply")

@app.api_route("/api/v1/workouts{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def proxy_workouts(request: Request, path: str = "") -> Response:
    """Generic proxy for all workouts endpoints.

    If MONO_WORKOUTS=true, forward to plans-service to access workouts generated by plans-service.
    Otherwise, forward to dedicated workouts-service.
    """
    if MONO_WORKOUTS:
        return await proxy_plans(request, path=f"/workouts{path}")

    target_url = f"{WORKOUTS_SERVICE_URL}/api/v1/workouts{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("traceparent", "x-request-id", "content-type")}
    method = request.method
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=5.0) as client:
        if method in ("POST", "PUT"):
            body = await request.body()
            r = await client.request(method, target_url, params=params, headers=headers, content=body, follow_redirects=True)
        else:
            r = await client.request(method, target_url, params=params, headers=headers, follow_redirects=True)
    ct = r.headers.get("content-type", "application/json")
    if r.status_code == 204:
        return Response(status_code=204)
    if "application/json" in ct.lower():
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return Response(content=r.content, status_code=r.status_code, media_type=ct)
    return Response(content=r.content, status_code=r.status_code, media_type=ct)

@app.api_route("/api/v1/mesocycles{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def proxy_mesocycles(request: Request, path: str = "") -> Response:
    """Proxy for mesocycle endpoints to plans-service."""
    return await proxy_plans(request, path=f"/mesocycles{path}")


@app.api_route("/api/v1/microcycles{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
async def proxy_microcycles(request: Request, path: str = "") -> Response:
    """Proxy for microcycle endpoints to plans-service."""
    return await proxy_plans(request, path=f"/microcycles{path}")

@app.api_route("/api/v1/calendar-plans/{plan_id}/mesocycles", methods=["GET", "POST"])
async def proxy_calendar_plan_mesocycles(request: Request, plan_id: int) -> Response:
    """Proxy for listing/creating mesocycles under a calendar plan."""
    return await proxy_plans(request, path=f"/calendar-plans/{plan_id}/mesocycles")


@app.api_route("/api/v1/calendar-plans/{plan_id}/mesocycles/{mesocycle_id}", methods=["GET", "PUT", "DELETE"])
async def proxy_calendar_plan_mesocycle_detail(request: Request, plan_id: int, mesocycle_id: int) -> Response:
    """Proxy for detail view (GET, PUT, DELETE) of a mesocycle under a calendar plan."""
    return await proxy_plans(request, path=f"/calendar-plans/{plan_id}/mesocycles/{mesocycle_id}")
