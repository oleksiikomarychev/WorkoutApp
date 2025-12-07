from __future__ import annotations

from fastapi import APIRouter, Request, Response

from gateway_app import main as gateway_main  # type: ignore

exercises_core_router = APIRouter(prefix="/api/v1/exercises")
exercises_definitions_router = APIRouter(prefix="/api/v1/exercises/definitions")
exercises_instances_router = APIRouter(prefix="/api/v1/exercises/instances")


@exercises_core_router.api_route("{path:path}", methods=["GET"])
async def proxy_exercises_core(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@exercises_definitions_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_exercises_definitions(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/definitions{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@exercises_instances_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_exercises_instances(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/instances{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)
