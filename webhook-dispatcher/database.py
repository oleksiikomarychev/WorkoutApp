"""Database connection management for Webhook Dispatcher."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base declarative class for models."""

    pass


def normalize_sync_database_url(url: str) -> str:
    """Ensure database URL uses psycopg2 driver for synchronous access."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return url


class DatabaseManager:
    """Manages database connections for both social and messaging services."""

    def __init__(self) -> None:
        """Initialize database engines and session factories."""
        social_url = normalize_sync_database_url(settings.social_database_url)
        messaging_url = normalize_sync_database_url(settings.messaging_database_url)

        # Create sync engines with connection pool health verification
        self.social_engine = create_engine(
            social_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
        )
        self.messaging_engine = create_engine(
            messaging_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
        )

        # Create session factories
        self.social_session_factory = sessionmaker(
            bind=self.social_engine,
            expire_on_commit=False,
            autoflush=False,
        )
        self.messaging_session_factory = sessionmaker(
            bind=self.messaging_engine,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info("Database connections initialized")

    def get_social_session(self) -> Session:
        """Get a session for social service database (caller must close)."""
        return self.social_session_factory()

    def get_messaging_session(self) -> Session:
        """Get a session for messaging service database (caller must close)."""
        return self.messaging_session_factory()

    @contextmanager
    def social_session(self) -> Generator[Session, None, None]:
        """Context manager for social service session."""
        session: Session = self.social_session_factory()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def messaging_session(self) -> Generator[Session, None, None]:
        """Context manager for messaging service session."""
        session: Session = self.messaging_session_factory()
        try:
            yield session
        finally:
            session.close()

    def close(self) -> None:
        """Close all database engines and dispose connections."""
        self.social_engine.dispose()
        self.messaging_engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()
