from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import JSONResponse

from gateway_app import main as gateway_main  # type: ignore
from gateway_app import schemas
from gateway_app.http_client import ServiceClient

workouts_router = APIRouter(prefix="/api/v1/workouts")
workout_metrics_router = APIRouter(prefix="/api/v1")

_DAY_LABEL_RE = re.compile(r":\s*(Day\s*\d+)", re.IGNORECASE)


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

                instances = []
                for ex in pw.get("exercises") or []:
                    sets = []
                    for s in ex.get("sets") or []:
                        sets.append(
                            {
                                "id": None,
                                "reps": s.get("volume"),
                                "weight": s.get("working_weight"),
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

                if isinstance(plan_order_index, int):
                    if current_index == plan_order_index:
                        return instances
                else:
                    if day_label_target:
                        return instances

    return []


async def _assemble_workout_for_client(
    *,
    workout_data: dict,
    workout_id: int,
    headers: dict,
    include: set[str],
) -> dict:
    instances_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/instances/workouts/{workout_id}/instances"
    gateway_main.logger.debug("instances_fetch_start", url=instances_url)
    async with ServiceClient() as client:
        instances_data = await client.get_json(
            instances_url,
            headers=headers,
            default=[],
            workout_id=workout_id,
        )
    gateway_main.logger.debug("instances_fetch_response", count=len(instances_data) if instances_data else 0)

    if not instances_data:
        workout_type = str(workout_data.get("workout_type") or "").lower()
        if workout_type == "generated":
            exercises = workout_data.get("exercises") or []
            if exercises:
                mapped_instances: list[dict] = []
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
                            "workout_id": workout_id,
                            "user_max_id": None,
                        }
                    )
                workout_data["exercise_instances"] = mapped_instances
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
    else:
        workout_data["exercise_instances"] = instances_data

    if any("exercise_instances.exercise_definition" in inc or inc == "exercise_definition" for inc in include):
        ids = [i.get("exercise_list_id") for i in workout_data.get("exercise_instances", [])]
        ids = [int(i) for i in ids if isinstance(i, int | str) and str(i).isdigit()]
        if ids:
            q = ",".join(str(i) for i in sorted(set(ids)))
            defs_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/definitions"
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


@workouts_router.post("/", response_model=schemas.WorkoutResponseWithExercises, status_code=status.HTTP_201_CREATED)
async def create_workout(workout_data: schemas.WorkoutCreateWithExercises, request: Request):
    headers = gateway_main._forward_headers(request)

    try:
        workout_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/"
        async with httpx.AsyncClient() as client:
            workout_payload = workout_data.model_dump_json(exclude={"exercise_instances"})
            workout_resp = await client.post(workout_url, content=workout_payload, headers=headers)
            workout_resp.raise_for_status()

            workout = workout_resp.json()
            workout_id = workout["id"]

            if workout_data.exercise_instances:
                instances_url = (
                    f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/instances/workouts/{workout_id}/instances"
                )
                created_instances = []

                for instance in workout_data.exercise_instances:
                    instance_data = instance.model_dump_json()
                    instance_resp = await client.post(
                        instances_url, content=instance_data, headers=headers, follow_redirects=True
                    )

                    if instance_resp.status_code != 201:
                        await client.delete(f"{workout_url}{workout_id}", headers=headers, follow_redirects=True)
                        return JSONResponse(
                            content={
                                "detail": "Failed to create exercise instance",
                                "error": instance_resp.json(),
                            },
                            status_code=instance_resp.status_code,
                        )
                    created_instances.append(instance_resp.json())

                workout["exercise_instances"] = created_instances

        return JSONResponse(content=workout, status_code=201)
    except httpx.HTTPStatusError as e:
        if "workout_id" in locals():
            async with httpx.AsyncClient() as cleanup_client:
                await cleanup_client.delete(f"{workout_url}{workout_id}/", headers=headers)
        return JSONResponse(content={"detail": str(e)}, status_code=e.response.status_code)


@workouts_router.get("/", response_model=list[schemas.WorkoutResponse])
async def list_workouts(request: Request, skip: int = 0, limit: int = 100) -> Response:
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.get("/{workout_id}", response_model=schemas.WorkoutResponseWithExercises)
async def get_workout(workout_id: int, request: Request):
    headers = gateway_main._forward_headers(request)

    workout_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
    async with httpx.AsyncClient() as client:
        workout_res = await client.get(workout_url, headers=headers)
        gateway_main.logger.debug(
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
    gateway_main.logger.debug("workout_fetch_completed", workout_id=workout_id)
    return JSONResponse(content=workout_data)


@workouts_router.get("/sessions/{workout_id}/history")
async def get_workout_session_history(workout_id: int, request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/history"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.get("/sessions/history/all")
async def get_all_workouts_sessions_history(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/history/all"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.post("/schedule/shift-in-plan")
async def shift_plan_schedule(request: Request) -> Response:
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/schedule/shift-in-plan"
    return await gateway_main._proxy_request(request, target_url, headers)


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
    headers = gateway_main._forward_headers(request)

    next_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}/next"
    async with httpx.AsyncClient() as client:
        next_res = await client.get(next_url, headers=headers)
        gateway_main.logger.debug(
            "next_workout_fetch_response",
            url=next_url,
            status_code=next_res.status_code,
        )
        if next_res.status_code != 200:
            return JSONResponse(content=next_res.json(), status_code=next_res.status_code)
        next_data = next_res.json()

    next_id = next_data.get("id", workout_id)

    instances_data = []
    instances_url = f"{gateway_main.EXERCISES_SERVICE_URL}/exercises/instances/workouts/{next_id}/instances"
    async with httpx.AsyncClient() as client:
        instances_res = await client.get(instances_url, headers=headers, follow_redirects=True)
        gateway_main.logger.debug(
            "next_instances_fetch_response",
            url=instances_url,
            status_code=instances_res.status_code,
        )
        instances_data = instances_res.json() if instances_res.status_code == 200 else []

    if instances_data:
        next_data["exercise_instances"] = instances_data
    else:
        exercises = next_data.get("exercises") or []
        if exercises:
            gateway_main.logger.debug("next_workout_mapping_exercises", workout_id=next_id)
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
            plan_instances = await _derive_exercise_instances_from_plan(
                applied_plan_id=next_data.get("applied_plan_id"),
                plan_order_index=next_data.get("plan_order_index"),
                workout_name=next_data.get("name"),
                workout_id=next_id,
                headers=headers,
            )
            if plan_instances:
                gateway_main.logger.debug("next_workout_plan_based_fallback", workout_id=next_id)
                next_data["exercise_instances"] = plan_instances
            else:
                next_data["exercise_instances"] = next_data.get("exercise_instances", [])

    next_data.pop("exercises", None)
    gateway_main.logger.debug("next_workout_response_ready", workout_id=next_id)
    return JSONResponse(content=next_data)


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
    headers = gateway_main._forward_headers(request)
    include = _parse_include_expand(request)

    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
    body = await request.body()

    async with httpx.AsyncClient() as client:
        workout_res = await client.put(target_url, headers=headers, content=body)
        gateway_main.logger.debug(
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
    gateway_main.logger.debug(
        "workout_update_completed",
        workout_id=workout_id,
        exercise_instances=len(workout_data.get("exercise_instances", [])),
    )
    return JSONResponse(content=workout_data)


@workouts_router.post("/{workout_id}/start", response_model=schemas.WorkoutResponseWithExercises)
async def start_workout(workout_id: int, request: Request):
    headers = gateway_main._forward_headers(request)
    include = _parse_include_expand(request)

    body = await request.body()
    session_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/start"
    async with httpx.AsyncClient() as client:
        session_res = await client.post(session_url, headers=headers, content=body)
        gateway_main.logger.debug("session_start_response", workout_id=workout_id, status_code=session_res.status_code)
        if session_res.status_code not in (200, 201):
            return JSONResponse(content=session_res.json(), status_code=session_res.status_code)
        session_data = session_res.json()

    try:
        put_payload = {"status": "in_progress"}
        if isinstance(session_data, dict) and session_data.get("started_at"):
            put_payload["started_at"] = session_data["started_at"]
        workout_put_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
        async with httpx.AsyncClient() as client:
            put_res = await client.put(workout_put_url, headers=headers, json=put_payload)
            gateway_main.logger.debug(
                "workout_update_after_start",
                workout_id=workout_id,
                status_code=put_res.status_code,
            )

    except httpx.HTTPError:
        gateway_main.logger.error("Failed to update workout status after start", exc_info=True, workout_id=workout_id)

    async with httpx.AsyncClient() as client:
        workout_res = await client.get(f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}", headers=headers)
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
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/active"
    return await gateway_main._proxy_request(request, target_url, headers)


@workouts_router.post("/{workout_id}/finish", response_model=schemas.WorkoutResponseWithExercises)
async def finish_workout(workout_id: int, request: Request):
    headers = gateway_main._forward_headers(request)
    include = _parse_include_expand(request)

    async with httpx.AsyncClient() as client:
        active_res = await client.get(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/{workout_id}/active",
            headers=headers,
        )
        gateway_main.logger.debug("session_active_fetch", workout_id=workout_id, status_code=active_res.status_code)
        if active_res.status_code != 200:
            workout_res = await client.get(
                f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}",
                headers=headers,
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
            return JSONResponse(content=workout_data)

        active = active_res.json()
        session_id = active.get("id")

    body = await request.body()
    async with httpx.AsyncClient() as client:
        finish_res = await client.post(
            f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions/{session_id}/finish",
            headers=headers,
            content=body,
        )
        gateway_main.logger.debug("session_finish_response", workout_id=workout_id, status_code=finish_res.status_code)
        if finish_res.status_code not in (200, 201):
            return JSONResponse(content=finish_res.json(), status_code=finish_res.status_code)
        finish_data = finish_res.json()

    try:
        put_payload = {"status": "completed"}
        if isinstance(finish_data, dict):
            completed_ts = finish_data.get("finished_at") or finish_data.get("ended_at")
            if completed_ts:
                put_payload["completed_at"] = completed_ts
            if finish_data.get("duration_seconds") is not None:
                put_payload["duration_seconds"] = finish_data["duration_seconds"]
        workout_put_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}"
        async with httpx.AsyncClient() as client:
            put_res = await client.put(workout_put_url, headers=headers, json=put_payload)
            gateway_main.logger.debug(
                "workout_update_after_finish",
                workout_id=workout_id,
                status_code=put_res.status_code,
            )
    except httpx.HTTPError:
        gateway_main.logger.error("Failed to update workout status after finish", exc_info=True, workout_id=workout_id)

    try:
        user = getattr(request.state, "user", None)
        uid = (user or {}).get("uid") if isinstance(user, dict) else None
        gateway_main._invalidate_profile_cache_for_user(uid)
    except Exception:
        gateway_main.logger.error("Failed to invalidate profile cache for user", exc_info=True)

    async with httpx.AsyncClient() as client:
        workout_res = await client.get(f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/{workout_id}", headers=headers)
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
