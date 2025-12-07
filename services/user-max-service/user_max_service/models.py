import datetime

from sqlalchemy import Column, Date, Float, Index, Integer, String

from .database import Base


class UserMax(Base):
    __tablename__ = "user_maxes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False)
    exercise_id = Column(Integer, nullable=False)
    exercise_name = Column(String(255))
    max_weight = Column(Integer, nullable=False)
    rep_max = Column(Integer)
    date = Column(Date, default=datetime.date.today, nullable=False)
    true_1rm = Column(Float)
    verified_1rm = Column(Float)
    source = Column(String(64))

    __table_args__ = (
        Index("idx_exercise_id", "exercise_id"),
        Index("ix_user_maxes_user_id", "user_id"),
        Index("ix_user_maxes_unique_entry", "user_id", "exercise_id", "rep_max", "date", unique=True),
    )

    def __str__(self):
        return f"UserMax(exercise_id={self.exercise_id}): {self.max_weight} kg ({self.rep_max} reps)"

    def __repr__(self):
        return f"<UserMax(id={self.id}, exercise_id={self.exercise_id}, max_weight={self.max_weight})>"

    class Config:
        from_attributes = True


class UserMaxDailyAgg(Base):
    __tablename__ = "user_max_daily_agg"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False)
    exercise_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    sum_true_1rm = Column(Float, nullable=False)
    cnt = Column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_user_max_daily_agg_user_ex", "user_id", "exercise_id"),
        Index(
            "ix_user_max_daily_agg_user_ex_date",
            "user_id",
            "exercise_id",
            "date",
            unique=True,
        ),
    )
