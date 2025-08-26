from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.database import Base
from app.models.workout import Workout
from app.models.exercises import ExerciseInstance
from app.schemas.workout import WorkoutResponse
from app.schemas.exercises import ExerciseInstanceCreate

# Helpers to map incoming sets and ensure stable IDs

def _ensure_set_ids(sets: List[dict]) -> List[dict]:
    if not isinstance(sets, list):
        return []
    used_ids = set()
    max_id = 0
    sanitized: List[dict] = []
    for item in sets:
        if not isinstance(item, dict):
            # skip non-dict entries
            continue
        item_copy = dict(item)
        sid = item_copy.get('id')
        if isinstance(sid, int) and sid > 0 and sid not in used_ids:
            used_ids.add(sid)
            if sid > max_id:
                max_id = sid
        else:
            # remove invalid id; will assign later
            item_copy.pop('id', None)
        sanitized.append(item_copy)
    for item in sanitized:
        if 'id' not in item:
            max_id += 1
            item['id'] = max_id
            used_ids.add(max_id)
    return sanitized


def _apply_inbound_mapping_to_set(item: dict) -> dict:
    s = dict(item) if isinstance(item, dict) else {}
    if 'reps' in s:
        try:
            s['volume'] = int(s['reps']) if s['reps'] is not None else s.get('volume')
        except Exception:
            pass
    if 'rpe' in s:
        try:
            # store as float for effort; schemas allow int range, but keep numeric
            s['effort'] = float(s['rpe']) if s['rpe'] is not None else s.get('effort')
        except Exception:
            pass
    return s


class WorkoutsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_workout(self, workout_id: int) -> Optional[Workout]:
        return self.db.query(Workout)\
            .options(
                joinedload(Workout.exercise_instances)\
                .joinedload(ExerciseInstance.exercise_definition)
            )\
            .filter(Workout.id == workout_id)\
            .first()

    def list_workouts(self, skip: int = 0, limit: int = 100) -> List[Workout]:
        return self.db.query(Workout)\
            .options(
                joinedload(Workout.exercise_instances)\
                .joinedload(ExerciseInstance.exercise_definition)
            )\
            .offset(skip)\
            .limit(limit)\
            .all()

    def update_workout(self, workout_id: int, workout: WorkoutResponse) -> Workout:
        db_workout = self.get_workout(workout_id)
        if db_workout is None:
            raise ValueError(f"Workout with id {workout_id} not found")

        # Update workout fields
        if hasattr(workout, 'name') and getattr(workout, 'name') is not None:
            db_workout.name = workout.name
        # Optional top-level metadata fields
        if hasattr(workout, 'notes') and getattr(workout, 'notes') is not None:
            db_workout.notes = workout.notes
        if hasattr(workout, 'status') and getattr(workout, 'status') is not None:
            db_workout.status = workout.status
        if hasattr(workout, 'started_at') and getattr(workout, 'started_at') is not None:
            db_workout.started_at = workout.started_at
        if hasattr(workout, 'duration_seconds') and getattr(workout, 'duration_seconds') is not None:
            db_workout.duration_seconds = workout.duration_seconds
        if hasattr(workout, 'rpe_session') and getattr(workout, 'rpe_session') is not None:
            db_workout.rpe_session = workout.rpe_session
        if hasattr(workout, 'location') and getattr(workout, 'location') is not None:
            db_workout.location = workout.location
        if hasattr(workout, 'readiness_score') and getattr(workout, 'readiness_score') is not None:
            db_workout.readiness_score = workout.readiness_score
        if hasattr(workout, 'applied_plan_id') and getattr(workout, 'applied_plan_id') is not None:
            db_workout.applied_plan_id = workout.applied_plan_id
        if hasattr(workout, 'plan_order_index') and getattr(workout, 'plan_order_index') is not None:
            db_workout.plan_order_index = workout.plan_order_index
        if hasattr(workout, 'scheduled_for') and getattr(workout, 'scheduled_for') is not None:
            db_workout.scheduled_for = workout.scheduled_for
        if hasattr(workout, 'completed_at') and getattr(workout, 'completed_at') is not None:
            db_workout.completed_at = workout.completed_at
        
        # Update exercise instances if provided
        if hasattr(workout, 'exercise_instances') and isinstance(workout.exercise_instances, list):
            # Delete existing instances
            for instance in list(db_workout.exercise_instances):
                self.db.delete(instance)

            # Create new instances with proper sets mapping and stable IDs
            for instance_data in workout.exercise_instances:
                # Support both dict-like and object-like access
                ex_list_id = getattr(instance_data, 'exercise_list_id', None) if not isinstance(instance_data, dict) else instance_data.get('exercise_list_id')
                user_max_id = getattr(instance_data, 'user_max_id', None) if not isinstance(instance_data, dict) else instance_data.get('user_max_id')
                sets_raw = getattr(instance_data, 'sets', None) if not isinstance(instance_data, dict) else instance_data.get('sets')
                notes = getattr(instance_data, 'notes', None) if not isinstance(instance_data, dict) else instance_data.get('notes')
                order = getattr(instance_data, 'order', None) if not isinstance(instance_data, dict) else instance_data.get('order')
                sets_raw = sets_raw or []

                # Normalize sets: map reps->volume, rpe->effort and ensure IDs
                normalized_sets: List[dict] = []
                for s in sets_raw:
                    if hasattr(s, 'model_dump'):
                        normalized_sets.append(_apply_inbound_mapping_to_set(s.model_dump()))
                    else:
                        normalized_sets.append(_apply_inbound_mapping_to_set(s))
                normalized_sets = _ensure_set_ids(normalized_sets)

                db_instance = ExerciseInstance(
                    workout_id=workout_id,
                    exercise_list_id=ex_list_id,
                    user_max_id=user_max_id,
                    sets=normalized_sets,
                    notes=notes,
                    order=order,
                )
                self.db.add(db_instance)

        self.db.commit()
        self.db.refresh(db_workout)
        return db_workout

    def create_workout(self, workout: WorkoutResponse) -> Workout:
        # Create workout with optional metadata if provided
        db_workout = Workout(
            name=getattr(workout, 'name', None),
            notes=getattr(workout, 'notes', None),
            status=getattr(workout, 'status', None),
            started_at=getattr(workout, 'started_at', None),
            duration_seconds=getattr(workout, 'duration_seconds', None),
            rpe_session=getattr(workout, 'rpe_session', None),
            location=getattr(workout, 'location', None),
            readiness_score=getattr(workout, 'readiness_score', None),
            applied_plan_id=getattr(workout, 'applied_plan_id', None),
            plan_order_index=getattr(workout, 'plan_order_index', None),
            scheduled_for=getattr(workout, 'scheduled_for', None),
            completed_at=getattr(workout, 'completed_at', None),
        )
        self.db.add(db_workout)
        self.db.commit()
        self.db.refresh(db_workout)
        return db_workout

    def delete_workout(self, workout_id: int) -> None:
        db_workout = self.get_workout(workout_id)
        if db_workout:
            self.db.delete(db_workout)
            self.db.commit()
