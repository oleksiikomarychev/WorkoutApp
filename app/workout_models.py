from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum as SQLEnum, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum
import json
from typing import Optional, Dict, Any, Union, List


class EffortType(str, enum.Enum):
    RPE = "RPE"
    RIR = "RIR"


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    progression_template_id = Column(Integer, ForeignKey("progressions.id"), nullable=True)
    
    # Relationship with Progressions (one workout can have one progression template)
    progression_template = relationship(
        "Progressions",
        foreign_keys=[progression_template_id],
        post_update=True,
        # Don't cascade deletes to avoid circular dependencies
        # The progression template should be managed separately
    )
    
    # Relationship with Exercises (one-to-many, one workout has many exercises)
    exercises = relationship(
        "Exercise", 
        back_populates="workout", 
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class ExerciseList(Base):
    __tablename__ = "exercise_list"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    muscle_group = Column(String(100), nullable=True)
    equipment = Column(String(255), nullable=True)
    video_url = Column(String, nullable=True)
    
    user_maxes = relationship("UserMax", back_populates="exercise")


class Exercise(Base):
    __tablename__ = "exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sets = Column(Integer, nullable=False)  # Количество подходов
    volume = Column(Integer, nullable=False)  # Количество повторений в подходе
    weight = Column(Integer, nullable=True)   # Вес в кг
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False)
    exercise_definition_id = Column(Integer, ForeignKey("exercise_list.id"), nullable=True)
    
    workout = relationship("Workout", back_populates="exercises")
    exercise_definition = relationship("ExerciseList")
    
    @property
    def total_volume(self) -> int:
        """Вычисляет общий объем (сеты * повторения * вес).
        
        Returns:
            int: Общий объем упражнения. Если вес не указан, возвращает 0.
        """
        if self.weight is None:
            return 0
        return self.sets * self.volume * self.weight


class UserMax(Base):
    __tablename__ = "user_maxes"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercise_list.id"), nullable=False)
    max_weight = Column(Integer, nullable=False)
    rep_max = Column(Integer, nullable=False)
    
    exercise = relationship("ExerciseList", back_populates="user_maxes")
    progressions = relationship("Progressions", back_populates="user_max")
    progression_templates = relationship("ProgressionTemplate", back_populates="user_max")
    
    def __str__(self):
        return f"{self.exercise.name}: {self.max_weight}kg x {self.rep_max}"


class Progressions(Base):
    __tablename__ = "progressions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_max_id = Column(Integer, ForeignKey("user_maxes.id"), nullable=False)
    sets = Column(Integer, nullable=False)
    intensity = Column(Integer, nullable=False)
    effort = Column(Integer, nullable=False)
    volume = Column(Integer, nullable=False)
    
    # Relationship with UserMax (many-to-one, many progressions can belong to one user max)
    user_max = relationship("UserMax", back_populates="progressions")
    
    # Relationship with Workout (one-to-many, one progression can be used by many workouts)
    # Note: Using viewonly=True to avoid circular dependency issues
    # The actual relationship is managed by Workout.progression_template
    workouts = relationship(
        "Workout",
        foreign_keys="Workout.progression_template_id",
        back_populates="progression_template",
        viewonly=True
    )
    
    RPE_TABLE = {
        100: {10: 1},
        95: {10: 2, 9.5: "1-2", 9: 1},
        90: {10: 3, 9.5: "2-3", 9: 2, 8.5: "1-2", 8: 1},
        85: {10: 5, 9.5: "4-5", 9: 4, 8.5: "3-4", 8: 3, 7.5: "2-3", 7: 2},
        80: {10: 7, 9.5: "6-7", 9: 6, 8.5: "5-6", 8: 5, 7.5: "4-5", 7: 4, 6.5: "3-4", 6: 3},
        75: {10: 10, 9.5: "9-10", 9: 9, 8.5: "8-9", 8: 8, 7.5: "7-8", 7: 7, 6.5: "6-7", 6: 6},
        70: {10: "12+", 9.5: "11-12", 9: 11, 8.5: "10-11", 8: 10, 7.5: "9-10", 7: 9, 6.5: "8-9", 6: 8},
        65: {10: "15+", 9.5: "13-15", 9: "13-14", 8.5: "12-13", 8: 12, 7.5: "11-12", 7: 11, 6.5: "10-11", 6: 10},
        60: {10: "20+", 9.5: "18-20", 9: "17-18", 8.5: "16-17", 8: "15-16", 7.5: "14-15", 7: "13-14", 6.5: "12-13", 6: 12}
    }
    
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



class ProgressionTemplate(Base):
    __tablename__ = "progression_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    user_max_id = Column(Integer, ForeignKey("user_maxes.id"), nullable=False)
    sets = Column(Integer, nullable=False)
    intensity = Column(Integer, nullable=False)
    volume = Column(Integer, nullable=False)
    effort = Column(Integer, nullable=False)
    
    user_max = relationship("UserMax", back_populates="progression_templates")
    
    def get_volume(self) -> Union[int, str]:
        intensity_rounded = min(Progressions.RPE_TABLE.keys(), key=lambda x: abs(x - self.intensity))
        closest_effort = min(Progressions.RPE_TABLE[intensity_rounded].keys(), key=lambda x: abs(x - self.effort))
        return Progressions.RPE_TABLE[intensity_rounded].get(closest_effort, "N/A")
    
    def update_volume(self):
        if hasattr(self, 'volume') and self.volume is not None:
            return
            
        self.volume = self.get_volume()
        if isinstance(self.volume, str):
            self.volume = 0
