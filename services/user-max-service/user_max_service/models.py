from sqlalchemy import Column, Integer
from .database import Base


class UserMax(Base):
    __tablename__ = "user_maxes"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, nullable=False)
    max_weight = Column(Integer, nullable=False)
    rep_max = Column(Integer, nullable=False)
