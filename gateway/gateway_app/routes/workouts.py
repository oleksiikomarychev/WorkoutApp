from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta

import common_pb2 as common_pb2
import httpx
import workouts_pb2 as workouts_pb2
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse

from gateway_app import main as gateway_main  # type: ignore
from gateway_app import schemas
from gateway_app.grpc_clients import (
    create_user_context,
    grpc_client_manager,
)
from gateway_app.http_client import ServiceClient

workouts_router = APIRouter(prefix="/api/v1/workouts")
workout_metrics_router = APIRouter(prefix="/api/v1")

_DAY_LABEL_RE = re.compile(r":\s*(Day\s*\d+)", re.IGNORECASE)


def get_current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return x_user_id


def _parse_include_expand(request: Request) -> set[str]:
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


def _extract_day_label(workout_name: str) -> str | None:
    if m := _DAY_LABEL_RE.search(workout_name or ""):
        return m.group(1)
    return None


def _sort_meso(m: dict) -> tuple[int, int]:
    return (m.get("order_index", 0), m.get("id", 0))


def _sort_micro(mc: dict) -> tuple[int, int]:
    return (mc.get("order_index", 0), mc.get("id", 0))


def _sort_workout(pw: dict) -> tuple[int, int]:
    return (pw.get("order_index", 0), pw.get("id", 0))


async def _derive_exercise_instances_from_plan(
    *,
    applied_plan_id: int | None,
    plan_order_index: int | None,
    workout_name: str | None,
    workout_id: int,
    headers: dict,
) -> list[dict]:
    if not applied_plan_id:
        return []

    plan_url = f"{gateway_main.PLANS_SERVICE_URL}/plans/applied-plans/{applied_plan_id}"
    async with ServiceClient() as client:
        plan = await client.get_json(
            plan_url,
            headers=headers,
            default=None,
            applied_plan_id=applied_plan_id,
        )
    if plan is None:
        return []

    if not isinstance(plan, dict):
        gateway_main.logger.error(
            "Unexpected applied plan payload",
            url=plan_url,
            body=plan,
            applied_plan_id=applied_plan_id,
        )
        return []

    calendar_plan = (plan or {}).get("calendar_plan") or {}
    mesocycles = calendar_plan.get("mesocycles") or []

    day_label_target: str | None = None
    if not isinstance(plan_order_index, int) and workout_name:
        day_label_target = _extract_day_label(workout_name)

    current_index = -1
    for meso in sorted(mesocycles, key=_sort_meso):
        for micro in sorted((meso.get("microcycles") or []), key=_sort_micro):
            for pw in sorted((micro.get("plan_workouts") or []), key=_sort_workout):
                current_index += 1

                if plan_order_index is None and day_label_target and pw.get("day_label") != day_label_target:
                    continue

                instances: list[dict] = []
                for ex_idx, ex in enumerate(pw.get("exercises") or []):
                    sets: list[dict] = []
                    for set_idx, s in enumerate(ex.get("sets") or []):
                        # For preview workouts, we don't have actual sets data, so use what's available
                        sets.append(
                            {
                                "id": None,
                                "reps": s.get("volume"),
                                "working_weight": s.get("working_weight"),
                                "rpe": s.get("effort"),
                                "effort": s.get("effort"),
                                "effort_type": "RPE",
                                "intensity": s.get("intensity"),
                                "order": set_idx,
                            }
                        )
                    instances.append(
                        {
                            "id": None,
                            "exercise_list_id": ex.get("exercise_definition_id"),
                            "sets": sets,
                            "notes": None,
                            "order": ex_idx,
                            "workout_id": workout_id,
                            "user_max_id": None,
                        }
                    )

                if isinstance(plan_order_index, int):
                    if current_index == plan_order_index:
                        return instances
                else:
                    if day_label_target:
                        return instances

    return []


async def _get_actual_workout_sets(workout_id: int, headers: dict) -> dict[str, list[dict]]:
    """Get actual workout sets data from workouts-service organized by exercise_id"""
    try:
        # Make request to workouts-service to get raw workout data with actual sets
        workout_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(workout_url, headers=headers)
            if response.status_code != 200:
                gateway_main.logger.error(
                    "failed_to_fetch_workout_for_sets",
                    workout_id=workout_id,
                    status_code=response.status_code,
                )
                return {}
            
            workout_data = response.json()
            exercises = workout_data.get("exercises", [])
            
            # Organize sets by exercise_list_id (exercise definition ID from exercises-service)
            # The sets are already nested under exercises, so we can use exercise_list_id as key
            sets_by_exercise = {}
            for ex in exercises:
                ex_list_id = ex.get("exercise_list_id")
                if ex_list_id:
                    sets_by_exercise[str(ex_list_id)] = ex.get("sets", [])
            
            return sets_by_exercise
            
    except Exception as e:
        gateway_main.logger.error(
            "error_getting_actual_sets",
            workout_id=workout_id,
            error=str(e),
        )
        return {}


async def _assemble_workout_for_client(
    *,
    workout_data: dict,
    workout_id: int,
    headers: dict,
    include: set[str],
) -> dict:
    # Use exercise instances from workouts-service response instead of fetching from exercises-service
    instances_data = workout_data.get("exercise_instances", [])
    gateway_main.logger.debug("instances_from_workout_response", count=len(instances_data))

    if not instances_data:
        workout_type = str(workout_data.get("workout_type") or "").lower()
        if workout_type == "generated":
            exercises = workout_data.get("exercises") or []
            if exercises:
                # Get actual workout sets data from workouts-service
                actual_sets_data = await _get_actual_workout_sets(workout_id, headers)
                gateway_main.logger.info(
                    "actual_sets_data_loaded",
                    workout_id=workout_id,
                    exercise_count=len(actual_sets_data),
                    exercise_ids=list(actual_sets_data.keys())
                )
                
                # Create exercise instances from workouts data with actual sets
                created_instances = []
                for ex_idx, ex in enumerate(exercises):
                    ex_list_id = ex.get("exercise_id")
                    if ex_list_id is None:
                        continue
                    
                    plan_sets = ex.get("sets", [])
                    actual_sets = actual_sets_data.get(str(ex_list_id), [])
                    
                    sets_payload = []
                    for set_idx, s in enumerate(plan_sets):
                        # Get actual working_weight from database
                        actual_weight = None
                        if set_idx < len(actual_sets):
                            actual_weight = actual_sets[set_idx].get("working_weight")
                            gateway_main.logger.debug(
                                "set_weight_check",
                                workout_id=workout_id,
                                exercise_list_id=ex_list_id,
                                set_idx=set_idx,
                                actual_weight=actual_weight,
                                set_data=actual_sets[set_idx] if set_idx < len(actual_sets) else None
                            )
                        
                        reps = s.get("volume")
                        if reps is None:
                            reps = s.get("reps")
                        sets_payload.append(
                            {
                                "reps": reps,
                                "working_weight": actual_weight if actual_weight is not None else None,
                                "rpe": s.get("effort"),
                                "effort": s.get("effort"),
                                "effort_type": "RPE",
                                "intensity": s.get("intensity"),
                                "order": set_idx,
                            }
                        )
                    
                    created_instances.append({
                        "id": None,  # Will be set by exercises-service when created
                        "exercise_list_id": ex_list_id,
                        "sets": sets_payload,
                        "notes": ex.get("notes"),
                        "order": ex_idx,
                        "workout_id": workout_id,
                        "user_max_id": None,
                    })
                
                if created_instances:
                    workout_data["exercise_instances"] = created_instances
            else:
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
        workout_data["exercise_instances"] = workout_data.get("exercise_instances", [])

    instances = workout_data.get("exercise_instances")
    if isinstance(instances, list) and instances:
        def _instance_sort_key(item: dict) -> tuple[int, int]:
            if not isinstance(item, dict):
                return (2**31 - 1, 2**31 - 1)
            order_val = item.get("order")
            try:
                order_key = int(order_val) if order_val is not None else (2**31 - 1)
            except (TypeError, ValueError):
                order_key = 2**31 - 1
            inst_id = item.get("id")
            try:
                id_key = int(inst_id) if inst_id is not None else (2**31 - 1)
            except (TypeError, ValueError):
                id_key = 2**31 - 1
            return (order_key, id_key)

        workout_data["exercise_instances"] = sorted(instances, key=_instance_sort_key)

    if any("exercise_instances.exercise_definition" in inc or inc == "exercise_definition" for inc in include):
        ids = [i.get("exercise_list_id") for i in workout_data.get("exercise_instances", [])]
        ids = [int(i) for i in ids if isinstance(i, int | str) and str(i).isdigit()]
        if ids:
            q = ",".join(str(i) for i in sorted(set(ids)))
            defs_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/definitions/"
            async with ServiceClient() as client:
                defs_list = await client.get_json(
                    defs_url,
                    headers=headers,
                    params={"ids": q},
                    default=[],
                )
            by_id = {int(d.get("id")): d for d in defs_list if d and d.get("id") is not None}
            for inst in workout_data.get("exercise_instances", []):
                ex_id = inst.get("exercise_list_id")
                if isinstance(ex_id, int | str) and str(ex_id).isdigit():
                    inst["exercise_definition"] = by_id.get(int(ex_id))

    workout_data.pop("exercises", None)
    return workout_data


@workouts_router.post("/import/hevy", status_code=status.HTTP_202_ACCEPTED)
async def import_hevy_csv(file: UploadFile, request: Request):
    """Enqueue async Hevy CSV import (Celery worker in workouts-service)."""
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/import/hevy"

    raw = await file.read()
    files = {
        "file": (
            file.filename or "hevy.csv",
            raw,
            file.content_type or "text/csv",
        )
    }
    # Do not forward multipart content-type to downstream JSON APIs.
    headers.pop("content-type", None)

    timeout = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=60.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.post(target_url, headers=headers, files=files)
        try:
            payload = resp.json()
        except ValueError:
            payload = {"detail": resp.text or "Upstream error"}
        return JSONResponse(content=payload, status_code=resp.status_code)


@workouts_router.get("/import/hevy/tasks/{task_id}")
async def import_hevy_task_status(task_id: str, request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/import/hevy/tasks/{task_id}"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.post("/", response_model=schemas.WorkoutResponseWithExercises, status_code=status.HTTP_201_CREATED)
async def create_workout(workout_data: schemas.WorkoutCreateWithExercises, request: Request):
    """Create workout using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.CreateWorkoutRequest(
        name=workout_data.name or "",
        workout_type=workout_data.workout_type or "",
        applied_plan_id=workout_data.applied_plan_id or 0,
        plan_order_index=workout_data.plan_order_index or 0,
        user_context=user_context,
    )

    response = await stub.CreateWorkout(request_pb, timeout=10.0)

    if not response.workout:
        return JSONResponse(status_code=500, content={"detail": "Failed to create workout"})

    workout_dict = {
        "id": response.workout.id,
        "name": response.workout.name,
        "status": response.workout.status,
        "workout_type": response.workout.workout_type,
        "started_at": response.workout.started_at if response.workout.started_at else None,
        "completed_at": response.workout.finished_at if response.workout.finished_at else None,
        "applied_plan_id": response.workout.applied_plan_id,
        "plan_order_index": response.workout.plan_order_index,
        "exercise_instances": [],
    }

    return JSONResponse(content=workout_dict, status_code=201)


@workouts_router.get("/", response_model=list[schemas.WorkoutResponse])
async def list_workouts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    applied_plan_id: int | None = None,
    type: str | None = None,
) -> Response:
    """List workouts.

    Prefer the workouts-service HTTP endpoint because it includes scheduling fields
    (e.g. scheduled_for) which are required by the calendar UI.
    """
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    headers = gateway_main._forward_headers(request)
    params: dict[str, str | int] = {"skip": skip, "limit": limit}
    if isinstance(applied_plan_id, int):
        params["applied_plan_id"] = applied_plan_id
    if type:
        params["type"] = type

    try:
        async with ServiceClient(timeout=20.0) as client:
            workouts_list = await client.get_json(
                f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/",
                headers=headers,
                params=params,
                default=[],
            )

        if not isinstance(workouts_list, list):
            workouts_list = []

        normalized: list[dict] = []
        for w in workouts_list:
            if not isinstance(w, dict):
                continue

            started_at = w.get("started_at")
            completed_at = w.get("completed_at")
            if completed_at is None:
                completed_at = w.get("finished_at")

            normalized.append(
                {
                    **w,
                    "started_at": started_at or None,
                    "completed_at": completed_at or None,
                    "exercise_instances": w.get("exercise_instances")
                    if isinstance(w.get("exercise_instances"), list)
                    else [],
                }
            )

        return JSONResponse(content=normalized)
    except Exception:
        stub = await grpc_client_manager.get_workouts_stub()
        user_context = create_user_context(str(uid))

        pagination = common_pb2.PaginationRequest(skip=skip, limit=limit)
        request_pb = workouts_pb2.ListWorkoutsRequest(
            pagination=pagination,
            user_context=user_context,
        )

        response = await stub.ListWorkouts(request_pb, timeout=10.0)

        workouts_list = []
        for workout in response.workouts:
            workouts_list.append(
                {
                    "id": workout.id,
                    "name": workout.name,
                    "status": workout.status,
                    "workout_type": workout.workout_type,
                    "started_at": workout.started_at if workout.started_at else None,
                    "completed_at": workout.finished_at if workout.finished_at else None,
                    "applied_plan_id": workout.applied_plan_id,
                    "plan_order_index": workout.plan_order_index,
                    "exercise_instances": [],
                }
            )

        return JSONResponse(content=workouts_list)


@workouts_router.get("/analytics/history")
async def proxy_workout_history_analytics(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/analytics/history"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.get("/{workout_id}/grpc")
async def get_workout_grpc(
    workout_id: int,
    user_id: str = Depends(get_current_user_id),
):
    """Get workout by ID using gRPC."""
    try:
        stub = await grpc_client_manager.get_workouts_stub()
        
        request = workouts_pb2.GetWorkoutRequest(
            workout_id=workout_id,
            user_context=create_user_context(user_id),
        )
        
        response = await stub.GetWorkout(request)
        
        if not response.workout:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        # Convert proto workout to dict format
        workout_dict = {
            "id": response.workout.id,
            "name": response.workout.name,
            "status": response.workout.status,
            "workout_type": response.workout.workout_type,
            "started_at": response.workout.started_at if response.workout.started_at else None,
            "completed_at": response.workout.finished_at if response.workout.finished_at else None,
            "applied_plan_id": response.workout.applied_plan_id,
            "plan_order_index": response.workout.plan_order_index,
            "exercise_instances": [],
        }
        
        # Convert exercise instances
        for instance in response.workout.exercise_instances:
            sets = []
            for s in instance.sets:
                sets.append({
                    "id": s.id,
                    "reps": s.reps,
                    "working_weight": s.working_weight,
                    "rpe": s.rpe,
                    "effort": s.effort,
                    "effort_type": s.effort_type,
                    "intensity": s.intensity,
                    "order": s.order,
                })
            
            workout_dict["exercise_instances"].append({
                "id": instance.id,
                "exercise_list_id": instance.exercise_list_id,
                "workout_id": instance.workout_id,
                "sets": sets,
                "notes": instance.notes,
                "order": instance.order,
                "user_max_id": instance.user_max_id,
            })
        
        return workout_dict
    except HTTPException:
        raise
    except Exception as e:
        gateway_main.logger.error(f"Workout gRPC call failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch workout via gRPC")


@workouts_router.get("/{workout_id}", response_model=schemas.WorkoutResponseWithExercises)
async def get_workout(workout_id: int, request: Request):
    """Get workout with exercise instances using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    include = _parse_include_expand(request)
    request_pb = workouts_pb2.GetWorkoutWithDetailsRequest(
        workout_id=workout_id,
        include_exercise_instances=True,
        user_context=user_context,
    )

    response = await stub.GetWorkoutWithDetails(request_pb, timeout=10.0)

    if not response.workout:
        return JSONResponse(status_code=404, content={"detail": "Workout not found"})

    workout_dict = {
        "id": response.workout.id,
        "name": response.workout.name,
        "status": response.workout.status,
        "workout_type": response.workout.workout_type,
        "started_at": response.workout.started_at if response.workout.started_at else None,
        "completed_at": response.workout.finished_at if response.workout.finished_at else None,
        "applied_plan_id": response.workout.applied_plan_id,
        "plan_order_index": response.workout.plan_order_index,
        "exercise_instances": [],
    }

    for instance in response.workout.exercise_instances:
        instance_dict = {
            "id": instance.id,
            "exercise_list_id": instance.exercise_list_id,
            "workout_id": instance.workout_id,
            "sets": [],
            "notes": instance.notes,
            "order": instance.order,
            "user_max_id": instance.user_max_id,
        }
        for s in instance.sets:
            instance_dict["sets"].append({
                "id": s.id,
                "reps": s.reps,
                "working_weight": s.working_weight,
                "rpe": s.rpe,
                "effort": s.effort,
                "effort_type": s.effort_type,
                "intensity": s.intensity,
                "order": s.order,
            })
        workout_dict["exercise_instances"].append(instance_dict)

    return JSONResponse(content=workout_dict)


@workouts_router.get("/sessions/{workout_id}/history")
async def get_workout_session_history(workout_id: int, request: Request) -> Response:
    """Get workout session history using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.GetSessionHistoryRequest(
        workout_id=workout_id,
        user_context=user_context,
    )

    response = await stub.GetSessionHistory(request_pb, timeout=10.0)

    sessions_list = []
    for session in response.sessions:
        session_dict = {
            "id": session.id,
            "workout_id": session.workout_id,
            "started_at": session.started_at,
            "finished_at": session.finished_at,
            "status": session.status,
            "exercise_instances": [],
        }
        for instance in session.exercise_instances:
            instance_dict = {
                "id": instance.id,
                "exercise_list_id": instance.exercise_list_id,
                "workout_id": instance.workout_id,
                "sets": [],
                "notes": instance.notes,
                "order": instance.order,
                "user_max_id": instance.user_max_id,
            }
            for s in instance.sets:
                instance_dict["sets"].append({
                    "id": s.id,
                    "reps": s.reps,
                    "working_weight": s.working_weight,
                    "rpe": s.rpe,
                    "effort": s.effort,
                    "effort_type": s.effort_type,
                    "intensity": s.intensity,
                    "order": s.order,
                })
            session_dict["exercise_instances"].append(instance_dict)
        sessions_list.append(session_dict)

    return JSONResponse(content=sessions_list)


@workouts_router.get("/sessions/history/all")
async def get_all_workouts_sessions_history(request: Request) -> Response:
    """Get all workout sessions history using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.ListAllSessionsRequest(
        user_context=user_context,
    )

    response = await stub.ListAllSessions(request_pb, timeout=10.0)

    sessions_list = []
    for session in response.sessions:
        # Filter out empty/None date strings
        started_at = session.started_at if session.started_at and session.started_at.strip() else None
        finished_at = session.finished_at if session.finished_at and session.finished_at.strip() else None
        
        session_dict = {
            "id": session.id,
            "workout_id": session.workout_id,
            "status": session.status,
            "exercise_instances": [],
        }
        # Only add date fields if they have valid values
        if started_at:
            session_dict["started_at"] = started_at
        if finished_at:
            session_dict["finished_at"] = finished_at
            
        for instance in session.exercise_instances:
            instance_dict = {
                "id": instance.id,
                "exercise_list_id": instance.exercise_list_id,
                "workout_id": instance.workout_id,
                "sets": [],
                "notes": instance.notes,
                "order": instance.order,
                "user_max_id": instance.user_max_id,
            }
            for s in instance.sets:
                instance_dict["sets"].append({
                    "id": s.id,
                    "reps": s.reps,
                    "working_weight": s.working_weight,
                    "rpe": s.rpe,
                    "effort": s.effort,
                    "effort_type": s.effort_type,
                    "intensity": s.intensity,
                    "order": s.order,
                })
            session_dict["exercise_instances"].append(instance_dict)
        sessions_list.append(session_dict)

    return JSONResponse(content=sessions_list)


@workouts_router.post("/schedule/shift-in-plan")
async def shift_plan_schedule(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/schedule/shift-in-plan"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.put("/{workout_id}/exercises/replace")
async def replace_workout_exercise(workout_id: int, request: Request) -> Response:
    """Replace exercise in workout using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    body = await request.json()

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.ReplaceExerciseRequest(
        workout_id=workout_id,
        old_exercise_id=body.get("old_exercise_id", 0),
        new_exercise_id=body.get("new_exercise_id", 0),
        user_context=user_context,
    )

    response = await stub.ReplaceExercise(request_pb, timeout=10.0)

    return JSONResponse(content={"updated_count": response.updated_count})


@workouts_router.post("/schedule/shift-in-plan-async")
async def shift_plan_schedule_async(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/schedule/shift-in-plan-async"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.get("/schedule/tasks/{task_id}")
async def get_task_status(task_id: str, request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/schedule/tasks/{task_id}"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.post("/applied-plans/{applied_plan_id}/mass-edit-sets")
async def mass_edit_sets(applied_plan_id: int, request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/applied-plans/{applied_plan_id}/mass-edit-sets"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.post("/applied-plans/{applied_plan_id}/mass-edit-sets-async")
async def mass_edit_sets_async(applied_plan_id: int, request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/applied-plans/{applied_plan_id}/mass-edit-sets-async"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.get("/{workout_id}/next", response_model=schemas.WorkoutResponseWithExercises)
async def get_next_workout_in_plan(workout_id: int, request: Request):
    """Get next workout using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.GetNextWorkoutRequest(
        workout_id=workout_id,
        user_context=user_context,
    )

    response = await stub.GetNextWorkout(request_pb, timeout=10.0)

    if not response.workout:
        return JSONResponse(status_code=404, content={"detail": "Next workout not found"})

    workout_dict = {
        "id": response.workout.id,
        "name": response.workout.name,
        "status": response.workout.status,
        "workout_type": response.workout.workout_type,
        "started_at": response.workout.started_at if response.workout.started_at else None,
        "completed_at": response.workout.finished_at if response.workout.finished_at else None,
        "applied_plan_id": response.workout.applied_plan_id,
        "plan_order_index": response.workout.plan_order_index,
        "exercise_instances": [],
    }

    for instance in response.workout.exercise_instances:
        instance_dict = {
            "id": instance.id,
            "exercise_list_id": instance.exercise_list_id,
            "workout_id": instance.workout_id,
            "sets": [],
            "notes": instance.notes,
            "order": instance.order,
            "user_max_id": instance.user_max_id,
        }
        for s in instance.sets:
            instance_dict["sets"].append({
                "id": s.id,
                "reps": s.reps,
                "working_weight": s.working_weight,
                "rpe": s.rpe,
                "effort": s.effort,
                "effort_type": s.effort_type,
                "intensity": s.intensity,
                "order": s.order,
            })
        workout_dict["exercise_instances"].append(instance_dict)

    return JSONResponse(content=workout_dict)


@workouts_router.get("/generated/next", response_model=schemas.WorkoutResponse)
async def get_next_generated_workout(request: Request):
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/generated/next"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.get("/generated/first", response_model=schemas.WorkoutResponse)
async def get_first_generated_workout(request: Request):
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/generated/first"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.put("/{workout_id}", response_model=schemas.WorkoutResponseWithExercises)
async def update_workout(workout_id: int, request: Request):
    """Update workout using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    body = await request.json()

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.UpdateWorkoutRequest(
        workout_id=workout_id,
        name=body.get("name", ""),
        status=body.get("status", ""),
        workout_type=body.get("workout_type", ""),
        user_context=user_context,
    )

    response = await stub.UpdateWorkout(request_pb, timeout=10.0)

    if not response.workout:
        return JSONResponse(status_code=404, content={"detail": "Workout not found"})

    workout_dict = {
        "id": response.workout.id,
        "name": response.workout.name,
        "status": response.workout.status,
        "workout_type": response.workout.workout_type,
        "started_at": response.workout.started_at if response.workout.started_at else None,
        "completed_at": response.workout.finished_at if response.workout.finished_at else None,
        "applied_plan_id": response.workout.applied_plan_id,
        "plan_order_index": response.workout.plan_order_index,
        "exercise_instances": [],
    }

    return JSONResponse(content=workout_dict)


@workouts_router.post("/{workout_id}/start", response_model=schemas.WorkoutResponseWithExercises)
async def start_workout(workout_id: int, request: Request):
    """Start workout using gRPC and create session."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.StartWorkoutRequest(
        workout_id=workout_id,
        user_context=user_context,
    )

    response = await stub.StartWorkout(request_pb, timeout=10.0)

    if not response.workout:
        return JSONResponse(status_code=404, content={"detail": "Workout not found"})

    # Create workout session via REST API
    headers = gateway_main._forward_headers(request)
    session_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/start"
    try:
        async with httpx.AsyncClient() as client:
            session_response = await client.post(session_url, headers=headers, timeout=10.0)
            if session_response.status_code != 201:
                gateway_main.logger.warning(
                    "failed_to_create_session",
                    workout_id=workout_id,
                    status_code=session_response.status_code,
                    body=session_response.text,
                )
    except Exception as e:
        gateway_main.logger.error(
            "error_creating_session",
            workout_id=workout_id,
            error=str(e),
        )

    workout_dict = {
        "id": response.workout.id,
        "name": response.workout.name,
        "status": response.workout.status,
        "workout_type": response.workout.workout_type,
        "started_at": response.workout.started_at if response.workout.started_at else None,
        "completed_at": response.workout.finished_at if response.workout.finished_at else None,
        "applied_plan_id": response.workout.applied_plan_id,
        "plan_order_index": response.workout.plan_order_index,
        "exercise_instances": [],
    }

    for instance in response.workout.exercise_instances:
        instance_dict = {
            "id": instance.id,
            "exercise_list_id": instance.exercise_list_id,
            "workout_id": instance.workout_id,
            "sets": [],
            "notes": instance.notes,
            "order": instance.order,
            "user_max_id": instance.user_max_id,
        }
        for s in instance.sets:
            instance_dict["sets"].append({
                "id": s.id,
                "reps": s.reps,
                "working_weight": s.working_weight,
                "rpe": s.rpe,
                "effort": s.effort,
                "effort_type": s.effort_type,
                "intensity": s.intensity,
                "order": s.order,
            })
        workout_dict["exercise_instances"].append(instance_dict)

    return JSONResponse(content=workout_dict)


@workouts_router.get("/sessions/{workout_id}/active")
async def get_active_workout_session(workout_id: int, request: Request) -> Response:
    """Get active workout session using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.GetActiveSessionRequest(
        workout_id=workout_id,
        user_context=user_context,
    )

    try:
        response = await stub.GetActiveSession(request_pb, timeout=10.0)
    except Exception as e:
        # Handle NOT_FOUND and other gRPC errors gracefully
        if "NOT_FOUND" in str(e):
            return JSONResponse(status_code=404, content={"detail": "Active session not found"})
        raise

    if not response.session:
        return JSONResponse(status_code=404, content={"detail": "Active session not found"})

    started_at = response.session.started_at if response.session.started_at and response.session.started_at.strip() else None
    finished_at = response.session.finished_at if response.session.finished_at and response.session.finished_at.strip() else None

    session_dict = {
        "id": response.session.id,
        "workout_id": response.session.workout_id,
        "status": response.session.status,
        "exercise_instances": [],
    }

    if started_at:
        session_dict["started_at"] = started_at
    if finished_at:
        session_dict["finished_at"] = finished_at

    for instance in response.session.exercise_instances:
        instance_dict = {
            "id": instance.id,
            "exercise_list_id": instance.exercise_list_id,
            "workout_id": instance.workout_id,
            "sets": [],
            "notes": instance.notes,
            "order": instance.order,
            "user_max_id": instance.user_max_id,
        }
        for s in instance.sets:
            set_dict = {
                "id": s.id,
                "reps": s.reps,
                "working_weight": s.working_weight,
                "rpe": s.rpe,
                "effort": s.effort,
                "effort_type": s.effort_type,
                "intensity": s.intensity,
                "order": s.order,
            }
            instance_dict["sets"].append(set_dict)
        session_dict["exercise_instances"].append(instance_dict)

    return JSONResponse(content=session_dict)


@workouts_router.post("/{workout_id}/finish", response_model=schemas.WorkoutResponseWithExercises)
async def finish_workout(workout_id: int, request: Request):
    """Finish workout using gRPC and finish active session."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.FinishWorkoutRequest(
        workout_id=workout_id,
        user_context=user_context,
    )

    response = await stub.FinishWorkout(request_pb, timeout=10.0)

    if not response.workout:
        return JSONResponse(status_code=404, content={"detail": "Workout not found"})

    # Finish active workout session via REST API
    headers = gateway_main._forward_headers(request)
    active_session_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/active"
    try:
        async with httpx.AsyncClient() as client:
            # Get active session
            active_session_response = await client.get(active_session_url, headers=headers, timeout=10.0)
            if active_session_response.status_code == 200:
                session_data = active_session_response.json()
                session_id = session_data.get("id")
                if session_id:
                    # Finish the session
                    finish_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/{session_id}/finish"
                    finish_response = await client.post(finish_url, headers=headers, timeout=10.0)
                    if finish_response.status_code != 200:
                        gateway_main.logger.warning(
                            "failed_to_finish_session",
                            workout_id=workout_id,
                            session_id=session_id,
                            status_code=finish_response.status_code,
                            body=finish_response.text,
                        )
    except Exception as e:
        gateway_main.logger.error(
            "error_finishing_session",
            workout_id=workout_id,
            error=str(e),
        )

    workout_dict = {
        "id": response.workout.id,
        "name": response.workout.name,
        "status": response.workout.status,
        "workout_type": response.workout.workout_type,
        "started_at": response.workout.started_at if response.workout.started_at else None,
        "completed_at": response.workout.finished_at if response.workout.finished_at else None,
        "applied_plan_id": response.workout.applied_plan_id,
        "plan_order_index": response.workout.plan_order_index,
        "exercise_instances": [],
    }

    for instance in response.workout.exercise_instances:
        instance_dict = {
            "id": instance.id,
            "exercise_list_id": instance.exercise_list_id,
            "workout_id": instance.workout_id,
            "sets": [],
            "notes": instance.notes,
            "order": instance.order,
            "user_max_id": instance.user_max_id,
        }
        for s in instance.sets:
            instance_dict["sets"].append({
                "id": s.id,
                "reps": s.reps,
                "working_weight": s.working_weight,
                "rpe": s.rpe,
                "effort": s.effort,
                "effort_type": s.effort_type,
                "intensity": s.intensity,
                "order": s.order,
            })
        workout_dict["exercise_instances"].append(instance_dict)

    return JSONResponse(content=workout_dict)


@workouts_router.get("/sessions/{workout_id}/active")
async def get_active_workout_session(workout_id: int, request: Request) -> Response:
    """Get active workout session using gRPC."""
    user = getattr(request.state, "user", None)
    uid = user.get("uid") if user else None
    if not uid:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    stub = await grpc_client_manager.get_workouts_stub()
    user_context = create_user_context(str(uid))

    request_pb = workouts_pb2.GetActiveSessionRequest(
        workout_id=workout_id,
        user_context=user_context,
    )

    try:
        response = await stub.GetActiveSession(request_pb, timeout=10.0)
    except Exception as e:
        # Handle NOT_FOUND and other gRPC errors gracefully
        if "NOT_FOUND" in str(e):
            return JSONResponse(status_code=404, content={"detail": "Active session not found"})
        raise

    if not response.session:
        return JSONResponse(status_code=404, content={"detail": "Active session not found"})

    session_dict = {
        "id": response.session.id,
        "workout_id": response.session.workout_id,
        "started_at": response.session.started_at,
        "finished_at": response.session.finished_at,
        "status": response.session.status,
        "exercise_instances": [],
    }

    for instance in response.session.exercise_instances:
        instance_dict = {
            "id": instance.id,
            "exercise_list_id": instance.exercise_list_id,
            "workout_id": instance.workout_id,
            "sets": [],
            "notes": instance.notes,
            "order": instance.order,
            "user_max_id": instance.user_max_id,
        }
        for s in instance.sets:
            instance_dict["sets"].append({
                "id": s.id,
                "reps": s.reps,
                "working_weight": s.working_weight,
                "rpe": s.rpe,
                "effort": s.effort,
                "effort_type": s.effort_type,
                "intensity": s.intensity,
                "order": s.order,
            })
        session_dict["exercise_instances"].append(instance_dict)

    return JSONResponse(content=session_dict)


@workouts_router.api_route("{path:path}", methods=["POST", "PUT", "DELETE"])
async def proxy_workouts(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@workout_metrics_router.get("/workout-metrics")
async def workout_metrics_endpoint(
    request: Request,
    plan_id: int | None = None,
    metric_x: str = Query(..., description="One of: volume, effort, kpsh, reps, 1rm"),
    metric_y: str = Query(..., description="One of: volume, effort, kpsh, reps, 1rm"),
    date_from: str | None = Query(None, description="ISO8601 start date"),
    date_to: str | None = Query(None, description="ISO8601 end date"),
):
    return await get_workout_metrics(
        request=request,
        plan_id=plan_id,
        metric_x=metric_x,
        metric_y=metric_y,
        date_from=date_from,
        date_to=date_to,
    )


async def get_workout_metrics(
    request: Request,
    plan_id: int | None = None,
    metric_x: str = Query(..., description="One of: volume, effort, kpsh, reps, 1rm"),
    metric_y: str = Query(..., description="One of: volume, effort, kpsh, reps, 1rm"),
    date_from: str | None = Query(None, description="ISO8601 start date"),
    date_to: str | None = Query(None, description="ISO8601 end date"),
):
    headers = gateway_main._forward_headers(request)
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

    def _parse_dt(s: str | None) -> datetime | None:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None

    end_dt = _parse_dt(date_to) or datetime.utcnow()
    start_dt = _parse_dt(date_from) or (end_dt - timedelta(days=90))

    list_params: dict[str, str | int] = {"skip": 0, "limit": 1000}
    if isinstance(plan_id, int):
        list_params["applied_plan_id"] = plan_id

    async with ServiceClient(timeout=20.0) as client:
        workouts_summary = await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/",
            headers=headers,
            params=list_params,
            default=[],
        )

    def _within(d: str | None) -> bool:
        if not d:
            return True
        try:
            dt = datetime.fromisoformat(d)
            return start_dt <= dt <= end_dt
        except ValueError:
            return True

    preselected = [w for w in workouts_summary if _within(w.get("scheduled_for"))]
    workout_ids = [w.get("id") for w in preselected if isinstance(w.get("id"), int)]

    details: dict[int, dict] = {}
    instances_by_workout: dict[int, list[dict]] = {}

    async def fetch_detail(wid: int) -> None:
        async with ServiceClient(timeout=20.0) as client:
            data = await client.get_json(
                f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{wid}",
                headers=headers,
                default=None,
                workout_id=wid,
            )
        if data is not None:
            details[wid] = data

    async def fetch_instances(wid: int) -> None:
        async with ServiceClient(timeout=20.0) as client:
            data = await client.get_json(
                f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/instances/workouts/{wid}/instances",
                headers=headers,
                default=None,
                workout_id=wid,
            )
        if isinstance(data, list):
            instances_by_workout[wid] = data

    await asyncio.gather(*[fetch_detail(wid) for wid in workout_ids])
    await asyncio.gather(*[fetch_instances(wid) for wid in workout_ids])

    exercise_ids: set[int] = set()
    for d in details.values():
        for ex in d.get("exercises") or []:
            ex_id = ex.get("exercise_id")
            if isinstance(ex_id, int):
                exercise_ids.add(ex_id)

    for inst_list in instances_by_workout.values():
        for inst in inst_list or []:
            ex_id = inst.get("exercise_list_id")
            if isinstance(ex_id, int):
                exercise_ids.add(ex_id)

    equipment_by_ex_id: dict[int, str] = {}
    if exercise_ids:
        ids_query = ",".join(str(i) for i in sorted(exercise_ids))
        async with ServiceClient(timeout=20.0) as client:
            defs = await client.get_json(
                f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/definitions",
                headers=headers,
                params={"ids": ids_query},
                default=[],
            )
        for d in defs:
            if isinstance(d, dict) and isinstance(d.get("id"), int):
                equipment_by_ex_id[int(d["id"])] = (d.get("equipment") or "").lower()

    def _pick_date(d: dict) -> datetime | None:
        for k in ("completed_at", "started_at", "scheduled_for"):
            v = d.get(k)
            if v:
                try:
                    return datetime.fromisoformat(v)
                except ValueError:
                    continue
        return None

    items: list[dict] = []
    for wid, d in details.items():
        dt = _pick_date(d)
        if dt and (dt < start_dt or dt > end_dt):
            continue

        total_reps_ws = 0
        total_eff_list: list[float] = []
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
                except (TypeError, ValueError):
                    reps = 0
                total_reps_ws += reps
                if isinstance(s.get("effort"), int | float):
                    total_eff_list.append(float(s["effort"]))
                if isinstance(w, int | float) and reps:
                    volume_kg_ws += float(w) * reps

                if is_impl or isinstance(w, int | float):
                    kpsh += reps

        volume_kg_inst = 0.0
        total_reps_inst = 0
        if wid in instances_by_workout:
            for inst in instances_by_workout.get(wid, []) or []:
                equip = equipment_by_ex_id.get(inst.get("exercise_list_id"), "")
                is_impl = _is_implement(equip)
                for s in inst.get("sets") or []:
                    reps = s.get("reps") or s.get("volume") or 0
                    weight = s.get("weight")
                    try:
                        reps = int(reps)
                    except (TypeError, ValueError):
                        reps = 0
                    total_reps_inst += reps
                    if isinstance(weight, int | float) and reps:
                        volume_kg_inst += float(weight) * reps

                    if is_impl or isinstance(weight, int | float):
                        kpsh += reps

        avg_effort = None
        if total_eff_list:
            avg_effort = sum(total_eff_list) / len(total_eff_list)
        elif isinstance(d.get("rpe_session"), int | float):
            avg_effort = float(d["rpe_session"])

        volume_final = volume_kg_ws if volume_kg_ws > 0 else volume_kg_inst

        total_reps = total_reps_ws if total_reps_ws > 0 else total_reps_inst

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

    one_rm_series: list[dict] = []
    if mx == "1rm" or my == "1rm":
        async with ServiceClient(timeout=20.0) as client:
            data = await client.get_json(
                f"{gateway_main.USER_MAX_SERVICE_URL}/user-max/",
                headers=headers,
                params={"skip": 0, "limit": 10000},
                default=[],
            )

        by_day: dict[str, float] = {}
        for um in data:
            try:
                dstr = um.get("date")
                if not dstr:
                    continue
                d_dt = datetime.fromisoformat(dstr)
                if d_dt < start_dt or d_dt > end_dt:
                    continue
                v = None
                if isinstance(um.get("verified_1rm"), int | float):
                    v = float(um["verified_1rm"])
                elif isinstance(um.get("true_1rm"), int | float):
                    v = float(um["true_1rm"])
                else:
                    mw = um.get("max_weight")
                    rp = um.get("rep_max")
                    if isinstance(mw, int | float) and isinstance(rp, int):
                        v = float(mw) * (1.0 + (rp / 30.0))
                if v is None:
                    continue
                day_key = d_dt.date().isoformat()
                current = by_day.get(day_key)
                by_day[day_key] = max(current, v) if current is not None else v
            except (TypeError, ValueError):
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


@workouts_router.post("/supplements/food")
async def create_food_gateway(request: Request):
    async with ServiceClient() as client:
        return await client.post_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/food",
            headers=request.headers,
            body=await request.json(),
        )


@workouts_router.get("/supplements/food/{food_id}")
async def get_food_gateway(food_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/food/{food_id}",
            headers=request.headers,
        )


@workouts_router.get("/supplements/food")
async def get_all_food_gateway(request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/food",
            headers=request.headers,
        )


@workouts_router.put("/supplements/food/{food_id}")
async def update_food_gateway(food_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.put_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/food/{food_id}",
            headers=request.headers,
            body=await request.json(),
        )


@workouts_router.delete("/supplements/food/{food_id}")
async def delete_food_gateway(food_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.delete(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/food/{food_id}",
            headers=request.headers,
        )


@workouts_router.post("/supplements/supplement")
async def create_supplement_gateway(request: Request):
    async with ServiceClient() as client:
        return await client.post_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/supplement",
            headers=request.headers,
            body=await request.json(),
        )


@workouts_router.get("/supplements/supplement/{supplement_id}")
async def get_supplement_gateway(supplement_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/supplement/{supplement_id}",
            headers=request.headers,
        )


@workouts_router.get("/supplements/supplement")
async def get_all_supplements_gateway(request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/supplement",
            headers=request.headers,
        )


@workouts_router.put("/supplements/supplement/{supplement_id}")
async def update_supplement_gateway(supplement_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.put_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/supplement/{supplement_id}",
            headers=request.headers,
            body=await request.json(),
        )


@workouts_router.delete("/supplements/supplement/{supplement_id}")
async def delete_supplement_gateway(supplement_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.delete(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/supplement/{supplement_id}",
            headers=request.headers,
        )


@workouts_router.post("/supplements/medication")
async def create_medication_gateway(request: Request):
    async with ServiceClient() as client:
        return await client.post_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/medication",
            headers=request.headers,
            body=await request.json(),
        )


@workouts_router.get("/supplements/medication/{medication_id}")
async def get_medication_gateway(medication_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/medication/{medication_id}",
            headers=request.headers,
        )


@workouts_router.get("/supplements/medication")
async def get_all_medications_gateway(request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/medication",
            headers=request.headers,
        )


@workouts_router.put("/supplements/medication/{medication_id}")
async def update_medication_gateway(medication_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.put_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/medication/{medication_id}",
            headers=request.headers,
            body=await request.json(),
        )


@workouts_router.delete("/supplements/medication/{medication_id}")
async def delete_medication_gateway(medication_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.delete(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/medication/{medication_id}",
            headers=request.headers,
        )


@workouts_router.post("/supplements/session")
async def create_session_gateway(request: Request):
    async with ServiceClient() as client:
        return await client.post_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/session",
            headers=request.headers,
            body=await request.json(),
        )


@workouts_router.get("/supplements/session/{session_id}")
async def get_session_gateway(session_id: str, request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/session/{session_id}",
            headers=request.headers,
        )


@workouts_router.get("/supplements/session/user/{user_id}")
async def get_sessions_by_user_id_gateway(user_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/session/user/{user_id}",
            headers=request.headers,
        )


@workouts_router.get("/supplements/session/workout/{workout_id}")
async def get_session_by_workout_id_gateway(workout_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/session/workout/{workout_id}",
            headers=request.headers,
        )


@workouts_router.get("/supplements/session/applied-plan-workout/{applied_plan_workout_id}")
async def get_session_by_applied_plan_workout_id_gateway(applied_plan_workout_id: int, request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/session/applied-plan-workout/{applied_plan_workout_id}",
            headers=request.headers,
        )


@workouts_router.get("/supplements/session")
async def get_all_sessions_gateway(request: Request):
    async with ServiceClient() as client:
        return await client.get_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/session",
            headers=request.headers,
        )


@workouts_router.put("/supplements/session/{session_id}")
async def update_session_gateway(session_id: str, request: Request):
    async with ServiceClient() as client:
        return await client.put_json(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/session/{session_id}",
            headers=request.headers,
            body=await request.json(),
        )


@workouts_router.delete("/supplements/session/{session_id}")
async def delete_session_gateway(session_id: str, request: Request):
    async with ServiceClient() as client:
        return await client.delete(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/supplements/session/{session_id}",
            headers=request.headers,
        )
