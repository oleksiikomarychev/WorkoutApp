"""Database configuration and session management."""
from collections.abc import Generator

from config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = settings.effective_database_url

engine_args: dict[str, object] = {
    "echo": False,
}

if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
    if ":memory:" in DATABASE_URL:
        engine_args["poolclass"] = StaticPool
else:
    engine_args["pool_pre_ping"] = True
    engine_args["pool_size"] = 20
    engine_args["max_overflow"] = 0

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, **engine_args)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create Base class for models using SQLAlchemy 2.0 DeclarativeBase
class Base(DeclarativeBase):
    """Base declarative model."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
