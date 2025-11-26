from typing import List, Optional

from pydantic import BaseModel, Field


class ParamsSets(BaseModel):
    intensity: Optional[int] = Field(default=None, ge=0, le=110)
    effort: Optional[int] = Field(default=None, ge=1, le=10)
    volume: Optional[int] = Field(default=None, ge=1)
    working_weight: Optional[float] = Field(default=None, exclude=True)  # Only for workout instances, not for plans


class ExerciseScheduleItem(BaseModel):
    """Схема для элемента расписания"""

    exercise_id: int
    sets: List[ParamsSets]

    class Config:
        from_attributes = True

    def model_dump(self, *args, **kwargs):
        # Create a copy of the model's dictionary
        data = super().model_dump(*args, **kwargs)
        # Remove working_weight from all sets if it exists
        if "sets" in data and data["sets"]:
            for set_item in data["sets"]:
                set_item.pop("working_weight", None)
        return data
