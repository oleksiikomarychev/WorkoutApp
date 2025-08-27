from typing import List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import ExerciseList, ExerciseInstance
from . import schemas as exercise_schemas

app = FastAPI(title="exercises-service", version="0.1.0")

# Tables are managed via Alembic migrations. Do not auto-create here.


@app.get("/api/v1/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


# Helpers copied from monolith for set id and key normalization

def _ensure_set_ids(sets: List[dict]) -> List[dict]:
    if not isinstance(sets, list):
        return []
    used_ids = set()
    max_id = 0
    sanitized: List[dict] = []
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


def _normalize_sets_for_frontend(sets: List[dict]) -> List[dict]:
    base = _ensure_set_ids(sets)
    normalized: List[dict] = []
    for item in base:
        if not isinstance(item, dict):
            continue
        s = dict(item)
        if "reps" not in s and "volume" in s and isinstance(s.get("volume"), (int, float)):
            try:
                s["reps"] = int(s["volume"]) if s["volume"] is not None else s.get("reps")
            except Exception:
                pass
        if "rpe" not in s and "effort" in s and isinstance(s.get("effort"), (int, float)):
            try:
                s["rpe"] = float(s["effort"]) if s["effort"] is not None else s.get("rpe")
            except Exception:
                pass
        normalized.append(s)
    return normalized


def _apply_inbound_mapping_to_set(item: dict) -> dict:
    s = dict(item) if isinstance(item, dict) else {}
    if "reps" in s:
        try:
            s["volume"] = int(s["reps"]) if s["reps"] is not None else s.get("volume")
        except Exception:
            pass
    if "rpe" in s:
        try:
            s["effort"] = float(s["rpe"]) if s["rpe"] is not None else s.get("effort")
        except Exception:
            pass
    return s


@app.get("/api/v1/exercises/list", response_model=List[exercise_schemas.ExerciseList])
def list_exercise_definitions(ids: str | None = None, db: Session = Depends(get_db)):
    """List exercise definitions. If `ids` query param is provided (comma-separated),
    return only those IDs. Compatible with existing Flutter client usage.
    """
    query = db.query(ExerciseList)
    if ids:
        parsed_ids: List[int] = []
        for part in ids.split(","):
            try:
                parsed_ids.append(int(part.strip()))
            except Exception:
                continue
        if parsed_ids:
            query = query.filter(ExerciseList.id.in_(parsed_ids))
        else:
            return []
    return query.all()


@app.get("/api/v1/exercises/instances/{instance_id}", response_model=exercise_schemas.ExerciseInstanceResponse)
def get_exercise_instance(instance_id: int, db: Session = Depends(get_db)):
    db_instance = db.query(ExerciseInstance).filter(ExerciseInstance.id == instance_id).first()
    if db_instance is None:
        raise HTTPException(status_code=404, detail="Exercise instance not found")
    return {
        "id": db_instance.id,
        "exercise_list_id": db_instance.exercise_list_id,
        "sets": _normalize_sets_for_frontend(db_instance.sets or []),
        "notes": getattr(db_instance, "notes", None),
        "order": getattr(db_instance, "order", None),
        "workout_id": getattr(db_instance, "workout_id", None),
        "user_max_id": getattr(db_instance, "user_max_id", None),
    }


@app.get("/api/v1/exercises/list/{exercise_list_id}", response_model=exercise_schemas.ExerciseList)
def get_exercise_definition(exercise_list_id: int, db: Session = Depends(get_db)):
    db_exercise = db.get(ExerciseList, exercise_list_id)
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    return db_exercise


@app.post("/api/v1/exercises/list", response_model=exercise_schemas.ExerciseList)
def create_exercise_definition(exercise: exercise_schemas.ExerciseListCreate, db: Session = Depends(get_db)):
    db_exercise = ExerciseList(**exercise.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise


@app.post("/api/v1/exercises/workouts/{workout_id}/instances", response_model=exercise_schemas.ExerciseInstanceResponse, status_code=status.HTTP_201_CREATED)
def create_exercise_instance(workout_id: int, instance_data: exercise_schemas.ExerciseInstanceCreate, db: Session = Depends(get_db)):
    # Create instance bound to workout_id from path
    instance_data_dict = instance_data.model_dump()
    instance_data_dict["workout_id"] = workout_id
    db_instance = ExerciseInstance(**instance_data_dict)
    # Normalize sets ids and inbound mapping
    try:
        mapped_sets = []
        for s in (db_instance.sets or []):
            mapped_sets.append(_apply_inbound_mapping_to_set(s) if isinstance(s, dict) else s)
        db_instance.sets = _ensure_set_ids(mapped_sets)
    except Exception:
        pass

    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)

    return {
        "id": db_instance.id,
        "exercise_list_id": db_instance.exercise_list_id,
        "sets": _normalize_sets_for_frontend(db_instance.sets or []),
        "notes": getattr(db_instance, "notes", None),
        "order": getattr(db_instance, "order", None),
        "workout_id": getattr(db_instance, "workout_id", None),
        "user_max_id": getattr(db_instance, "user_max_id", None),
    }


@app.put("/api/v1/exercises/instances/{instance_id}", response_model=exercise_schemas.ExerciseInstanceResponse)
def update_exercise_instance(instance_id: int, instance_update: exercise_schemas.ExerciseInstanceBase, db: Session = Depends(get_db)):
    db_instance = db.query(ExerciseInstance).filter(ExerciseInstance.id == instance_id).first()
    if db_instance is None:
        raise HTTPException(status_code=404, detail="Exercise instance not found")

    update_data = instance_update.model_dump(exclude_unset=True)
    # normalize keys sets/sets_and_reps
    if "sets_and_reps" in update_data and "sets" not in update_data:
        update_data["sets"] = [item for item in update_data["sets_and_reps"]]
    if "sets" in update_data and isinstance(update_data["sets"], list):
        update_data["sets"] = [_apply_inbound_mapping_to_set(s) if isinstance(s, dict) else s for s in update_data["sets"]]

    for key, value in update_data.items():
        setattr(db_instance, key, value)

    if isinstance(db_instance.sets, list):
        db_instance.sets = _ensure_set_ids(db_instance.sets)

    db.commit()
    db.refresh(db_instance)

    return {
        "id": db_instance.id,
        "exercise_list_id": db_instance.exercise_list_id,
        "sets": _normalize_sets_for_frontend(db_instance.sets or []),
        "notes": getattr(db_instance, "notes", None),
        "order": getattr(db_instance, "order", None),
        "workout_id": getattr(db_instance, "workout_id", None),
        "user_max_id": getattr(db_instance, "user_max_id", None),
    }


@app.put("/api/v1/exercises/instances/{instance_id}/sets/{set_id}", response_model=exercise_schemas.ExerciseInstanceResponse)
def update_exercise_set(instance_id: int, set_id: int, payload: exercise_schemas.ExerciseSetUpdate, db: Session = Depends(get_db)):
    db_instance = db.query(ExerciseInstance).filter(ExerciseInstance.id == instance_id).first()
    if db_instance is None:
        raise HTTPException(status_code=404, detail="Exercise instance not found")

    if not isinstance(db_instance.sets, list):
        raise HTTPException(status_code=404, detail="No sets to update")

    updated = False
    new_sets: List[dict] = []
    payload_dict = payload.model_dump(exclude_unset=True)

    for s in db_instance.sets:
        if isinstance(s, dict) and s.get("id") == set_id:
            merged = dict(s)
            merged.update({k: v for k, v in payload_dict.items()})
            merged = _apply_inbound_mapping_to_set(merged)
            merged["id"] = set_id
            new_sets.append(merged)
            updated = True
        else:
            new_sets.append(s)

    if not updated:
        raise HTTPException(status_code=404, detail="Set not found")

    db_instance.sets = _ensure_set_ids(new_sets)

    db.commit()
    db.refresh(db_instance)

    return {
        "id": db_instance.id,
        "exercise_list_id": db_instance.exercise_list_id,
        "sets": _normalize_sets_for_frontend(db_instance.sets or []),
        "notes": getattr(db_instance, "notes", None),
        "order": getattr(db_instance, "order", None),
        "workout_id": getattr(db_instance, "workout_id", None),
        "user_max_id": getattr(db_instance, "user_max_id", None),
    }

@app.delete("/api/v1/exercises/instances/{instance_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise_set(instance_id: int, set_id: int, db: Session = Depends(get_db)):
    db_instance = db.query(ExerciseInstance).filter(ExerciseInstance.id == instance_id).first()
    if db_instance is None:
        raise HTTPException(status_code=404, detail="Exercise instance not found")

    if not isinstance(db_instance.sets, list):
        raise HTTPException(status_code=404, detail="No sets to delete")

    original_len = len(db_instance.sets)
    new_sets = [s for s in db_instance.sets if isinstance(s, dict) and s.get("id") != set_id]
    if len(new_sets) == original_len:
        raise HTTPException(status_code=404, detail="Set not found")

    db_instance.sets = new_sets
    db.commit()
    return


@app.delete("/api/v1/exercises/instances/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise_instance(instance_id: int, db: Session = Depends(get_db)):
    db_instance = db.get(ExerciseInstance, instance_id)
    if not db_instance:
        raise HTTPException(status_code=404, detail="Exercise instance not found")

    db.delete(db_instance)
    db.commit()
    return


@app.delete("/api/v1/exercises/list/{exercise_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise_definition(exercise_list_id: int, db: Session = Depends(get_db)):
    db_exercise = db.get(ExerciseList, exercise_list_id)
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    db.delete(db_exercise)
    db.commit()
    return


@app.put("/api/v1/exercises/list/{exercise_list_id}", response_model=exercise_schemas.ExerciseList)
def update_exercise_definition(exercise_list_id: int, exercise_update: exercise_schemas.ExerciseListCreate, db: Session = Depends(get_db)):
    db_exercise = db.get(ExerciseList, exercise_list_id)
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise definition not found")

    update_data = exercise_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_exercise, key, value)

    db.commit()
    db.refresh(db_exercise)
    return db_exercise


@app.post("/api/v1/exercises/migrate-set-ids", status_code=status.HTTP_200_OK)
def migrate_set_ids(db: Session = Depends(get_db)):
    updated = 0
    instances = db.query(ExerciseInstance).all()
    for inst in instances:
        if isinstance(inst.sets, list) and any(
            not isinstance(s, dict) or "id" not in s or not isinstance(s.get("id"), int) for s in inst.sets
        ):
            inst.sets = _ensure_set_ids(inst.sets)
            updated += 1
    if updated:
        db.commit()
    return {"updated_instances": updated}
