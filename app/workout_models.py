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
    progression_template_id = Column(Integer, ForeignKey("progression_templates.id"), nullable=True)
    
    progression_template = relationship(
        "ProgressionTemplate",
        foreign_keys=[progression_template_id],
        post_update=True,
    )
    
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
    name = Column(String(255), nullable=False)
    muscle_group = Column(String(100), nullable=True)
    equipment = Column(String(255), nullable=True)
    
    # Relationships
    user_maxes = relationship("UserMax", back_populates="exercise")
    exercises = relationship("Exercise", back_populates="exercise_definition")


class Exercise(Base):
    __tablename__ = "exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    exercise_definition_id = Column(Integer, ForeignKey("exercise_list.id"), nullable=True)
    
    # Relationships
    exercise_definition = relationship("ExerciseList", back_populates="exercises")
    instances = relationship(
        "ExerciseInstance", 
        back_populates="exercise", 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Exercise(id={self.id}, name='{self.name}')>"


class ExerciseInstance(Base):
    __tablename__ = "exercise_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    volume = Column(Integer, nullable=False)
    intensity = Column(Integer, nullable=False)
    effort = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=True)
    
    # Relationships
    exercise = relationship("Exercise", back_populates="instances")
    workout = relationship("Workout", back_populates="exercise_instances")
    
    def __repr__(self):
        return f"<ExerciseInstance(id={self.id}, exercise_id={self.exercise_id}, workout_id={self.workout_id})>"



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
    user_max_id = Column(Integer, ForeignKey("user_maxes.id"), nullable=False)
    intensity = Column(Integer, nullable=False)
    volume = Column(Integer, nullable=False)
    effort = Column(Integer, nullable=False)

    user_max = relationship("UserMax", back_populates="progression_templates")
    workouts = relationship("Workout", back_populates="progression_template")
    
    RPE_TABLE = RPE_TABLE
    
    def get_volume(self) -> Union[int, str]:
        intensity_rounded = min(self.RPE_TABLE.keys(), key=lambda x: abs(x - self.intensity))
        closest_effort = min(self.RPE_TABLE[intensity_rounded].keys(), key=lambda x: abs(x - self.effort))
        return self.RPE_TABLE[intensity_rounded].get(closest_effort, "N/A")
    
    def get_calculated_weight(self) -> Optional[int]:
        if not self.user_max or not self.user_max.max_weight:
            return None
        return round(self.user_max.max_weight * (self.intensity / 100.0))
    
    def calculate_volume(self) -> Union[int, str]:
        """
        Calculate the volume (number of repetitions) based on intensity and RPE effort.
        Returns either an integer or a string range (e.g., '3-4').
        """
        if not hasattr(self, 'intensity') or not hasattr(self, 'effort'):
            return 0
            
        # Round intensity to the nearest 5% to match our RPE table
        rounded_intensity = round(self.intensity / 5) * 5
        # Ensure intensity is within our table bounds (60-100%)
        rounded_intensity = max(60, min(100, rounded_intensity))
        
        # Round effort to nearest 0.5 for RPE
        rounded_effort = round(self.effort * 2) / 2
        # Ensure effort is within our table bounds (6-10)
        rounded_effort = max(6, min(10, rounded_effort))
        
        # Find the closest intensity in our table
        intensity_key = min(self.RPE_TABLE.keys(), key=lambda x: abs(x - rounded_intensity))
        
        # Find the closest effort in our table
        effort_key = min(self.RPE_TABLE[intensity_key].keys(), 
                        key=lambda x: abs(x - rounded_effort))
        
        return self.RPE_TABLE[intensity_key][effort_key]
    
    def update_volume(self):
        """Update the volume based on current intensity and effort."""
        if not hasattr(self, 'intensity') or not hasattr(self, 'effort'):
            return
            
        self.volume = self.calculate_volume()
        # If we got a string range (e.g., '3-4'), we'll store the lower bound as an integer
        if isinstance(self.volume, str):
            try:
                # Extract the first number from ranges like '3-4' or '12+'
                self.volume = int(''.join(filter(str.isdigit, self.volume)) or '0')
            except (ValueError, TypeError):
                self.volume = 0
        if hasattr(self, 'volume') and self.volume is not None:
            return
            
        self.volume = self.get_volume()
        if isinstance(self.volume, str):
            self.volume = 0
