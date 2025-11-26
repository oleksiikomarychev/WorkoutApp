from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from .database import Base

# Define enum type
workout_type_enum = Enum("manual", "generated", name="workouttypeenum")


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)

    # Plan linkage and scheduling
    applied_plan_id = Column(Integer, nullable=True)
    microcycle_id = Column(Integer, nullable=True)
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
    # Add workout type classification
    workout_type = Column(workout_type_enum, nullable=False, default="manual")

    sessions = relationship(
        "WorkoutSession",
        back_populates="workout",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    exercises = relationship("WorkoutExercise", back_populates="workout", cascade="all, delete-orphan")

    def __repr__(self):
        return "<Workout(id=%s, name='%s', applied_plan_id=%s, order=%s)>" % (
            self.id,
            self.name,
            self.applied_plan_id,
            self.plan_order_index,
        )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    exercise_id = Column(Integer, nullable=False)

    workout = relationship("Workout", back_populates="exercises")
    sets = relationship("WorkoutSet", back_populates="exercise", cascade="all, delete-orphan")


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False)
    intensity = Column(Float, nullable=True)
    effort = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    working_weight = Column(Float, nullable=True)
    set_type = Column(String(32), nullable=True)

    exercise = relationship("WorkoutExercise", back_populates="sets")


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    # Derived at finish; seconds
    duration_seconds = Column(Integer, nullable=True)
    progress = Column(JSON, nullable=False, default=dict)
    # Persisted suggestion built on finish; used by client to prompt applying macros
    macro_suggestion = Column(JSON, nullable=True)

    workout = relationship("Workout", back_populates="sessions")

    def __repr__(self):
        return "<WorkoutSession(id=%s, workout_id=%s, status=%s)>" % (self.id, self.workout_id, self.status)


# Removed CalendarPlan model because it resides in the plans-service
