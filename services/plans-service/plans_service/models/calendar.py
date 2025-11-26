from datetime import datetime, timedelta

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CalendarPlan(Base):
    __tablename__ = "calendar_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, server_default=text("true"))
    user_id = Column(String(255), nullable=False, index=True)
    root_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    # Plan metadata
    notes = Column(String(512), nullable=True)
    primary_goal = Column(String(32), nullable=True)
    intended_experience_level = Column(String(32), nullable=True)
    intended_frequency_per_week = Column(Integer, nullable=True)
    session_duration_target_min = Column(Integer, nullable=True)
    primary_focus_lifts = Column(JSON, nullable=True)  # e.g. list of exercise_definition_ids
    required_equipment = Column(JSON, nullable=True)  # e.g. list of strings

    applied_instances = relationship(
        "AppliedCalendarPlan", back_populates="calendar_plan", cascade="all, delete-orphan"
    )
    mesocycles = relationship(
        "Mesocycle",
        back_populates="calendar_plan",
        cascade="all, delete-orphan",
        order_by="Mesocycle.order_index",
        lazy="selectin",
    )
    root_plan = relationship("CalendarPlan", remote_side=[id], back_populates="variants", uselist=False)
    variants = relationship("CalendarPlan", back_populates="root_plan", cascade="all, delete-orphan")
    # New: macros attached to this plan
    macros = relationship("PlanMacro", back_populates="calendar_plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CalendarPlan(id={self.id}, name='{self.name}')>"

    class Config:
        from_attributes = True


class AppliedCalendarPlan(Base):
    __tablename__ = "applied_calendar_plans"

    id = Column(Integer, primary_key=True, index=True)
    calendar_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    user_max_ids = Column(JSON, nullable=True)
    current_workout_index = Column(Integer, default=0)
    user_id = Column(String(255), nullable=False, index=True)
    # User plan progress metadata (USER_PLANS core)
    status = Column(String(32), nullable=True)  # active/completed/dropped/etc.
    planned_sessions_total = Column(Integer, nullable=True)
    actual_sessions_completed = Column(Integer, nullable=True)
    adherence_pct = Column(Float, nullable=True)
    notes = Column(String(512), nullable=True)
    # Dropout analytics
    dropout_reason = Column(String(64), nullable=True)  # e.g. injury/no_time/too_hard/not_enjoyable
    dropped_at = Column(DateTime, nullable=True)

    calendar_plan = relationship("CalendarPlan", back_populates="applied_instances")
    workouts = relationship(
        "AppliedPlanWorkout",
        back_populates="applied_plan",
        order_by="AppliedPlanWorkout.order_index",
        cascade="all, delete-orphan",
    )
    mesocycles = relationship("AppliedMesocycle", back_populates="applied_plan", cascade="all, delete-orphan")

    def calculate_end_date(self, duration_weeks: int) -> None:
        if duration_weeks:
            self.end_date = self.start_date + timedelta(weeks=duration_weeks)

    def __repr__(self):
        return (
            "<AppliedCalendarPlan("
            f"id={self.id}, calendar_plan_id={self.calendar_plan_id}, "
            f"start_date={self.start_date}, end_date={self.end_date})>"
        )


class AppliedPlanWorkout(Base):
    __tablename__ = "applied_plan_workouts"

    id = Column(Integer, primary_key=True, index=True)
    applied_plan_id = Column(Integer, ForeignKey("applied_calendar_plans.id"), nullable=False)
    workout_id = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False)

    applied_plan = relationship("AppliedCalendarPlan", back_populates="workouts")

    def __repr__(self):
        return f"<AppliedPlanWorkout(id={self.id}, workout_id={self.workout_id}, order={self.order_index})>"


class AppliedMesocycle(Base):
    __tablename__ = "applied_mesocycles"

    id = Column(Integer, primary_key=True, index=True)
    applied_plan_id = Column(Integer, ForeignKey("applied_calendar_plans.id"), nullable=False)
    mesocycle_id = Column(Integer, ForeignKey("mesocycles.id"), nullable=True)
    order_index = Column(Integer, nullable=False)

    applied_plan = relationship("AppliedCalendarPlan", back_populates="mesocycles")
    microcycles = relationship("AppliedMicrocycle", back_populates="applied_mesocycle", cascade="all, delete-orphan")


class AppliedMicrocycle(Base):
    __tablename__ = "applied_microcycles"

    id = Column(Integer, primary_key=True, index=True)
    applied_mesocycle_id = Column(Integer, ForeignKey("applied_mesocycles.id"), nullable=False)
    microcycle_id = Column(Integer, ForeignKey("microcycles.id"), nullable=True)
    order_index = Column(Integer, nullable=False)

    applied_mesocycle = relationship("AppliedMesocycle", back_populates="microcycles")
    workouts = relationship("AppliedWorkout", back_populates="applied_microcycle", cascade="all, delete-orphan")


class AppliedWorkout(Base):
    __tablename__ = "applied_workouts"

    id = Column(Integer, primary_key=True, index=True)
    applied_microcycle_id = Column(Integer, ForeignKey("applied_microcycles.id"), nullable=False)
    workout_id = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False)

    applied_microcycle = relationship("AppliedMicrocycle", back_populates="workouts")


class Mesocycle(Base):
    __tablename__ = "mesocycles"

    id = Column(Integer, primary_key=True, index=True)
    calendar_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    notes = Column(String(100), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    weeks_count = Column(Integer, nullable=True)
    microcycle_length_days = Column(Integer, nullable=True)
    duration_weeks = Column(Integer, nullable=False)

    calendar_plan = relationship("CalendarPlan", back_populates="mesocycles")
    microcycles = relationship(
        "Microcycle",
        back_populates="mesocycle",
        cascade="all, delete-orphan",
        order_by="Microcycle.order_index",
    )

    def __repr__(self):
        return (
            f"<Mesocycle(id={self.id}, plan_id={self.calendar_plan_id}, name='{self.name}', order={self.order_index})>"
        )


class Microcycle(Base):
    __tablename__ = "microcycles"

    id = Column(Integer, primary_key=True, index=True)
    mesocycle_id = Column(Integer, ForeignKey("mesocycles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    notes = Column(String(100), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    normalization_value = Column(Float, nullable=True)
    normalization_unit = Column(String(16), nullable=True)
    normalization_rules = Column(JSON, nullable=True)
    days_count = Column(Integer, nullable=True)

    mesocycle = relationship("Mesocycle", back_populates="microcycles")
    plan_workouts = relationship(
        "PlanWorkout",
        back_populates="microcycle",
        cascade="all, delete-orphan",
        order_by="PlanWorkout.order_index",
    )

    def __repr__(self):
        return (
            "<Microcycle("
            f"id={self.id}, mesocycle_id={self.mesocycle_id}, "
            f"name='{self.name}', order={self.order_index})>"
        )


class PlanWorkout(Base):
    __tablename__ = "plan_workouts"

    id = Column(Integer, primary_key=True, index=True)
    microcycle_id = Column(Integer, ForeignKey("microcycles.id", ondelete="CASCADE"), nullable=False)
    day_label = Column(String(50), nullable=False)  # e.g., "Day 1"
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    microcycle = relationship("Microcycle", back_populates="plan_workouts")
    exercises = relationship("PlanExercise", back_populates="plan_workout", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PlanWorkout(id={self.id}, microcycle_id={self.microcycle_id}, day_label='{self.day_label}')>"


class PlanExercise(Base):
    __tablename__ = "plan_exercises"

    id = Column(Integer, primary_key=True, index=True)
    plan_workout_id = Column(Integer, ForeignKey("plan_workouts.id", ondelete="CASCADE"), nullable=False)
    exercise_definition_id = Column(Integer, nullable=False)
    exercise_name = Column(String(255), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plan_workout = relationship("PlanWorkout", back_populates="exercises")
    sets = relationship("PlanSet", back_populates="plan_exercise", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            "<PlanExercise("
            f"id={self.id}, plan_workout_id={self.plan_workout_id}, "
            f"exercise_definition_id={self.exercise_definition_id}, "
            f"exercise_name='{self.exercise_name}')>"
        )


class PlanSet(Base):
    __tablename__ = "plan_sets"

    id = Column(Integer, primary_key=True, index=True)
    plan_exercise_id = Column(Integer, ForeignKey("plan_exercises.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    intensity = Column(Integer, nullable=True)  # 0-110
    effort = Column(Integer, nullable=True)  # 1-10
    volume = Column(Integer, nullable=True)  # >=1
    working_weight = Column(Float, nullable=True)  # For calculations, exclude in responses if needed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    plan_exercise = relationship("PlanExercise", back_populates="sets")

    def __repr__(self):
        return f"<PlanSet(id={self.id}, plan_exercise_id={self.plan_exercise_id}, intensity={self.intensity})>"


class WorkoutProgress(Base):  # Сопоставление с воркаут сервисом(на будущее)
    __tablename__ = "workout_progress"

    id = Column(Integer, primary_key=True, index=True)
    plan_exercise_id = Column(Integer, ForeignKey("plan_exercises.id"), nullable=True)
    workout_set_id = Column(Integer, nullable=False)  # From workouts-service WorkoutSet.id
    planned_intensity = Column(Integer, nullable=True)
    actual_intensity = Column(Float, nullable=True)
    planned_effort = Column(Integer, nullable=True)
    actual_effort = Column(Float, nullable=True)
    planned_volume = Column(Integer, nullable=True)
    actual_volume = Column(Integer, nullable=True)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Optional relationships (if needed)
    plan_exercise = relationship("PlanExercise")

    def __repr__(self):
        return f"<WorkoutProgress(id={self.id}, date={self.date})>"
