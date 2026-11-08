"""FastAPI dependencies for agent-service."""

from __future__ import annotations

from backend_common.dependencies import make_get_current_user_id

from .database import SessionLocal, engine, get_db

get_current_user_id = make_get_current_user_id("agent-service")

__all__ = ["SessionLocal", "engine", "get_current_user_id", "get_db"]
