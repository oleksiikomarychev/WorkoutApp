from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from ..database import Base


class ExerciseList(Base):
    __tablename__ = "exercise_list"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    muscle_group = Column(String(255), nullable=True)
    equipment = Column(String(255), nullable=True)
    target_muscles = Column(JSON, nullable=True)
    synergist_muscles = Column(JSON, nullable=True)
    # Classification fields
    # movement_type: 'compound' (multi-joint) or 'isolation'
    movement_type = Column(String(32), nullable=True)
    # region: 'upper' or 'lower'
    region = Column(String(32), nullable=True)

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
    workout_id = Column(
        Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False
    )
    exercise_list_id = Column(
        Integer, ForeignKey("exercise_list.id", ondelete="CASCADE"), nullable=False
    )
    user_max_id = Column(
        Integer, ForeignKey("user_maxes.id", ondelete="SET NULL"), nullable=True
    )
    sets = Column(JSON, nullable=False, default=list)
    # Optional metadata fields aligned with frontend
    notes = Column(Text, nullable=True)
    # 'order' is a reserved SQL word; set explicit column name for safety
    order = Column("order", Integer, nullable=True)

    exercise_definition = relationship("ExerciseList", back_populates="instances")
    workout = relationship("Workout", back_populates="exercise_instances")
    user_max = relationship(
        "UserMax", back_populates="exercise_instances", lazy="selectin"
    )

    def get_sets(self):
        """Получение сетов"""
        return self.sets

    def __repr__(self):
        return f"<ExerciseInstance(id={self.id}, exercise='{self.exercise_definition.name}')>"
