from sqlalchemy import Column, Integer, String, JSON, DateTime, Index, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class GeneratedPlan(Base):
    __tablename__ = "generated_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    plan_data = Column(JSON)  # Stores the entire TrainingPlan as JSON
    
    __table_args__ = (
        Index('ix_generated_plans_user_id', 'user_id'),
    )


class Avatar(Base):
    __tablename__ = "user_avatars"

    user_id = Column(String(255), primary_key=True, index=True)
    content_type = Column(String(64), default="image/png", nullable=False)
    image = Column(LargeBinary, nullable=False)  # PNG bytes
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
