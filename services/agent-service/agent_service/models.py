from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class GeneratedPlan(Base):
    __tablename__ = "generated_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    plan_data = Column(JSON)  # Stores the entire TrainingPlan as JSON
