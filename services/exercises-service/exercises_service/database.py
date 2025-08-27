import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback to a local SQLite database inside container volume
if not DATABASE_URL:
    os.makedirs("/app/data", exist_ok=True)
    DATABASE_URL = "sqlite:////app/data/exercises.db"

# For SQLite we need check_same_thread=False for use in FastAPI
engine_args = {"echo": False}
if DATABASE_URL.startswith("sqlite"):   # pragma: no cover
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
