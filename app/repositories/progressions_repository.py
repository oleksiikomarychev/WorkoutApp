from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app import workout_models as models

class ProgressionsRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_progression(self, progression_data: dict) -> models.Progressions:
    
        db_progression = models.Progressions(**progression_data)
        db_progression.update_volume()
        self.db.add(db_progression)
        self.db.commit()
        self.db.refresh(db_progression)
        return db_progression
    
    def get_progressions(self, skip: int = 0, limit: int = 100) -> List[models.Progressions]:
    
        return self.db.query(models.Progressions).offset(skip).limit(limit).all()
    
    def get_progression_by_id(self, progression_id: int) -> Optional[models.Progressions]:
    
        return self.db.query(models.Progressions).filter(models.Progressions.id == progression_id).first()
    
    def update_progression(self, db_progression: models.Progressions, progression_data: dict) -> models.Progressions:
    
        for key, value in progression_data.items():
            setattr(db_progression, key, value)
        
        db_progression.update_volume()
        self.db.commit()
        self.db.refresh(db_progression)
        return db_progression
    
    def delete_progression(self, db_progression: models.Progressions) -> None:
    
        self.db.delete(db_progression)
        self.db.commit()
    
    def get_user_max(self, user_max_id: int) -> Optional[models.UserMax]:
    
        return self.db.query(models.UserMax).filter(models.UserMax.id == user_max_id).first()
    

    
    def create_progression_template(self, template_data: dict) -> models.ProgressionTemplate:
    
        db_template = models.ProgressionTemplate(**template_data)
        db_template.update_volume()
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template
    
    def get_progression_templates(self, skip: int = 0, limit: int = 100) -> List[models.ProgressionTemplate]:
    
        return self.db.query(models.ProgressionTemplate).offset(skip).limit(limit).all()
    
    def get_progression_template_by_id(self, template_id: int) -> Optional[models.ProgressionTemplate]:
    
        return self.db.query(models.ProgressionTemplate).filter(models.ProgressionTemplate.id == template_id).first()
    

    def create_llm_progression(self, progression_data: dict) -> models.LLMProgression:
    
        db_progression = models.LLMProgression(**progression_data)
        db_progression.update_volume()
        self.db.add(db_progression)
        self.db.commit()
        self.db.refresh(db_progression)
        return db_progression
    
    def get_llm_progressions(self, skip: int = 0, limit: int = 100) -> List[models.LLMProgression]:
    
        return self.db.query(models.LLMProgression).offset(skip).limit(limit).all()
    
    def get_llm_progression_by_id(self, progression_id: int) -> Optional[models.LLMProgression]:
    
        return self.db.query(models.LLMProgression).filter(models.LLMProgression.id == progression_id).first()
    
    def update_llm_progression(self, db_progression: models.LLMProgression, progression_data: dict) -> models.LLMProgression:
    
        for key, value in progression_data.items():
            setattr(db_progression, key, value)
        
        db_progression.update_volume()
        self.db.commit()
        self.db.refresh(db_progression)
        return db_progression
    
    def delete_llm_progression(self, progression: models.LLMProgression) -> None:
        self.db.delete(progression)
        self.db.commit()
