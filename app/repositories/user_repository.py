from sqlalchemy.orm import Session, joinedload
from .base_repository import BaseRepository
from app.user_models import User, Athlete, Trainer, UserRole
from app.user_schemas import UserCreate, UserUpdate, AthleteCreate, TrainerCreate
from typing import Optional, List

class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def create_user_with_profile(
        self, db: Session, *, user_in: UserCreate
    ) -> User:
        db_user = User(
            email=user_in.email,
            hashed_password=user_in.password,
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            role=user_in.role
        )

        if user_in.role == UserRole.ATHLETE:

            db_athlete = Athlete()
            db_user.athlete_profile = db_athlete
        elif user_in.role == UserRole.TRAINER:

            db_trainer = Trainer()
            db_user.trainer_profile = db_trainer
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        if db_user.athlete_profile:
            db.refresh(db_user.athlete_profile)
        if db_user.trainer_profile:
            db.refresh(db_user.trainer_profile)
        return db_user

    def get_with_profile(self, db: Session, user_id: int) -> Optional[User]:
        return (
            db.query(User)
            .options(joinedload(User.athlete_profile), joinedload(User.trainer_profile))
            .filter(User.id == user_id)
            .first()
        )
    
    def assign_trainer_to_athlete_repo(self, db: Session, athlete_id: int, trainer_id: int) -> Optional[User]:
        athlete_user = db.query(User).filter(User.id == athlete_id, User.role == UserRole.ATHLETE).first()
        trainer = db.query(Trainer).filter(Trainer.id == trainer_id).first()

        if athlete_user and trainer:
            athlete_user.assigned_trainer_id = trainer.id
            db.commit()
            db.refresh(athlete_user)
            return athlete_user
        return None

    def get_athletes_by_trainer(self, db: Session, trainer_id: int) -> List[User]:

        trainer_profile = db.query(Trainer).filter(Trainer.id == trainer_id).first()
        if not trainer_profile:
            return []
        

        return db.query(User).filter(User.role == UserRole.ATHLETE, User.assigned_trainer_id == trainer_id).all()


user_repository = UserRepository(User)
