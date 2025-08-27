from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from ..database import Base
from typing import Optional, List

class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # Link to applied plan (optional)
    applied_plan_id = Column(Integer, ForeignKey("applied_calendar_plans.id", ondelete="SET NULL"), nullable=True)
    # Order of the workout inside the applied plan
    plan_order_index = Column(Integer, nullable=True)
    # Scheduled date/time for this workout (used to determine "next")
    scheduled_for = Column(DateTime, nullable=True)
    # Completion timestamp (null -> not completed)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    rpe_session = Column(Float, nullable=True)
    location = Column(String(255), nullable=True)
    readiness_score = Column(Integer, nullable=True)
    
    exercise_instances = relationship(
        "ExerciseInstance", 
        back_populates="workout", 
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    # Sessions associated with this workout
    sessions = relationship(
        "WorkoutSession",
        back_populates="workout",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    # Relationship back to AppliedCalendarPlan
    applied_plan = relationship("AppliedCalendarPlan", back_populates="workouts")
    
    def __repr__(self):
        return f"<Workout(id={self.id}, name='{self.name}', applied_plan_id={self.applied_plan_id}, order={self.plan_order_index})>"
