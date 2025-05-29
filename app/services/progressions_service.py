from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException
import requests
import json
from sqlalchemy.orm import Session
from app import workout_models as models, workout_schemas
from app.repositories.progressions_repository import ProgressionsRepository
from app.config.config import settings, LLM_PROMPT

class ProgressionsService:
    
    def __init__(self, db: Session):
        self.repository = ProgressionsRepository(db)
        self.llm_api_key = settings.GEMINI_API_KEY
        self.llm_prompt_template = LLM_PROMPT
    
    def _get_user_max(self, user_max_id: int) -> models.UserMax:
        user_max = self.repository.get_user_max(user_max_id)
        if not user_max:
            raise HTTPException(status_code=404, detail="UserMax not found")
        return user_max
    
    def _get_progression(self, progression_id: int, is_llm: bool = False) -> models.Progressions:
        if is_llm:
            progression = self.repository.get_llm_progression_by_id(progression_id)
            if progression is None:
                raise HTTPException(status_code=404, detail="AI progression not found")
            return progression
            
        progression = self.repository.get_progression_by_id(progression_id)
        if progression is None:
            raise HTTPException(status_code=404, detail="Progression not found")
        return progression
    
    def _prepare_progression_response(
        self, 
        progression: models.Progressions, 
        user_max: models.UserMax
    ) -> Dict[str, Any]:
        """"""
        if hasattr(progression, 'sets') and hasattr(progression, 'intensity'):
    
            response_data = {
                'id': progression.id,
                'user_max_id': progression.user_max_id,
                'sets': getattr(progression, 'sets', 0) or 0,
                'intensity': getattr(progression, 'intensity', 0) or 0,
                'effort': float(getattr(progression, 'effort', 0.0)) if getattr(progression, 'effort', None) is not None else 0.0,
                'volume': getattr(progression, 'volume', 0) or 0,
                'calculated_weight': getattr(progression, 'get_calculated_weight', lambda: 0)() or 0,
                'user_max_display': str(user_max) if user_max else "",
                'user_data': getattr(progression, 'user_data', {}) or {}
            }
            return workout_schemas.LLMProgressionResponse.model_validate(response_data).model_dump()
        

        return {
            "id": progression.id,
            "user_max_id": getattr(progression, 'user_max_id', None),
            "volume": getattr(progression, 'volume', None),
            "weight": getattr(progression, 'weight', None),
            "rpe": getattr(progression, 'rpe', None),
            "date": getattr(progression, 'date', None),
            "user_max_display": str(user_max) if user_max else "",
            "user_data": getattr(progression, 'user_data', {}) or {}
        }
    
    def _update_progression_volume(self, progression: models.LLMProgression) -> None:
        """"""
        progression.update_volume()
        self.repository.db.commit()
        self.repository.db.refresh(progression)

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
        return [
            self._prepare_progression_response(progression, progression.user_max)
            for progression in progressions
            if hasattr(progression, 'user_max') and progression.user_max is not None
        ]
    
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
    
    def _parse_intensity_value(self, intensity_str: Any) -> float:
        """Parse intensity value from various string formats to float."""
        if isinstance(intensity_str, (int, float)):
            return float(max(50, min(100, intensity_str)))  # Clamp between 50-100%
            
        if not isinstance(intensity_str, str):
            return 75.0  # Default value if not a string
            
        try:
            # Handle ranges like '80-85' by taking the average
            if '-' in intensity_str:
                values = [float(x.strip()) for x in intensity_str.split('-') if x.strip().replace('.', '').isdigit()]
                if values:
                    avg = sum(values) / len(values)
                    return max(50.0, min(100.0, avg))  # Clamp between 50-100%
            
            # Handle single value
            intensity = float(intensity_str.strip())
            return max(50.0, min(100.0, intensity))  # Clamp between 50-100%
            
        except (ValueError, TypeError):
            return 75.0  # Default value on parse error
    
    def _parse_set_value(self, set_str: Any) -> int:
        """Parse set value from various string formats to int."""
        if isinstance(set_str, (int, float)):
            return max(1, int(set_str))  # Ensure at least 1 set
            
        if not isinstance(set_str, str):
            return 3  # Default value if not a string
            
        try:
            # Handle ranges like '3-4' by taking the first number
            if '-' in set_str:
                first_num = set_str.split('-')[0].strip()
                if first_num.replace('.', '').isdigit():
                    return max(1, int(float(first_num)))
            
            # Handle single value
            return max(1, int(float(set_str.strip())))
            
        except (ValueError, TypeError):
            return 3  # Default value on parse error
    
    def _parse_effort_value(self, effort_str: Any) -> float:
        """Parse effort value from various string formats to float."""
        if isinstance(effort_str, (int, float)):
            return float(effort_str)
            
        if not isinstance(effort_str, str):
            return 8.0  # Default value if not a string
            
        try:
            # Handle ranges like '7-8' by taking the average
            if '-' in effort_str:
                values = [float(x.strip()) for x in effort_str.split('-') if x.strip().replace('.', '').isdigit()]
                if values:
                    return sum(values) / len(values)
            
            # Handle single value
            return float(effort_str.strip())
            
        except (ValueError, TypeError):
            return 8.0  # Default value on parse error
    
    def _generate_llm_recommendation(self, user_max: models.UserMax, user_data: dict) -> Dict[str, Any]:
        """Generate workout recommendations using the Gemini API."""
        try:
            # Prepare the prompt with user data
            prompt = self.llm_prompt_template.format(
                exercise_name=user_max.exercise.name,
                max_weight=user_max.max_weight,
                rep_max=user_max.rep_max or 1,
                recent_workouts=user_data.get('recent_workouts', 'No recent workout data'),
            )
            
            # Call Gemini API using the specified format
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.llm_api_key}"
            headers = {
                'Content-Type': 'application/json',
            }
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            # Extract the response text
            response_json = response.json()
            if 'candidates' not in response_json or not response_json['candidates']:
                raise ValueError("No candidates in API response")
                
            response_text = response_json['candidates'][0]['content']['parts'][0]['text']
            
            # Try to parse the JSON response
            try:
                # Extract JSON from markdown code block if present
                if '```json' in response_text:
                    json_str = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    json_str = response_text.split('```')[1].split('```')[0].strip()
                else:
                    json_str = response_text.strip()
                
                return json.loads(json_str)
            except (json.JSONDecodeError, IndexError) as e:
                # Fallback to default values if parsing fails
                print(f"Failed to parse LLM response: {e}")
                return {
                    "sets": 3,
                    "intensity": 75,
                    "effort": 8.0,
                    "recommendation": "Default recommendation - LLM response parsing failed"
                }
                
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            # Return default values if API call fails
            return {
                "sets": 3,
                "intensity": 75,
                "effort": 8.0,
                "recommendation": "Default recommendation - LLM service unavailable"
            }
    
    def create_llm_progression(self, progression_data: workout_schemas.LLMProgressionCreate) -> Dict[str, Any]:

        user_max = self._get_user_max(progression_data.user_max_id)
        

        user_data = progression_data.user_data or {}
        

        recommendation = self._generate_llm_recommendation(user_max, user_data)
        

        progression_values = {
            **progression_data.model_dump(),
            'sets': self._parse_set_value(recommendation.get('sets', 3)),
            'intensity': self._parse_intensity_value(recommendation.get('intensity', 75)),
            'effort': self._parse_effort_value(recommendation.get('effort', 8.0)),
            'volume': 0,
            'user_data': {
                **(user_data or {}),
                'llm_recommendation': recommendation.get('recommendation', ''),
                'generated_at': datetime.utcnow().isoformat()
            }
        }
        

        db_progression = self.repository.create_llm_progression(progression_values)
        

        self._update_progression_volume(db_progression)
        

        updated_progression = self._get_progression(db_progression.id)
        
        return self._prepare_progression_response(updated_progression, user_max)
    
    def get_llm_progressions(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        progressions = self.repository.get_llm_progressions(skip, limit)
        result = []
        for progression in progressions:
            user_max = getattr(progression, 'user_max', None)
            if user_max is None and hasattr(progression, 'user_max_id'):
    
                user_max = self._get_user_max(progression.user_max_id)
            
            if user_max is not None:
                result.append(self._prepare_progression_response(progression, user_max))
        return result
    
    def get_llm_progression(self, progression_id: int) -> Dict[str, Any]:
        progression = self._get_progression(progression_id, is_llm=True)
        user_max = self._get_user_max(progression.user_max_id)
        return self._prepare_progression_response(progression, user_max)
    
    def update_llm_progression(self, progression_id: int, progression_data: workout_schemas.LLMProgressionCreate) -> Dict[str, Any]:

        progression = self._get_progression(progression_id, is_llm=True)
        user_max = self._get_user_max(progression_data.user_max_id)
        

        updated_progression = self.repository.update_llm_progression(
            progression, 
            progression_data.model_dump()
        )
        

        self._update_progression_volume(updated_progression)
        
        return self._prepare_progression_response(updated_progression, user_max)
    
    def delete_llm_progression(self, progression_id: int) -> Dict[str, str]:
        progression = self._get_progression(progression_id, is_llm=True)
        self.repository.delete_llm_progression(progression)
        return {"detail": "LLM Progression deleted"}