import datetime

from sqlalchemy import Date, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class UserMax(Base):
    __tablename__ = "user_maxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    exercise_id: Mapped[int] = mapped_column(Integer, nullable=False)
    exercise_name: Mapped[str | None] = mapped_column(String(255))
    max_weight: Mapped[int] = mapped_column(Integer, nullable=False)
    rep_max: Mapped[int | None] = mapped_column(Integer)
    date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today, nullable=False)
    true_1rm: Mapped[float | None] = mapped_column(Float)
    verified_1rm: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("idx_exercise_id", "exercise_id"),
        Index("ix_user_maxes_user_id", "user_id"),
        Index("ix_user_maxes_unique_entry", "user_id", "exercise_id", "rep_max", "date", unique=True),
        Index("idx_user_exercise_date", "user_id", "exercise_id", "date"),
    )

    def __str__(self):
        return f"UserMax(exercise_id={self.exercise_id}): {self.max_weight} kg ({self.rep_max} reps)"

    def __repr__(self):
        return f"<UserMax(id={self.id}, exercise_id={self.exercise_id}, max_weight={self.max_weight})>"

    class Config:
        from_attributes = True


class UserMaxDailyAgg(Base):
    __tablename__ = "user_max_daily_agg"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    exercise_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    sum_true_1rm: Mapped[float] = mapped_column(Float, nullable=False)
    cnt: Mapped[int] = mapped_column(Integer, nullable=False)

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
