from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import workout_models as models, workout_schemas
from app.repositories.progressions_repository import ProgressionsRepository

class ProgressionsService:
    
    def __init__(self, db: Session):
        self.repository = ProgressionsRepository(db)
    
    def create_progression(self, progression_data: workout_schemas.ProgressionsCreate) -> Dict[str, Any]:
    

        user_max = self.repository.get_user_max(progression_data.user_max_id)
        if not user_max:
            raise HTTPException(status_code=404, detail="UserMax not found")
        

        db_progression = self.repository.create_progression(progression_data.model_dump())
        

        return self._prepare_progression_response(db_progression, user_max)
    
    def get_progressions(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    
        progressions = self.repository.get_progressions(skip, limit)
        return [self._prepare_progression_response(progression) for progression in progressions]
    
    def get_progression(self, progression_id: int) -> Dict[str, Any]:
    
        progression = self.repository.get_progression_by_id(progression_id)
        if progression is None:
            raise HTTPException(status_code=404, detail="Progression not found")
        
        return self._prepare_progression_response(progression)
    
    def update_progression(self, progression_id: int, progression_data: workout_schemas.ProgressionsCreate) -> Dict[str, Any]:
    

        db_progression = self.repository.get_progression_by_id(progression_id)
        if db_progression is None:
            raise HTTPException(status_code=404, detail="Progression not found")
        

        updated_progression = self.repository.update_progression(db_progression, progression_data.model_dump())
        

        return self._prepare_progression_response(updated_progression)
    
    def delete_progression(self, progression_id: int) -> Dict[str, str]:
    

        db_progression = self.repository.get_progression_by_id(progression_id)
        if db_progression is None:
            raise HTTPException(status_code=404, detail="Progression not found")
        

        self.repository.delete_progression(db_progression)
        
        return {"detail": "Progression deleted"}
    
    def create_progression_template(self, template_data: workout_schemas.ProgressionTemplateCreate) -> models.ProgressionTemplate:
    

        user_max = self.repository.get_user_max(template_data.user_max_id)
        if not user_max:
            raise HTTPException(status_code=404, detail="UserMax not found")
        

        return self.repository.create_progression_template(template_data.model_dump())
    
    def get_progression_templates(self, skip: int = 0, limit: int = 100) -> List[models.ProgressionTemplate]:
    
        return self.repository.get_progression_templates(skip, limit)
    
    def get_progression_template(self, template_id: int) -> models.ProgressionTemplate:
    
        template = self.repository.get_progression_template_by_id(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Progression template not found")
        
        return template
    
    def _prepare_progression_response(self, progression: models.Progressions, user_max: Optional[models.UserMax] = None) -> Dict[str, Any]:
    
        result = progression.__dict__.copy()
        result["reps"] = progression.get_reps()
        result["calculated_weight"] = progression.get_calculated_weight()
        

        if user_max is None:
            user_max = progression.user_max
            
        result["user_max_display"] = str(user_max)
        
        return result
