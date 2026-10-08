"""Database connection management for Webhook Dispatcher."""
import logging

from config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class DatabaseManager:
    """Manages database connections for both social and messaging services."""
    
    def __init__(self):
        """Initialize database engines."""
        # Convert postgresql:// to postgresql+psycopg2:// for sync connections
        social_url = settings.social_database_url.replace("postgresql://", "postgresql+psycopg2://")
        messaging_url = settings.messaging_database_url.replace("postgresql://", "postgresql+psycopg2://")
        
        # Create sync engines for reading webhook subscriptions
        self.social_engine = create_engine(social_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        self.messaging_engine = create_engine(messaging_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        
        # Create session factories
        self.social_session_factory = sessionmaker(bind=self.social_engine, expire_on_commit=False)
        self.messaging_session_factory = sessionmaker(bind=self.messaging_engine, expire_on_commit=False)
        
        logger.info("Database connections initialized")
    
    def get_social_session(self):
        """Get a session for social service database."""
        return self.social_session_factory()
    
    def get_messaging_session(self):
        """Get a session for messaging service database."""
        return self.messaging_session_factory()
    
    def close(self):
        """Close all database connections."""
        self.social_engine.dispose()
        self.messaging_engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()
