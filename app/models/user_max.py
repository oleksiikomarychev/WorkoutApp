from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from typing import Optional, List
from datetime import datetime

class UserMax(Base):
    __tablename__ = "user_maxes"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercise_list.id"), nullable=False)
    max_weight = Column(Integer, nullable=False)
    rep_max = Column(Integer, nullable=False)
    
    exercise_list = relationship("ExerciseList", back_populates="user_maxes")
    exercise_instances = relationship("ExerciseInstance", back_populates="user_max")
    applied_plans = relationship("AppliedCalendarPlan", back_populates="user_maxes", secondary="applied_calendar_plan_user_maxes")

    def __str__(self):
        return f"Max for {self.exercise_list.name}: {self.max_weight} kg ({self.rep_max} reps)"

    def __repr__(self):
        return f"<UserMax(id={self.id}, exercise_id={self.exercise_id}, max_weight={self.max_weight})>"

    class Config:
        from_attributes = True
