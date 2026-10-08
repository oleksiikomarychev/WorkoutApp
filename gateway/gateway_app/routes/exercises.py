from __future__ import annotations

import logging

import exercises_pb2 as exercises_pb2
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response

from gateway_app import main as gateway_main  # type: ignore
from gateway_app.grpc_clients import (
    create_user_context,
    grpc_client_manager,
)

logger = logging.getLogger(__name__)

exercises_core_router = APIRouter(prefix="/api/v1/exercises")
exercises_definitions_router = APIRouter(prefix="/api/v1/exercises/definitions")
exercises_instances_router = APIRouter(prefix="/api/v1/exercises/instances")


def get_current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return x_user_id


@exercises_definitions_router.get("/")
async def get_exercise_definitions(
    ids: str | None = Query(None),
    user_id: str = Depends(get_current_user_id),
):
    """Get exercise definitions by IDs using gRPC."""
    if ids:
        # Parse IDs from comma-separated string
        id_list = [int(id_str.strip()) for id_str in ids.split(",") if id_str.strip().isdigit()]
        
        stub = await grpc_client_manager.get_exercises_stub()
        
        request = exercises_pb2.GetExerciseDefinitionsRequest(
            ids=id_list,
            user_context=create_user_context(user_id),
        )
        
        response = await stub.GetExerciseDefinitions(request)
        
        # Convert proto responses to dict format compatible with existing API
        definitions = []
        for d in response.definitions:
            definitions.append({
                "id": d.id,
                "name": d.name,
                "muscle_group": d.muscle_group,
                "equipment": d.equipment,
                "description": d.description,
                "image_url": d.media_image,
                "gif_url": d.media_gif,
            })
        
        return definitions
    else:
        # Fall back to HTTP proxy for non-ID-based queries
        target_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/definitions/"
        headers = gateway_main._forward_headers(Request)
        return await gateway_main._proxy_request(Request, target_url, headers)


@exercises_definitions_router.get("/{exercise_id}")
async def get_exercise_definition(
    exercise_id: int,
    user_id: str = Depends(get_current_user_id),
):
    """Get a single exercise definition by ID using gRPC."""
    stub = await grpc_client_manager.get_exercises_stub()
    
    request = exercises_pb2.GetExerciseRequest(
        exercise_id=exercise_id,
        user_context=create_user_context(user_id),
    )
    
    response = await stub.GetExercise(request)
    
    if not response.exercise:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    
    return {
        "id": response.exercise.id,
        "name": response.exercise.name,
        "muscle_group": response.exercise.muscle_group,
        "equipment": response.exercise.equipment,
        "description": response.exercise.description,
        "image_url": response.exercise.media_image,
        "gif_url": response.exercise.media_gif,
    }


@exercises_core_router.api_route("{path:path}", methods=["GET"])
async def proxy_exercises_core(request: Request, path: str = "") -> Response:
    """Fallback HTTP proxy for exercises core endpoints."""
    target_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@exercises_definitions_router.api_route("{path:path}", methods=["POST", "PUT", "DELETE"])
async def proxy_exercises_definitions_mutations(request: Request, path: str = "") -> Response:
    """Fallback HTTP proxy for exercise definition mutations."""
    target_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/definitions{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@exercises_instances_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_exercises_instances(request: Request, path: str = "") -> Response:
    """Fallback HTTP proxy for exercise instances."""
    target_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/instances{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)
