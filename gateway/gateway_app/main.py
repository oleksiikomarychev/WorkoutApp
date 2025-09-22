import asyncio
import os
from typing import Dict, List
from gateway_app import schemas
import httpx
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import status
from gateway_app import schemas

RPE_SERVICE_URL = os.getenv("RPE_SERVICE_URL")
EXERCISES_SERVICE_URL = os.getenv("EXERCISES_SERVICE_URL")
USER_MAX_SERVICE_URL = os.getenv("USER_MAX_SERVICE_URL")
WORKOUTS_SERVICE_URL = os.getenv("WORKOUTS_SERVICE_URL")
PLANS_SERVICE_URL = os.getenv("PLANS_SERVICE_URL")

app = FastAPI(
    title="WorkoutApp Gateway",
    version="1.0",
    servers=[{"url": "/api/v1", "description": "Gateway API base path"}]
)
app.router.redirect_slashes = False


def _forward_headers(request: Request) -> Dict[str, str]:
    """Collect headers to forward to downstream services, adding X-User-Id if authenticated."""
    allowed = {k: v for k, v in request.headers.items() if k.lower() in ("traceparent", "x-request-id", "content-type")}
    return allowed


# First attach CORS (outer)
_cors_origins = os.getenv("CORS_ORIGINS", "*")
_allow_origins = [o.strip() for o in _cors_origins.split(",")] if _cors_origins != "*" else ["*"]
_env_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() in ("1", "true", "yes", "on")

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

@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}

async def fetch_service_spec(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        for attempt in range(10):
            try:
                r = await client.get(f"{url}/openapi.json", timeout=5.0)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                print(f"Attempt {attempt+1} failed to fetch spec from {url}: {e}")
            await asyncio.sleep(5)
        print(f"Failed to fetch spec from {url} after 10 attempts")
        return {}

def merge_openapi_schemas(specs: list[dict], services: dict) -> dict:
    merged = {
        "openapi": "3.0.3",
        "info": {
            "title": "WorkoutApp Gateway",
            "version": "1.0",
            "description": "Aggregated API Documentation"
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
        "plans": "/api/v1"
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
    services = {
        "rpe": RPE_SERVICE_URL,
        "exercises": EXERCISES_SERVICE_URL,
        "user_max": USER_MAX_SERVICE_URL,
        "workouts": WORKOUTS_SERVICE_URL,
        "plans": PLANS_SERVICE_URL
    }
    
    # Fetch OpenAPI specs from all services
    specs = await asyncio.gather(*[
        fetch_service_spec(url) for url in services.values() if url
    ])
    
    merged_spec = merge_openapi_schemas(specs, services)
    # Log which services were fetched successfully
    for service_name, spec in zip(services.keys(), specs):
        if spec:
            print(f"Successfully fetched OpenAPI spec for {service_name}")
        else:
            print(f"Failed to fetch OpenAPI spec for {service_name}")
    app.openapi_schema = merged_spec

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

async def _proxy_request(request: Request, target_url: str, headers: dict) -> Response:
    method = request.method
    params = dict(request.query_params)
    
    async with httpx.AsyncClient() as client:
        if method in ("POST", "PUT", "PATCH"):
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

# RPE routes
@rpe_router.api_route("{path:path}", methods=["GET", "POST"])
async def proxy_rpe(request: Request, path: str = "") -> Response:
    target_url = f"{RPE_SERVICE_URL}/rpe{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)

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
                instances_url = f"{EXERCISES_SERVICE_URL}/exercises/instances/workouts/{workout_id}/instances/"  
                created_instances = []
                
                for instance in workout_data.exercise_instances:
                    instance_data = instance.model_dump_json()
                    instance_resp = await client.post(instances_url, content=instance_data, headers=headers)
                    
                    if instance_resp.status_code != 201:
                        # Compensation: delete workout if instance creation fails
                        await client.delete(f"{workout_url}{workout_id}/", headers=headers)  
                        return JSONResponse(
                            content={"detail": "Failed to create exercise instance", "error": instance_resp.json()},
                            status_code=instance_resp.status_code
                        )
                    created_instances.append(instance_resp.json())
                
                # Add instances to workout response
                workout["exercise_instances"] = created_instances
        
        return JSONResponse(content=workout, status_code=201)
    except httpx.HTTPStatusError as e:
        # Если создание инстансов провалилось, удаляем тренировку
        if "workout_id" in locals():
            await httpx.AsyncClient().delete(f"{workout_url}{workout_id}/", headers=headers)  
        return JSONResponse(
            content={"detail": str(e)},
            status_code=e.response.status_code
        )

@workouts_router.get("/", response_model=List[schemas.WorkoutResponse])
async def list_workouts(request: Request, skip: int = 0, limit: int = 100) -> Response:
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/?skip={skip}&limit={limit}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)

@workouts_router.get("/{workout_id}", response_model=schemas.WorkoutResponseWithExercises)
async def get_workout(workout_id: int, request: Request):
    headers = _forward_headers(request)
    
    # Get workout
    workout_url = f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
    print(f"[DEBUG] Fetching workout from: {workout_url}")
    async with httpx.AsyncClient() as client:
        workout_res = await client.get(workout_url, headers=headers)
        print(f"[DEBUG] Workout response status: {workout_res.status_code}")
        print(f"[DEBUG] Workout response content: {workout_res.text}")
        if workout_res.status_code != 200:
            return JSONResponse(content=workout_res.json(), status_code=workout_res.status_code)
        workout_data = workout_res.json()
    
    # Get exercise instances
    instances_url = f"{EXERCISES_SERVICE_URL}/exercises/instances/workouts/{workout_id}/instances"
    print(f"[DEBUG] Fetching instances from: {instances_url}")
    async with httpx.AsyncClient() as client:
        instances_res = await client.get(instances_url, headers=headers)
        print(f"[DEBUG] Instances response status: {instances_res.status_code}")
        print(f"[DEBUG] Instances response content: {instances_res.text}")
        instances_data = instances_res.json() if instances_res.status_code == 200 else []
    
    # Combine data
    workout_data["exercise_instances"] = instances_data
    print(f"[DEBUG] Final response data: {workout_data}")
    return JSONResponse(content=workout_data)

@workouts_router.get("/{workout_id}/next", response_model=schemas.WorkoutResponse)
async def get_next_workout_in_plan(workout_id: int, request: Request):
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts/{workout_id}/next"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)

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

@workouts_router.api_route("{path:path}", methods=["POST", "PUT", "DELETE"])
async def proxy_workouts(request: Request, path: str = "") -> Response:
    target_url = f"{WORKOUTS_SERVICE_URL}/workouts{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)

# Sessions routes
@sessions_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_sessions(request: Request, path: str = "") -> Response:
    target_url = f"{WORKOUTS_SERVICE_URL}/sessions{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)

# Plans applied routes
@plans_applied_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_applied(request: Request, path: str = "") -> Response:
    target_url = f"{PLANS_SERVICE_URL}/plans/applied-plans{path}"
    headers = _forward_headers(request)
    return await _proxy_request(request, target_url, headers)

# Plans calendar routes
@plans_calendar_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plans_calendar(request: Request, path: str = "") -> Response:
    target_url = f"{PLANS_SERVICE_URL}/plans/calendar-plans{path}"
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