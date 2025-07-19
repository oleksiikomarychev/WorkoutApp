from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from app.workout_models import UserMax, ExerciseList
from app.repositories.base_repository import BaseRepository
from app.workout_schemas import UserMaxCreate

class UserMaxRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_max(self, user_max_id: int) -> Optional[UserMax]:
        return self.get_user_max_by_id(user_max_id)
        
    def get_user_max_by_id(self, user_max_id: int) -> Optional[UserMax]:
        return self.db.query(UserMax).options(
            joinedload(UserMax.exercise)
        ).filter(UserMax.id == user_max_id).first()
    
    def get_user_maxes_by_user(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[UserMax]:
        return self.db.query(UserMax).options(
            joinedload(UserMax.exercise)
        ).filter(UserMax.user_id == user_id).offset(skip).limit(limit).all()
    
    def get_user_max_by_exercise(
        self, 
        user_id: int, 
        exercise_id: int
    ) -> Optional[UserMax]:
        return self.db.query(UserMax).filter(
            UserMax.user_id == user_id,
            UserMax.exercise_id == exercise_id
        ).first()
    
    def create_user_max(self, user_id: int, user_max_data: Dict[str, Any]) -> UserMax:
        user_max = UserMax(
            user_id=user_id,
            exercise_id=user_max_data["exercise_id"],
            max_weight=user_max_data["max_weight"],
            rep_max=user_max_data["rep_max"]
        )
        self.db.add(user_max)
        self.db.commit()
        self.db.refresh(user_max)
        return user_max
    
    def update_user_max(
        self, 
        user_max_id: int, 
        user_max_data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Optional[UserMax]:
        query = self.db.query(UserMax).filter(UserMax.id == user_max_id)
        
        if user_id is not None:
            query = query.filter(UserMax.user_id == user_id)
            
        user_max = query.first()
        if not user_max:
            return None
            
        for key, value in user_max_data.items():
            setattr(user_max, key, value)
            
        self.db.commit()
        self.db.refresh(user_max)
        return user_max
    
    def delete_user_max(
        self, 
        user_max_id: int, 
        user_id: Optional[int] = None
    ) -> bool:
        query = self.db.query(UserMax).filter(UserMax.id == user_max_id)
        
        if user_id is not None:
            query = query.filter(UserMax.user_id == user_id)
            
        user_max = query.first()
        if not user_max:
            return False
            
        self.db.delete(user_max)
        self.db.commit()
        return True
    
    def get_or_create_user_max(
        self, 
        user_id: int, 
        exercise_id: int, 
        defaults: Optional[Dict[str, Any]] = None
    ) -> UserMax:
        if defaults is None:
            defaults = {}
            
        user_max = self.get_user_max_by_exercise(user_id, exercise_id)
        if user_max:
            return user_max
            
        create_data = {
            "exercise_id": exercise_id,
            "max_weight": defaults.get("max_weight", 0),
            "rep_max": defaults.get("rep_max", 1)
        }
        return self.create_user_max(user_id, create_data)
