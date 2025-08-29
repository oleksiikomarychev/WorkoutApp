from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..schemas.workout import (
    WorkoutCreate,
    WorkoutResponse,
    WorkoutUpdate,
    WorkoutSummaryResponse,
)
from ..repositories.workouts_repository import WorkoutsRepository
from ..dependencies import get_db
from sqlalchemy.orm import Session
from ..models.workout import Workout
from sqlalchemy.orm import joinedload
from ..models.exercises import ExerciseInstance


router = APIRouter()


# Helper: ensure each set dict has an integer 'id'.
# IDs are unique within an instance and preserved once assigned.
def _ensure_set_ids(sets):
    if not isinstance(sets, list):
        return []
    used_ids = set()
    max_id = 0
    sanitized = []
    for item in sets:
        if not isinstance(item, dict):
            continue
        item_copy = dict(item)
        sid = item_copy.get("id")
        if isinstance(sid, int) and sid > 0 and sid not in used_ids:
            used_ids.add(sid)
            if sid > max_id:
                max_id = sid
        else:
            item_copy.pop("id", None)
        sanitized.append(item_copy)
    for item in sanitized:
        if "id" not in item:
            max_id += 1
            item["id"] = max_id
            used_ids.add(max_id)
    return sanitized


# Helper: normalize keys for frontend consumption while preserving originals.
# - Ensure 'id' is present (via _ensure_set_ids)
# - If 'reps' missing but 'volume' present -> copy volume to reps
# - If 'rpe' missing but 'effort' present -> copy effort to rpe
# - Leave original keys (volume, effort, intensity, weight) intact
def _normalize_sets_for_frontend(sets):
    base = _ensure_set_ids(sets)
    normalized = []
    for item in base:
        if not isinstance(item, dict):
            continue
        s = dict(item)
        if (
            "reps" not in s
            and "volume" in s
            and isinstance(s.get("volume"), (int, float))
        ):
            # reps is an integer in the app models
            try:
                s["reps"] = (
                    int(s["volume"]) if s["volume"] is not None else s.get("reps")
                )
            except Exception:
                pass
        if (
            "rpe" not in s
            and "effort" in s
            and isinstance(s.get("effort"), (int, float))
        ):
            try:
                s["rpe"] = (
                    float(s["effort"]) if s["effort"] is not None else s.get("rpe")
                )
            except Exception:
                pass
        normalized.append(s)
    return normalized


def get_workouts_repository(db: Session = Depends(get_db)) -> WorkoutsRepository:
    return WorkoutsRepository(db)


@router.post("/", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(
    workout: WorkoutCreate, repo: WorkoutsRepository = Depends(get_workouts_repository)
):
    return repo.create_workout(workout)


@router.get("/summary", response_model=List[WorkoutSummaryResponse])
def list_workouts_summary(
    skip: int = 0,
    limit: int = 100,
    include_completed: bool = False,
    db: Session = Depends(get_db),
):
    """Lightweight summary list for workouts screen.
    By default excludes completed workouts unless include_completed=true.
    """
    query = db.query(Workout)
    if not include_completed:
        query = query.filter(Workout.completed_at.is_(None))
    workouts = query.offset(skip).limit(limit).all()

    result: List[dict] = []
    for workout in workouts:
        safe_name = (
            workout.name
            if isinstance(workout.name, str) and len(workout.name) > 0
            else f"Workout #{workout.id}"
        )
        result.append(
            {
                "id": workout.id,
                "name": safe_name,
                "applied_plan_id": workout.applied_plan_id,
                "plan_order_index": workout.plan_order_index,
                "scheduled_for": workout.scheduled_for,
                "status": getattr(workout, "status", None),
            }
        )
    return result


@router.get("/", response_model=List[WorkoutResponse])
def list_workouts(
    skip: int = 0,
    limit: int = 100,
    summary: bool = False,
    include_completed: bool = False,
    db: Session = Depends(get_db),
):
    """
    List workouts. When `summary=true`, return a lightweight payload without
    joinedloading relationships or building nested exercise instances.
    """
    if summary:
        # Lightweight query: do not eager-load relationships
        query = db.query(Workout)
        # By default hide completed workouts on the list screen
        if not include_completed:
            query = query.filter(Workout.completed_at.is_(None))
        workouts = query.offset(skip).limit(limit).all()
    else:
        # Full detail: include exercise instances and their definitions
        workouts = (
            db.query(Workout)
            .options(
                joinedload(Workout.exercise_instances).joinedload(
                    ExerciseInstance.exercise_definition
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    result = []
    for workout in workouts:
        safe_name = (
            workout.name
            if isinstance(workout.name, str) and len(workout.name) > 0
            else f"Workout #{workout.id}"
        )
        if summary:
            # Minimal fields for list screen
            workout_data = {
                "id": workout.id,
                "name": safe_name,
                "applied_plan_id": workout.applied_plan_id,
                "plan_order_index": workout.plan_order_index,
                "scheduled_for": workout.scheduled_for,
                # keep status if needed by UI badges
                "status": getattr(workout, "status", None),
                # exercise_instances must exist per response_model compatibility
                "exercise_instances": [],
            }
        else:
            workout_data = {
                "id": workout.id,
                "name": safe_name,
                # expose applied plan linkage and scheduling fields
                "applied_plan_id": workout.applied_plan_id,
                "plan_order_index": workout.plan_order_index,
                "scheduled_for": workout.scheduled_for,
                "completed_at": workout.completed_at,
                # metadata fields
                "notes": getattr(workout, "notes", None),
                "status": getattr(workout, "status", None),
                "started_at": getattr(workout, "started_at", None),
                "duration_seconds": getattr(workout, "duration_seconds", None),
                "rpe_session": getattr(workout, "rpe_session", None),
                "location": getattr(workout, "location", None),
                "readiness_score": getattr(workout, "readiness_score", None),
                "exercise_instances": [],
            }

        if not summary:
            # Include exercise instances with their definitions and sets
            for instance in workout.exercise_instances:
                instance_data = {
                    "id": instance.id,
                    "exercise_list_id": instance.exercise_list_id,
                    "workout_id": instance.workout_id,
                    "user_max_id": instance.user_max_id,
                    # normalize sets to ensure 'id' is always present
                    "sets": _normalize_sets_for_frontend(instance.sets or []),
                    # optional metadata
                    "notes": getattr(instance, "notes", None),
                    "order": getattr(instance, "order", None),
                    "exercise_definition": None,
                }

                if instance.exercise_definition:
                    instance_data["exercise_definition"] = {
                        "id": instance.exercise_definition.id,
                        "name": instance.exercise_definition.name,
                        "muscle_group": instance.exercise_definition.muscle_group,
                        "equipment": instance.exercise_definition.equipment,
                        "target_muscles": getattr(
                            instance.exercise_definition, "target_muscles", None
                        ),
                        "synergist_muscles": getattr(
                            instance.exercise_definition, "synergist_muscles", None
                        ),
                    }

                workout_data["exercise_instances"].append(instance_data)

        result.append(workout_data)

    return result


@router.get("/{workout_id}", response_model=WorkoutResponse)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    # Get the workout with exercise instances, their definitions, and sets
    workout = (
        db.query(Workout)
        .options(
            joinedload(Workout.exercise_instances).joinedload(
                ExerciseInstance.exercise_definition
            )
        )
        .filter(Workout.id == workout_id)
        .first()
    )

    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    # Convert to dict to include relationships
    safe_name = (
        workout.name
        if isinstance(workout.name, str) and len(workout.name) > 0
        else f"Workout #{workout.id}"
    )
    result = {
        "id": workout.id,
        "name": safe_name,
        # expose applied plan linkage and scheduling fields
        "applied_plan_id": workout.applied_plan_id,
        "plan_order_index": workout.plan_order_index,
        "scheduled_for": workout.scheduled_for,
        "completed_at": workout.completed_at,
        # metadata fields
        "notes": getattr(workout, "notes", None),
        "status": getattr(workout, "status", None),
        "started_at": getattr(workout, "started_at", None),
        "duration_seconds": getattr(workout, "duration_seconds", None),
        "rpe_session": getattr(workout, "rpe_session", None),
        "location": getattr(workout, "location", None),
        "readiness_score": getattr(workout, "readiness_score", None),
        "exercise_instances": [],
    }

    # Include exercise instances with their definitions and sets
    for instance in workout.exercise_instances:
        instance_data = {
            "id": instance.id,
            "exercise_list_id": instance.exercise_list_id,
            "workout_id": instance.workout_id,
            "user_max_id": instance.user_max_id,
            # normalize sets to ensure 'id' is always present
            "sets": _normalize_sets_for_frontend(instance.sets or []),
            # optional metadata
            "notes": getattr(instance, "notes", None),
            "order": getattr(instance, "order", None),
            "exercise_definition": None,
        }

        if instance.exercise_definition:
            instance_data["exercise_definition"] = {
                "id": instance.exercise_definition.id,
                "name": instance.exercise_definition.name,
                "muscle_group": instance.exercise_definition.muscle_group,
                "equipment": instance.exercise_definition.equipment,
                "target_muscles": getattr(
                    instance.exercise_definition, "target_muscles", None
                ),
                "synergist_muscles": getattr(
                    instance.exercise_definition, "synergist_muscles", None
                ),
            }

        result["exercise_instances"].append(instance_data)

    return result


@router.put("/{workout_id}", response_model=WorkoutResponse)
def update_workout(
    workout_id: int,
    workout: WorkoutUpdate,
    repo: WorkoutsRepository = Depends(get_workouts_repository),
):
    try:
        return repo.update_workout(workout_id, workout)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int, repo: WorkoutsRepository = Depends(get_workouts_repository)
):
    repo.delete_workout(workout_id)
