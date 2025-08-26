from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON, String, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False, index=True)

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # active, completed, cancelled (future-proof)
    status = Column(String(50), nullable=False, default="active")

    # Derived at finish; seconds
    duration_seconds = Column(Integer, nullable=True)

    # Optional session metrics
    device_source = Column(String(100), nullable=True)
    hr_avg = Column(Integer, nullable=True)
    hr_max = Column(Integer, nullable=True)
    hydration_liters = Column(Float, nullable=True)
    mood = Column(String(50), nullable=True)
    injury_flags = Column(JSON, nullable=True)

    # Progress structure (flexible JSON). By convention:
    # {
    #   "completed": {"<instance_id>": [<set_id>, ...], ...}
    # }
    progress = Column(JSON, nullable=False, default=dict)

    workout = relationship("Workout", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<WorkoutSession(id={self.id}, workout_id={self.workout_id}, status={self.status})>"
