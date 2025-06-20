from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app import workout_schemas, workout_models as models
from app.database import get_db
from typing import List

router = APIRouter()

@router.post("/", response_model=workout_schemas.Workout, status_code=status.HTTP_201_CREATED)
def create_workout(workout: workout_schemas.WorkoutCreate, db: Session = Depends(get_db)):
    workout_data = workout.model_dump()
    exercise_instances_data = workout_data.pop('exercise_instances', [])
    
    db_workout = models.Workout(**workout_data)
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    
    if exercise_instances_data:
        for instance_data in exercise_instances_data:
            instance_data['workout_id'] = db_workout.id
            db_instance = models.ExerciseInstance(**instance_data)
            db.add(db_instance)
        db.commit()
        db.refresh(db_workout)
    
    workout_dict = {column.name: getattr(db_workout, column.name) for column in db_workout.__table__.columns}
    workout_dict['exercise_instances'] = [
        {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
        for instance in db_workout.exercise_instances
    ]
    
    return workout_dict

@router.get("/", response_model=List[workout_schemas.Workout])
def list_workouts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    workouts = db.query(models.Workout)\
        .options(joinedload(models.Workout.exercise_instances))\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    result = []
    for workout in workouts:
        workout_dict = {column.name: getattr(workout, column.name) for column in workout.__table__.columns}
        workout_dict['exercise_instances'] = [
            {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
            for instance in workout.exercise_instances
        ]
        result.append(workout_dict)
    
    return result

@router.get("/{workout_id}", response_model=workout_schemas.Workout)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.query(models.Workout)\
        .options(joinedload(models.Workout.exercise_instances))\
        .filter(models.Workout.id == workout_id)\
        .first()
        
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
        
    workout_dict = {column.name: getattr(workout, column.name) for column in workout.__table__.columns}
    workout_dict['exercise_instances'] = [
        {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
        for instance in workout.exercise_instances
    ]
    
    return workout_dict

@router.put("/{workout_id}", response_model=workout_schemas.Workout)
def update_workout(workout_id: int, workout: workout_schemas.WorkoutCreate, db: Session = Depends(get_db)):
    db_workout = db.query(models.Workout)\
        .options(joinedload(models.Workout.exercise_instances))\
        .filter(models.Workout.id == workout_id)\
        .first()
        
    if db_workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    for key, value in workout.model_dump().items():
        setattr(db_workout, key, value)
    
    db.commit()
    db.refresh(db_workout)
    
    workout_dict = {column.name: getattr(db_workout, column.name) for column in db_workout.__table__.columns}
    workout_dict['exercise_instances'] = [
        {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
        for instance in db_workout.exercise_instances
    ]
    
    return workout_dict

@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    db_workout = db.get(models.Workout, workout_id)
    if not db_workout:
        raise HTTPException(status_code=404, detail="Workout not found")  
    db.delete(db_workout)
    db.commit()
    return None
