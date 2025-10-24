from sqlalchemy import Column, Integer, Date, Float, String, Index
from sqlalchemy.orm import relationship
import datetime
from .database import Base


class UserMax(Base):
    __tablename__ = "user_maxes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False)
    exercise_id = Column(Integer, nullable=False)
    exercise_name = Column(String(255))  # New field
    max_weight = Column(Integer, nullable=False)
    rep_max = Column(Integer)
    date = Column(Date, default=datetime.date.today, nullable=False)
    true_1rm = Column(Float) #Теоретический максимум
    verified_1rm = Column(Float) #Подтвержденный максимум

    # exercise_instances = relationship("ExerciseInstance", back_populates="user_max")
    # applied_plans = relationship("AppliedCalendarPlan", back_populates="user_maxes", secondary="applied_calendar_plan_user_maxes")

    __table_args__ = (
        Index('idx_exercise_id', 'exercise_id'),
        Index('ix_user_maxes_user_id', 'user_id'),
        Index('ix_user_maxes_unique_entry', 'user_id', 'exercise_id', 'rep_max', 'date', unique=True),
    )

    def __str__(self):
        return f"UserMax(exercise_id={self.exercise_id}): {self.max_weight} kg ({self.rep_max} reps)"

    def __repr__(self):
        return f"<UserMax(id={self.id}, exercise_id={self.exercise_id}, max_weight={self.max_weight})>"

    class Config:
        from_attributes = True
