from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum as SQLEnum, Boolean, Text, JSON, DateTime
from sqlalchemy.orm import relationship, validates
from app.database import Base
import enum
import json
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from app.config.prompts import RPE_TABLE
from app.workout_calculation import WorkoutCalculator

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
    progression_associations = relationship("ExerciseInstanceWithProgressionTemplate", back_populates="exercise_list", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExerciseList(id={self.id}, name='{self.name}')>"


class ExerciseInstance(Base):
    __tablename__ = "exercise_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    exercise_list_id = Column(Integer, ForeignKey("exercise_list.id", ondelete="CASCADE"), nullable=False)
    user_max_id = Column(Integer, ForeignKey("user_maxes.id", ondelete="SET NULL"), nullable=True)
    weight = Column(Integer, nullable=True)
    sets_and_reps = Column(JSON, nullable=False, default=list)  # New field for sets and reps
    
    exercise_definition = relationship("ExerciseList", back_populates="instances")
    workout = relationship("Workout", back_populates="exercise_instances")
    progression_association = relationship(
        "ExerciseInstanceWithProgressionTemplate",
        foreign_keys=[exercise_list_id],
        primaryjoin="ExerciseInstance.exercise_list_id == ExerciseInstanceWithProgressionTemplate.exercise_list_id",
        uselist=False,
        lazy="selectin",
        overlaps="exercise_definition,instances,progression_association"
    )
    user_max = relationship("UserMax", back_populates="exercise_instances", lazy="selectin")
    
    @property
    def progression_template(self):
        """Get the associated progression template."""
        if not self.progression_association:
            return None
        return self.progression_association.progression_template
    
    @property
    def current_progression(self):
        if self.progression_template:
            return {
                'intensity': self.progression_template.intensity,
                'effort': self.progression_template.effort,
                'volume': self.progression_template.volume
            }
        return None
    
    def __repr__(self):
        return (
            f"<ExerciseInstance(id={self.id}, "
            f"exercise_id={self.exercise_id}, "
            f"workout_id={self.workout_id}, "
            f"progression_template_id={self.progression_template_id})>"
        )
    
    def apply_progression_template(self, template: 'ProgressionTemplate', db) -> None:
        if not template:
            return
            
        # Create or update the ExerciseInstanceWithProgressionTemplate
        progression_instance = db.query(ExerciseInstanceWithProgressionTemplate).filter(
            ExerciseInstanceWithProgressionTemplate.exercise_instance_id == self.id,
            ExerciseInstanceWithProgressionTemplate.progression_template_id == template.id
        ).first()
        
        if not progression_instance:
            progression_instance = ExerciseInstanceWithProgressionTemplate(
                exercise_instance_id=self.id,
                progression_template_id=template.id,
                intensity=template.intensity,
                effort=template.effort,
                volume=WorkoutCalculator.get_volume(template.intensity, template.effort),
                sets_and_reps=[]  # Default empty list, should be set appropriately
            )
            db.add(progression_instance)
            db.commit()
            db.refresh(progression_instance)
            
        # Calculate weight based on user_max
        if self.user_max and self.user_max.max_weight:
            self.weight = WorkoutCalculator.calculate_weight(self.user_max.max_weight, template.intensity)
        else:
            self.weight = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'id': self.id,
            'exercise_id': self.exercise_id,
            'workout_id': self.workout_id,
            'progression_template_id': self.progression_template_id,
            'user_max_id': self.user_max_id,
            'volume': self.volume if hasattr(self, 'volume') else None,
            'intensity': self.intensity if hasattr(self, 'intensity') else None,
            'effort': self.effort if hasattr(self, 'effort') else None,
            'weight': self.weight,
            'sets_and_reps': self.sets_and_reps,
            'exercise': {
                'id': self.exercise.id,
                'name': self.exercise.name,
                'exercise_definition_id': self.exercise.exercise_definition_id
            } if self.exercise else None,
            'user_max': {
                'id': self.user_max.id,
                'max_weight': self.user_max.max_weight,
                'rep_max': self.user_max.rep_max
            } if self.user_max else None
        }
        
        if self.progression_template:
            result['progression_template'] = {
                'id': self.progression_template.id,
                'name': self.progression_template.name,
                'intensity': self.progression_template.intensity,
                'effort': self.progression_template.effort,
                'volume': self.progression_template.volume
            }
            
        return result



class UserMax(Base):
    __tablename__ = "user_maxes"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercise_list.id"), nullable=False)
    max_weight = Column(Integer, nullable=False)
    rep_max = Column(Integer, nullable=False)
    
    exercise = relationship("ExerciseList", back_populates="user_maxes")
    exercise_instances = relationship("ExerciseInstance", back_populates="user_max", cascade="all, delete-orphan")
    
    def __str__(self):
        return f"{self.exercise.name}: {self.max_weight}kg x {self.rep_max}"



class ExerciseInstanceWithProgressionTemplate(Base):
    __tablename__ = "exercise_instances_with_progression_template"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_list_id = Column(Integer, ForeignKey("exercise_list.id", ondelete="CASCADE"), nullable=False)
    progression_template_id = Column(Integer, ForeignKey("progression_templates.id", ondelete="SET NULL"), nullable=True)
    intensity = Column(Integer, nullable=False)
    effort = Column(Integer, nullable=False)
    volume = Column(Integer, nullable=False)
    sets_and_reps = Column(JSON, nullable=False, default=list)  # New field for sets and reps
    
    exercise_list = relationship("ExerciseList", back_populates="progression_associations")
    progression_template = relationship("ProgressionTemplate", back_populates="exercise_instances")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Optionally, calculate volume from sets_and_reps if needed
        if hasattr(self, 'sets_and_reps') and self.sets_and_reps:
            self.volume = sum(item.get('sets', 0) * item.get('reps', 0) for item in self.sets_and_reps)
        else:
            self.volume = 0

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

class ProgressionTemplate(Base):
    __tablename__ = "progression_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    exercise_instances = relationship(
        "ExerciseInstanceWithProgressionTemplate", 
        back_populates="progression_template",
        cascade="all, delete-orphan"
    )
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
    @property
    def exercise_list_instances(self):
        return [assoc.exercise_list for assoc in self.exercise_list_associations]

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'id': self.id,
            'name': self.name,
        }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressionTemplate':
        return cls(**data)