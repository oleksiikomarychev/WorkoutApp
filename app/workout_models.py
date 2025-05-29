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
    
    progression_template = relationship("Progressions", back_populates="workouts")
    exercises = relationship("Exercise", back_populates="workout")


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
    sets = Column(Integer, nullable=False)
    volume = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False)
    
    workout = relationship("Workout", back_populates="exercises")


class UserMax(Base):
    __tablename__ = "user_maxes"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercise_list.id"), nullable=False)
    max_weight = Column(Integer, nullable=False)
    rep_max = Column(Integer, nullable=False)
    
    exercise = relationship("ExerciseList", back_populates="user_maxes")
    progressions = relationship("Progressions", back_populates="user_max")
    llm_progressions = relationship("LLMProgression", back_populates="user_max")
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
    
    user_max = relationship("UserMax", back_populates="progressions")
    workouts = relationship("Workout", back_populates="progression_template")
    
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
    
    def update_volume(self):
        """"""
        if hasattr(self, 'volume') and self.volume is not None:
            return
            
        self.volume = self.get_volume()
        if isinstance(self.volume, str):
            self.volume = 0


class LLMProgression(Base):
    """"""
    __tablename__ = "llm_progressions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_max_id = Column(Integer, ForeignKey("user_maxes.id"), nullable=False)
    sets = Column(Integer, nullable=True, default=0)
    intensity = Column(Integer, nullable=True, default=0)
    effort = Column(Integer, nullable=True, default=0)
    volume = Column(Integer, nullable=True, default=0)
    user_data = Column(JSON, nullable=True, default=dict)
    
    user_max = relationship("UserMax", back_populates="llm_progressions")
    
    def get_volume(self) -> Union[int, str]:
        """"""
        if self.intensity is None or self.effort is None:
            return "N/A"
        
        try:
            intensity_rounded = min(
                Progressions.RPE_TABLE.keys(), 
                key=lambda x: abs(x - self.intensity)
            )
            closest_effort = min(
                Progressions.RPE_TABLE[intensity_rounded].keys(), 
                key=lambda x: abs(x - self.effort)
            )
            return Progressions.RPE_TABLE[intensity_rounded].get(closest_effort, "N/A")
        except (TypeError, ValueError):
            return "N/A"

    def get_calculated_weight(self) -> Optional[int]:
        """"""
        if not self.user_max or not self.user_max.max_weight or self.intensity is None:
            return None
        try:
            return round(self.user_max.max_weight * (self.intensity / 100.0))
        except (TypeError, ValueError):
            return None
    
    def update_volume(self):
        if hasattr(self, 'volume') and self.volume is not None:
            return
            
        self.volume = self.get_volume()
        if isinstance(self.volume, str):
            self.volume = 0
    
    def store_user_data(self, data: Dict[str, Any]):
        self.user_data = data


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
