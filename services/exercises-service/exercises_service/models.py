from sqlalchemy import Column, Integer, String, JSON, Text
from sqlalchemy.orm import relationship
from .database import Base


class ExerciseList(Base):
    __tablename__ = "exercise_list"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    muscle_group = Column(String(255), nullable=True)
    equipment = Column(String(255), nullable=True)
    target_muscles = Column(JSON, nullable=True)
    synergist_muscles = Column(JSON, nullable=True)
    movement_type = Column(String(32), nullable=True)
    region = Column(String(32), nullable=True)


class ExerciseInstance(Base):
    __tablename__ = "exercise_instances"

    id = Column(Integer, primary_key=True, index=True)
    # Keep linkage fields as plain integers to avoid cross-service FK constraints
    workout_id = Column(Integer, nullable=False)
    exercise_list_id = Column(Integer, nullable=False)
    user_max_id = Column(Integer, nullable=True)
    sets = Column(JSON, nullable=False, default=list)
    notes = Column(Text, nullable=True)
    order = Column("order", Integer, nullable=True)
