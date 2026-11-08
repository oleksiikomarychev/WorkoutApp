"""Database configuration and session management."""

from __future__ import annotations

from collections.abc import Generator

from config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Create SQLAlchemy engine
engine = create_engine(
    settings.effective_database_url,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=0,
    echo=False,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
