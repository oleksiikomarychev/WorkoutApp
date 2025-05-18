from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.user_schemas import UserCreate, UserResponse, UserUpdate, AssignTrainerRequest, AthleteInDB, TrainerInDB
from app.services.user_service import user_service, UserService
from app import database
from app.user_models import User as UserModel, UserRole, Trainer, Athlete

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


def get_db_session():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_profile_endpoint(user_in: UserCreate, db: Session = Depends(get_db_session)):
    db_user = user_service.create_user_profile(db, user_in=user_in)
    if db_user is None:
        raise HTTPException(status_code=400, detail="Email already registered or invalid role setup")
    

    return db_user

@router.get("/{user_id}", response_model=UserResponse)
def read_user_endpoint(user_id: int, db: Session = Depends(get_db_session)):
    db_user = user_service.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db_session)):
    db_user = user_service.update_user(db, user_id=user_id, user_in=user_in)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.post("/assign-trainer", response_model=UserResponse)
def assign_trainer_to_athlete_endpoint(assignment: AssignTrainerRequest, db: Session = Depends(get_db_session)):
    updated_athlete = user_service.assign_trainer_to_athlete(db, assignment_request=assignment)
    if not updated_athlete:
        raise HTTPException(status_code=404, detail="Athlete or Trainer not found, or assignment failed.")
    return updated_athlete

@router.get("/trainer/{trainer_id}/athletes", response_model=List[UserResponse])
def get_athletes_for_trainer_endpoint(trainer_id: int, db: Session = Depends(get_db_session)):
    athletes = user_service.get_athletes_for_trainer(db, trainer_id=trainer_id)
    if not athletes:

        pass 
    return athletes


@router.get("/athletes/{athlete_id}/profile", response_model=AthleteInDB)
def get_athlete_profile_endpoint(athlete_id: int, db: Session = Depends(get_db_session)):
    user = user_service.get_user_by_id(db, user_id=athlete_id)
    if not user or user.role != UserRole.ATHLETE or not user.athlete_profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found")
    return user.athlete_profile

@router.get("/trainers/{trainer_id}/profile", response_model=TrainerInDB)
def get_trainer_profile_endpoint(trainer_id: int, db: Session = Depends(get_db_session)):

    trainer_profile = db.query(Trainer).filter(Trainer.id == trainer_id).first()
    if not trainer_profile:

        user = user_service.get_user_by_id(db, user_id=trainer_id)
        if user and user.role == UserRole.TRAINER and user.trainer_profile:
             trainer_profile = user.trainer_profile
        else:
            raise HTTPException(status_code=404, detail="Trainer profile not found by profile ID or User ID")
    return trainer_profile

