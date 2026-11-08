"""Database engine and session management for agent-service."""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings

logger = structlog.get_logger(__name__)

is_in_docker = bool(os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv"))
is_testing = bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TESTING"))

if is_testing:
    DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
else:
    raw_url = settings.AGENT_DATABASE_URL or os.getenv("DATABASE_URL") or "sqlite:///:memory:"
    DATABASE_URL = raw_url

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # Route host.docker.internal vs localhost depending on runtime environment
    if is_in_docker and "localhost" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("localhost", "host.docker.internal")
    elif not is_in_docker and "host.docker.internal" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("host.docker.internal", "localhost")

engine_args: dict[str, Any] = {"echo": False}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
    if ":memory:" in DATABASE_URL:
        engine_args["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models in agent-service."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and safely close it on completion."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
