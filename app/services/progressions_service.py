from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import workout_models as models, workout_schemas
from app.repositories.progressions_repository import ProgressionsRepository

class ProgressionsService:
    
    def __init__(self, db: Session):
        self.repository = ProgressionsRepository(db)
    
    def _get_user_max(self, user_max_id: int) -> models.UserMax:
        user_max = self.repository.get_user_max(user_max_id)
        if not user_max:
            raise HTTPException(status_code=404, detail="UserMax not found")
        return user_max
    
    def _get_progression(self, progression_id: int) -> models.Progressions:
        progression = self.repository.get_progression_by_id(progression_id)
        if progression is None:
            raise HTTPException(status_code=404, detail="Progression not found")
        return progression
    
    def _prepare_progression_response(
        self, 
        progression: models.Progressions, 
        user_max: models.UserMax
    ) -> Dict[str, Any]:
        """Prepare a progression response dictionary."""
        # Calculate the weight if not already set
        calculated_weight = None
        if hasattr(progression, 'get_calculated_weight'):
            calculated_weight = progression.get_calculated_weight()
        
        # Calculate the volume based on intensity and effort
        calculated_volume = None
        if hasattr(progression, 'calculate_volume'):
            calculated_volume = progression.calculate_volume()
            # If volume is a string (like '3-4'), convert it to an integer (take the first number)
            if isinstance(calculated_volume, str):
                try:
                    calculated_volume = int(''.join(filter(str.isdigit, calculated_volume)) or '0')
                except (ValueError, TypeError):
                    calculated_volume = 0
        
        return {
            "id": progression.id,
            "user_max_id": getattr(progression, 'user_max_id', None),
            "volume": calculated_volume or getattr(progression, 'volume', None),
            "weight": getattr(progression, 'weight', None),
            "rpe": getattr(progression, 'effort', None),  # Using effort as RPE
            "date": str(getattr(progression, 'date', None)) if getattr(progression, 'date', None) else None,
            "user_max_display": str(user_max) if user_max else "",
            # Backward compatibility fields
            "sets": getattr(progression, 'sets', None),
            "intensity": getattr(progression, 'intensity', None),
            "effort": getattr(progression, 'effort', None),
            "calculated_weight": calculated_weight
        }
    


    def _calculate_intensity(self, weight: float, max_weight: float) -> int:
        """"""
        if not max_weight or max_weight <= 0:
            return 0
        return round((weight / max_weight) * 100)

    def _calculate_effort(self, intensity: int, volume: int) -> float:
        """"""
        if intensity >= 90:
            return 9.0 if volume <= 3 else 9.5
        elif intensity >= 80:
            if volume <= 3:
                return 8.0
            elif volume <= 5:
                return 8.5
            else:
                return 9.0
        elif intensity >= 70:
            if volume <= 5:
                return 7.0
            elif volume <= 8:
                return 7.5
            else:
                return 8.0
        else:
            if volume <= 8:
                return 6.0
            elif volume <= 10:
                return 6.5
            else:
                return 7.0

    def _estimate_volume(self, intensity: int, effort: float) -> int:
        """"""
        if intensity >= 90:
            if effort <= 8.0:
                return 1
            elif effort <= 8.5:
                return 2
            else:
                return 3
        elif intensity >= 80:
            if effort <= 7.5:
                return 3
            elif effort <= 8.0:
                return 4
            elif effort <= 8.5:
                return 5
            else:
                return 6
        elif intensity >= 70:
            if effort <= 7.0:
                return 6
            elif effort <= 7.5:
                return 7
            elif effort <= 8.0:
                return 8
            else:
                return 9
        else:
            if effort <= 6.5:
                return 9
            elif effort <= 7.0:
                return 10
            else:
                return 12

    def _estimate_intensity(self, effort: float, volume: int) -> int:
        """"""
        if volume <= 3:
            if effort <= 8.0: return 90
            elif effort <= 8.5: return 87
            else: return 84
        elif volume <= 5:
            if effort <= 7.5: return 85
            elif effort <= 8.0: return 82
            elif effort <= 8.5: return 80
            else: return 77
        elif volume <= 8:
            if effort <= 7.0: return 80
            elif effort <= 7.5: return 77
            elif effort <= 8.0: return 75
            else: return 72
        else:
            if effort <= 6.5: return 70
            elif effort <= 7.0: return 67
            else: return 65

    def create_progression(self, progression_data: workout_schemas.ProgressionsCreate) -> Dict[str, Any]:
        user_max = self._get_user_max(progression_data.user_max_id)
        data = progression_data.model_dump()
        

        if data.get('intensity') is None:
            if data.get('effort') is not None and data.get('volume') is not None:
                data['intensity'] = self._estimate_intensity(data['effort'], data['volume'])
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Either 'intensity' or both 'effort' and 'volume' must be provided"
                )
        

        if data.get('effort') is None and data.get('volume') is not None:
            data['effort'] = self._calculate_effort(data['intensity'], data['volume'])

        elif data.get('volume') is None and data.get('effort') is not None:
            data['volume'] = self._estimate_volume(data['intensity'], data['effort'])
        
        db_progression = self.repository.create_progression(data)
        return self._prepare_progression_response(db_progression, user_max)
    
    def get_progressions(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        progressions = self.repository.get_progressions(skip, limit)
        result = []
        for progression in progressions:
            try:
                user_max = getattr(progression, 'user_max', None)
                if user_max is None:
                    continue
                result.append(self._prepare_progression_response(progression, user_max))
            except Exception as e:
                print(f"Error preparing progression {progression.id}: {str(e)}")
                continue
        return result
    
    def get_progression(self, progression_id: int) -> Dict[str, Any]:
        progression = self._get_progression(progression_id)
        if not hasattr(progression, 'user_max') or progression.user_max is None:
            raise HTTPException(
                status_code=404,
                detail=f"User max not found for progression {progression_id}"
            )
        return self._prepare_progression_response(progression, progression.user_max)
    
    def update_progression(self, progression_id: int, progression_data: workout_schemas.ProgressionsCreate) -> Dict[str, Any]:
        progression = self._get_progression(progression_id)
        data = progression_data.model_dump()
        
        # If volume is provided but effort is not, calculate effort
        if data.get('volume') is not None and data.get('effort') is None and 'intensity' in data:
            data['effort'] = self._calculate_effort(data['intensity'], data['volume'])
            
        updated_progression = self.repository.update_progression(progression, data)
        if not hasattr(updated_progression, 'user_max') or updated_progression.user_max is None:
            raise HTTPException(
                status_code=404,
                detail=f"User max not found for progression {progression_id}"
            )
        return self._prepare_progression_response(updated_progression, updated_progression.user_max)
    
    def delete_progression(self, progression_id: int) -> Dict[str, str]:
        progression = self._get_progression(progression_id)
        self.repository.delete_progression(progression)
        return {"detail": "Progression deleted"}
    
    def create_progression_template(self, template_data: workout_schemas.ProgressionTemplateCreate) -> models.ProgressionTemplate:
        user_max = self._get_user_max(template_data.user_max_id)
        return self.repository.create_progression_template(template_data.model_dump())
    
    def get_progression_templates(self, skip: int = 0, limit: int = 100) -> List[models.ProgressionTemplate]:
        return self.repository.get_progression_templates(skip, limit)
    
    def get_progression_template(self, template_id: int) -> models.ProgressionTemplate:
        template = self.repository.get_progression_template_by_id(template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Progression template not found")
        return template