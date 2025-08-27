from sqlalchemy import Column, Integer, String, DateTime, Float
from .database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Plan linkage and scheduling
    applied_plan_id = Column(Integer, nullable=True)
    plan_order_index = Column(Integer, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metadata
    notes = Column(String, nullable=True)
    status = Column(String(64), nullable=True)
    started_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    rpe_session = Column(Float, nullable=True)
    location = Column(String(255), nullable=True)
    readiness_score = Column(Integer, nullable=True)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, index=True, nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="active")
