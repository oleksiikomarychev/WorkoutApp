"""Pytest fixtures and database setup for messaging service tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator

import pytest
from database import Base, get_db
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


# Enable SQLite to handle PostgreSQL JSONB columns during tests
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw) -> str:
    return "JSON"


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database engine with StaticPool."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create an in-memory SQLite database session for tests."""
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = test_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine) -> Generator[TestClient, None, None]:
    """Test client with database session dependency overridden."""
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    async def mock_async_task(*args, **kwargs):
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass

    async def mock_stop_publisher(*args, **kwargs):
        pass

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("main.start_publisher", mock_async_task)
        mp.setattr("main.stop_publisher", mock_stop_publisher)
        mp.setattr("main.heartbeat_monitor", mock_async_task)
        mp.setattr("redis_publisher.SessionLocal", test_session_local)
        mp.setattr("idempotency.SessionLocal", test_session_local)
        mp.setattr("database.SessionLocal", test_session_local)
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()
