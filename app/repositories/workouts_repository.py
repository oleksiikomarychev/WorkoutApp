from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.database import Base
from app.workout_models import Workout, ExerciseInstance
from app.workout_schemas import WorkoutResponse, ExerciseInstanceCreate

class WorkoutsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_workout(self, workout_id: int) -> Optional[Workout]:
        return self.db.query(Workout)\
            .options(joinedload(Workout.exercise_instances))\
            .filter(Workout.id == workout_id)\
            .first()

    def list_workouts(self, skip: int = 0, limit: int = 100) -> List[Workout]:
        return self.db.query(Workout)\
            .options(joinedload(Workout.exercise_instances))\
            .offset(skip)\
            .limit(limit)\
            .all()

    def update_workout(self, workout_id: int, workout: WorkoutResponse) -> Workout:
        db_workout = self.get_workout(workout_id)
        if db_workout is None:
            raise ValueError(f"Workout with id {workout_id} not found")

        # Update workout fields
        if hasattr(workout, 'name'):
            db_workout.name = workout.name

        # Update exercise instances
        if hasattr(workout, 'exercise_instances'):
            # Delete existing instances
            for instance in db_workout.exercise_instances:
                self.db.delete(instance)

            # Create new instances
            for instance_data in workout.exercise_instances:
                db_instance = ExerciseInstance(
                    workout_id=workout_id,
                    exercise_list_id=instance_data.exercise_list_id,
                    weight=instance_data.weight,
                    user_max_id=instance_data.user_max_id,
                    sets_and_reps=[item for item in getattr(instance_data, 'sets_and_reps', [])]
                )
                self.db.add(db_instance)

        self.db.commit()
        self.db.refresh(db_workout)
        return db_workout

    def create_workout(self, workout: WorkoutResponse) -> Workout:
        db_workout = Workout(name=workout.name)
        self.db.add(db_workout)
        self.db.commit()
        self.db.refresh(db_workout)
        return db_workout

    def delete_workout(self, workout_id: int) -> None:
        db_workout = self.get_workout(workout_id)
        if db_workout:
            self.db.delete(db_workout)
            self.db.commit()
