from sqlalchemy import Column, Integer, String, Enum as SQLAlchemyEnum, ForeignKey, Date, Table, and_
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    ATHLETE = "athlete"
    TRAINER = "trainer"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.ATHLETE)

    
    athlete_profile = relationship("Athlete", uselist=False, back_populates="user", cascade="all, delete-orphan", primaryjoin="and_(User.id == Athlete.user_id)", foreign_keys="[Athlete.user_id]")
    trainer_profile = relationship("Trainer", uselist=False, back_populates="user", cascade="all, delete-orphan", primaryjoin="and_(User.id == Trainer.user_id)", foreign_keys="[Trainer.user_id]")

    
    assigned_trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True)
    assigned_trainer = relationship("Trainer", foreign_keys=[assigned_trainer_id], back_populates="assigned_athletes_relation")

    
    

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"

class Athlete(Base):
    __tablename__ = "athletes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    

    user = relationship("User", back_populates="athlete_profile")
    

    def __repr__(self):
        return f"<Athlete(id={self.id}, user_id={self.user_id})>"

class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    specialization = Column(String, nullable=True)
    

    user = relationship("User", back_populates="trainer_profile", primaryjoin="and_(Trainer.user_id == User.id)", foreign_keys="[Trainer.user_id]", uselist=False)
    
    
    assigned_athletes_relation = relationship(
    "User", 
    foreign_keys="[User.assigned_trainer_id]",
    back_populates="assigned_trainer"
)

    # TODO: Implement these relationships when corresponding models are created
    # created_exercise_templates = relationship("ExerciseTemplate", back_populates="creator_trainer")
    # created_progression_templates = relationship("ProgressionTemplate", back_populates="creator_trainer")
    # created_workout_templates = relationship("WorkoutTemplate", back_populates="creator_trainer")

    def __repr__(self):
        return f"<Trainer(id={self.id}, user_id={self.user_id})>"
