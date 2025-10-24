from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import HTTPException, Request, status
from .config import settings

# Create database engine
engine = create_engine(settings.agent_database_url)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(request: Request) -> str:
    """Extract user ID from X-User-Id header (case-insensitive)."""
    user_id = request.headers.get("x-user-id")  # Case-insensitive by default
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="X-User-Id header required"
        )
    return user_id
