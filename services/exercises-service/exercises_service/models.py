from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
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
    category = Column(String(64), nullable=True)
    movement_pattern = Column(String(64), nullable=True)
    is_competition_lift = Column(Integer, nullable=True)

    instances = relationship(
        "ExerciseInstance",
        back_populates="exercise_definition",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ExerciseList(id={self.id}, name='{self.name}')>"


class ExerciseInstance(Base):
    __tablename__ = "exercise_instances"

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, nullable=False)
    exercise_list_id = Column(Integer, ForeignKey("exercise_list.id"), nullable=False)
    user_max_id = Column(Integer, nullable=True)
    user_id = Column(String(255), nullable=False)
    sets = Column(JSON, nullable=False, default=list)
    notes = Column(Text, nullable=True)
    order = Column("order", Integer, nullable=True)

    exercise_definition = relationship("ExerciseList", back_populates="instances")

    def get_sets(self):
        return self.sets

    def __repr__(self):
        return f"<ExerciseInstance(id={self.id}, exercise='{self.exercise_definition.name}')>"
