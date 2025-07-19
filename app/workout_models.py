from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum as SQLEnum, Boolean, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
import enum
import json
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from app.config.prompts import RPE_TABLE

class EffortType(str, enum.Enum):
    RPE = "RPE"
    RIR = "RIR"


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    
    exercise_instances = relationship(
        "ExerciseInstance", 
        back_populates="workout", 
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    def __repr__(self):
        return f"<Workout(id={self.id}, name='{self.name}')>"


class ExerciseList(Base):
    __tablename__ = "exercise_list"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    muscle_group = Column(String(255), nullable=True)
    equipment = Column(String(255), nullable=True)

    instances = relationship("ExerciseInstance", back_populates="exercise_definition", cascade="all, delete-orphan")
    user_maxes = relationship("UserMax", back_populates="exercise")

    def __repr__(self):
        return f"<ExerciseList(id={self.id}, name='{self.name}')>"


class ExerciseInstance(Base):
    __tablename__ = "exercise_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    exercise_list_id = Column(Integer, ForeignKey("exercise_list.id", ondelete="CASCADE"), nullable=False)
    progression_template_id = Column(Integer, ForeignKey("progression_templates.id", ondelete="SET NULL"), nullable=True)
    volume = Column(Integer, nullable=True)
    intensity = Column(Integer, nullable=True)
    effort = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    
    exercise_definition = relationship("ExerciseList", back_populates="instances")
    workout = relationship("Workout", back_populates="exercise_instances")
    progression_template = relationship("ProgressionTemplate", back_populates="exercise_instances",lazy="selectin")
    
    def __repr__(self):
        return (
            f"<ExerciseInstance(id={self.id}, "
            f"exercise_id={self.exercise_id}, "
            f"workout_id={self.workout_id}, "
            f"progression_template_id={self.progression_template_id})>"
        )
    
    def apply_progression_template(self, template: 'ProgressionTemplate') -> None:
        if not template:
            return
            
        self.progression_template = template
        self.intensity = template.intensity
        self.effort = template.effort
        self.volume = template.volume if template.volume else None
        
        if template.user_max and template.user_max.max_weight:
            self.weight = round(template.user_max.max_weight * (template.intensity / 100.0), 2)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'id': self.id,
            'exercise_id': self.exercise_id,
            'workout_id': self.workout_id,
            'progression_template_id': self.progression_template_id,
            'volume': self.volume,
            'intensity': self.intensity,
            'effort': self.effort,
            'weight': self.weight,
            'exercise': {
                'id': self.exercise.id,
                'name': self.exercise.name,
                'exercise_definition_id': self.exercise.exercise_definition_id
            } if self.exercise else None,
        }
        
        if self.progression_template:
            result['progression_template'] = {
                'id': self.progression_template.id,
                'name': self.progression_template.name,
                'intensity': self.progression_template.intensity,
                'effort': self.progression_template.effort,
                'volume': self.progression_template.volume,
                'calculated_weight': self.progression_template.get_calculated_weight(),
            }
            
        return result



class UserMax(Base):
    __tablename__ = "user_maxes"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercise_list.id"), nullable=False)
    max_weight = Column(Integer, nullable=False)
    rep_max = Column(Integer, nullable=False)
    
    exercise = relationship("ExerciseList", back_populates="user_maxes")
    progression_templates = relationship("ProgressionTemplate", back_populates="user_max")
    
    def __str__(self):
        return f"{self.exercise.name}: {self.max_weight}kg x {self.rep_max}"



class ProgressionTemplate(Base):
    __tablename__ = "progression_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    user_max_id = Column(Integer, ForeignKey("user_maxes.id", ondelete="CASCADE"), nullable=False)
    intensity = Column(Integer, nullable=False)
    volume = Column(Integer, nullable=True)
    effort = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False)

    # Relationships
    user_max = relationship("UserMax", back_populates="progression_templates")
    exercise_instances = relationship(
        "ExerciseInstance", 
        back_populates="progression_template",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
    def __init__(self, **kwargs):
        if 'effort' in kwargs and kwargs['effort'] is not None:
            kwargs['effort'] = round(kwargs['effort'] * 2) / 2
        super().__init__(**kwargs)
    
    RPE_TABLE = RPE_TABLE
    
    def get_volume(self) -> Union[int, str, None]:
        if not hasattr(self, 'intensity') or not hasattr(self, 'effort'):
            return None
            
        rounded_intensity = round(self.intensity / 5) * 5
        rounded_intensity = max(60, min(100, rounded_intensity))
        
        rounded_effort = round(self.effort * 2) / 2
        rounded_effort = max(6, min(10, rounded_effort))
        
        try:
            intensity_key = min(
                self.RPE_TABLE.keys(), 
                key=lambda x: abs(x - rounded_intensity)
            )
            
            effort_key = min(
                self.RPE_TABLE[intensity_key].keys(), 
                key=lambda x: abs(x - rounded_effort)
            )
            
            return self.RPE_TABLE[intensity_key].get(effort_key, None)
        except (KeyError, ValueError):
            return None
    
    def get_calculated_weight(self) -> Optional[float]:
        if not self.user_max or not self.user_max.max_weight:
            return None
        return round(self.user_max.max_weight * (self.intensity / 100.0), 2)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'user_max_id': self.user_max_id,
            'intensity': self.intensity,
            'volume': self.volume,
            'effort': self.effort,
            'calculated_weight': self.get_calculated_weight(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_max': {
                'id': self.user_max.id,
                'exercise_id': self.user_max.exercise_id,
                'max_weight': self.user_max.max_weight,
                'rep_max': self.user_max.rep_max,
                'exercise_name': self.user_max.exercise.name if self.user_max.exercise else None
            } if self.user_max else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressionTemplate':
        return cls(
            name=data.get('name'),
            user_max_id=data.get('user_max_id'),
            intensity=data.get('intensity'),
            volume=data.get('volume'),
            effort=data.get('effort')
        )
    
    def update_volume(self):
        """Calculates and sets the volume (reps) based on intensity and effort using the RPE table."""
        if self.intensity is None or self.effort is None:
            self.volume = None
            return

        calculated_volume = self.get_volume()

        if isinstance(calculated_volume, int):
            self.volume = calculated_volume
        else:
            # If get_volume returns a string (e.g., "1-3") or None, keep volume as None
            self.volume = None
