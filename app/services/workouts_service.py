from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.workout_models import Workout
from app.workout_models import ProgressionTemplate

class WorkoutsService:
    @staticmethod
    def create_workout_with_validation(db: Session, workout_data: dict) -> Workout:
        pt_id = workout_data.get('progression_template_id')
        if pt_id is not None:
            exists = db.query(ProgressionTemplate).filter_by(id=pt_id).first()
            if not exists:
                raise HTTPException(status_code=400, detail="Invalid progression_template_id")
        db_workout = Workout(**workout_data)
        db.add(db_workout)
        db.commit()
        db.refresh(db_workout)
        return db_workout
