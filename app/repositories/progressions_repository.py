from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from app.workout_models import ProgressionTemplate, UserMax, Workout
from app.workout_schemas import ProgressionTemplateCreate


class ProgressionsRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_progression_templates(
        self, 
        skip: int = 0, 
        limit: int = 100,
        user_max_id: Optional[int] = None
    ) -> List[ProgressionTemplate]:
        query = (
            self.db.query(ProgressionTemplate)
            .options(
                joinedload(ProgressionTemplate.user_max)
                .joinedload(UserMax.exercise)
            )
        )
        
        if user_max_id is not None:
            query = query.filter(ProgressionTemplate.user_max_id == user_max_id)
            
        return query.offset(skip).limit(limit).all()
    
    def get_progression_template_by_id(self, template_id: int) -> Optional[ProgressionTemplate]:
        return (
            self.db.query(ProgressionTemplate)
            .options(
                joinedload(ProgressionTemplate.user_max)
                .joinedload(UserMax.exercise)
            )
            .filter(ProgressionTemplate.id == template_id)
            .first()
        )
    
    def get_progression_templates_by_user_max(self, user_max_id: int) -> List[ProgressionTemplate]:
        return self.get_progression_templates(user_max_id=user_max_id)
    
    def create_progression_template(self, template_data: Dict[str, Any]) -> ProgressionTemplate:
        db_template = ProgressionTemplate(**template_data)
        db_template.update_volume()
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template
    
    def update_progression_template(
        self, 
        db_template: ProgressionTemplate,
        template_data: Dict[str, Any]
    ) -> ProgressionTemplate:
        for key, value in template_data.items():
            setattr(db_template, key, value)
            
        if 'intensity' in template_data or 'effort' in template_data:
            db_template.update_volume()
            
        self.db.commit()
        self.db.refresh(db_template)
        return db_template
    
    def delete_progression_template(self, template: ProgressionTemplate) -> bool:
        try:
            self.db.query(Workout).filter(
                Workout.progression_template_id == template.id
            ).update({
                Workout.progression_template_id: None
            })
            
            self.db.delete(template)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e
    
    def get_template_usage_count(self, template_id: int) -> int:
        return self.db.query(Workout).filter(
            Workout.progression_template_id == template_id
        ).count()
