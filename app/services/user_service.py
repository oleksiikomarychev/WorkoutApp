from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional, List

from app.repositories.user_repository import user_repository, UserRepository
from app.user_models import User, UserRole, Athlete, Trainer
from app.user_schemas import UserCreate, UserUpdate, AthleteCreate, TrainerCreate, UserResponse, AssignTrainerRequest

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_user_profile(self, db: Session, user_in: UserCreate) -> Optional[User]:

        existing_user = self.repository.get_by_email(db, email=user_in.email)
        if existing_user:

            return None 

        hashed_password = self.get_password_hash(user_in.password.get_secret_value())
        

        user_data_for_repo = user_in.model_copy(update={"password": hashed_password})


        return self.repository.create_user_with_profile(db, user_in=user_data_for_repo)

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:

        return self.repository.get_with_profile(db, user_id=user_id)

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return self.repository.get_by_email(db, email=email)

    def update_user(self, db: Session, user_id: int, user_in: UserUpdate) -> Optional[User]:
        db_user = self.repository.get(db, id=user_id)
        if not db_user:
            return None

        return self.repository.update(db, db_obj=db_user, obj_in=user_in)

    def assign_trainer_to_athlete(self, db: Session, assignment_request: AssignTrainerRequest) -> Optional[User]:

        athlete_user = self.repository.get(db, id=assignment_request.athlete_id)
        trainer_user_profile = db.query(Trainer).filter(Trainer.id == assignment_request.trainer_id).first()

        if not athlete_user or athlete_user.role != UserRole.ATHLETE:

            return None 
        if not trainer_user_profile:

            return None


        return self.repository.assign_trainer_to_athlete_repo(
            db, athlete_id=assignment_request.athlete_id, trainer_id=assignment_request.trainer_id
        )

    def get_athletes_for_trainer(self, db: Session, trainer_id: int) -> List[User]:

        trainer_profile = db.query(Trainer).filter(Trainer.id == trainer_id).first()
        if not trainer_profile:
            return []
        return self.repository.get_athletes_by_trainer(db, trainer_id=trainer_id)


user_service = UserService(user_repository)
