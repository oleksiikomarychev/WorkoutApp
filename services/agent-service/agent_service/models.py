from sqlalchemy import Column, Integer, String, JSON, DateTime, Index
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
