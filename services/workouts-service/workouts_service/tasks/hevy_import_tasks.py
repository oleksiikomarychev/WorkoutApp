from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any

import httpx
from celery import shared_task
from celery.utils.log import get_task_logger

from ..celery_app import DEFAULT_QUEUE
from ..database import AsyncSessionLocal
from ..schemas import workout as workout_schemas
from ..services.rpc_client import PlansServiceRPC
from ..services.session_service import SessionService
from ..services.workout_service import WorkoutService

logger = get_task_logger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


def _parse_dt(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _map_sets_for_exercises_service(sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in sets or []:
        if not isinstance(s, dict):
            continue
        item: dict[str, Any] = {}
        if s.get("weight") is not None:
            item["weight"] = s["weight"]
        reps = s.get("reps")
        if reps is not None:
            item["reps"] = reps
            item["volume"] = reps
        if s.get("rpe") is not None:
            item["effort"] = s["rpe"]
            item["effort_type"] = "RPE"
        if s.get("set_type"):
            item["set_type"] = s["set_type"]
        if s.get("duration_seconds") is not None:
            item["duration_seconds"] = s["duration_seconds"]
        if s.get("distance_meters") is not None:
            item["distance_meters"] = s["distance_meters"]
        out.append(item)
    return out


async def _import_hevy_csv_async(
    *,
    csv_path: str,
    user_id: str,
    task=None,
) -> dict[str, Any]:
    # Import here so Celery worker doesn't require gateway code.
    from scripts.hevy_parser import parse_hevy_csv  # type: ignore

    workouts = parse_hevy_csv(csv_path)
    if not workouts:
        return {
            "created_workouts": 0,
            "total_in_file": 0,
            "errors": [{"error": "No workouts found in CSV"}],
            "workout_ids": [],
        }

    exercises_base = os.getenv("EXERCISES_SERVICE_URL")
    if not exercises_base:
        raise RuntimeError("EXERCISES_SERVICE_URL is not set")
    exercises_base = exercises_base.rstrip("/")

    created_ids: list[int] = []
    errors: list[dict[str, Any]] = []

    async with AsyncSessionLocal() as db:
        workout_service = WorkoutService(db, PlansServiceRPC(), user_id=user_id)
        session_service = SessionService(db, user_id=user_id)

        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http_client:
            total = len(workouts)
            for idx, w in enumerate(workouts):
                if task is not None:
                    try:
                        task.update_state(
                            state="PROGRESS",
                            meta={
                                "processed": idx,
                                "total": total,
                                "created_workouts": len(created_ids),
                                "errors": len(errors),
                            },
                        )
                    except Exception:
                        pass

                try:
                    workout_payload = {
                        "name": w.get("name") or "Workout",
                        "notes": w.get("notes"),
                        "status": w.get("status") or "completed",
                        "started_at": _parse_dt(w.get("started_at")),
                        "completed_at": _parse_dt(w.get("completed_at")),
                        "duration_seconds": w.get("duration_seconds"),
                        "workout_type": "manual",
                    }
                    workout_create = workout_schemas.WorkoutCreate.model_validate(workout_payload)
                    created = await workout_service.create_workout(workout_create)
                    workout_id = int(getattr(created, "id"))
                    created_ids.append(workout_id)

                    instances_url = f"{exercises_base}/exercises/instances/workouts/{workout_id}/instances"
                    headers = {"X-User-Id": user_id}

                    for ei_idx, ei in enumerate(w.get("exercise_instances") or []):
                        if not isinstance(ei, dict):
                            continue
                        instance_payload = {
                            "exercise_list_id": ei["exercise_list_id"],
                            "sets": _map_sets_for_exercises_service(ei.get("sets") or []),
                            "notes": ei.get("notes"),
                            "order": ei_idx,
                        }
                        inst_resp = await http_client.post(instances_url, json=instance_payload, headers=headers)
                        if inst_resp.status_code not in (200, 201):
                            errors.append(
                                {
                                    "index": idx,
                                    "name": workout_payload["name"],
                                    "error": f"Failed to create instance: {inst_resp.status_code} {inst_resp.text}",
                                }
                            )

                    started_at = workout_payload.get("started_at")
                    if started_at is not None and started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=UTC)

                    session = await session_service.start_workout_session(workout_id, started_at=started_at)
                    await session_service.complete_all_sets(session.id, completed=True)

                    finished_at = workout_payload.get("completed_at")
                    if finished_at is not None and finished_at.tzinfo is not None:
                        finished_at = finished_at.replace(tzinfo=None)
                    await session_service.finish_session(session.id, finished_at=finished_at)

                except Exception as exc:
                    logger.exception(
                        "hevy_import_failed",
                        user_id=user_id,
                        index=idx,
                        workout_name=w.get("name"),
                        exc_info=exc,
                    )
                    errors.append({"index": idx, "name": w.get("name"), "error": str(exc)})

            if task is not None:
                try:
                    task.update_state(
                        state="PROGRESS",
                        meta={
                            "processed": total,
                            "total": total,
                            "created_workouts": len(created_ids),
                            "errors": len(errors),
                        },
                    )
                except Exception:
                    pass

    return {
        "created_workouts": len(created_ids),
        "total_in_file": len(workouts),
        "errors": errors[:50],
        "workout_ids": created_ids,
    }


@shared_task(
    bind=True,
    name="workouts.import_hevy_csv",
    queue=DEFAULT_QUEUE,
    max_retries=0,
    time_limit=60 * 60 * 6,
)
def import_hevy_csv_task(self, *, user_id: str, csv_path: str) -> dict[str, Any]:
    try:
        logger.info("hevy_import_task_started", user_id=user_id, csv_path=csv_path)
        return _run_async(_import_hevy_csv_async(csv_path=csv_path, user_id=user_id, task=self))
    finally:
        try:
            os.unlink(csv_path)
        except Exception:
            pass
