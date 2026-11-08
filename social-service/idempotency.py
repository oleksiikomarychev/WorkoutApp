"""Idempotency middleware and utilities."""
from collections.abc import Callable
import json
from datetime import timedelta
from typing import Any

import database
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from models import IdempotencyKey
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from utils import parse_user_id, utcnow


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle idempotency for POST requests."""

    IDEMPOTENT_METHODS = {"POST"}
    IDEMPOTENCY_HEADER = "Idempotency-Key"
    TTL_HOURS = 24

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        """Process request with idempotency check."""
        # Only process POST requests with Idempotency-Key header
        if request.method not in self.IDEMPOTENT_METHODS:
            return await call_next(request)

        idempotency_key = request.headers.get(self.IDEMPOTENCY_HEADER)
        if not idempotency_key:
            return await call_next(request)

        # Extract user_id from X-User-Id header (set by Gateway)
        user_id_raw = request.headers.get("X-User-Id")
        if not user_id_raw:
            return await call_next(request)

        user_uuid = parse_user_id(user_id_raw)

        # Check if this idempotency key exists
        db = database.SessionLocal()
        try:
            existing = db.query(IdempotencyKey).filter(
                IdempotencyKey.key == idempotency_key
            ).first()

            if existing:
                endpoint = str(request.url.path)
                if existing.user_id != user_uuid or existing.endpoint != endpoint:
                    # Conflict: same key used for different operation
                    return JSONResponse(
                        status_code=409,
                        content={
                            "error": {
                                "code": "IDEMPOTENCY_KEY_CONFLICT",
                                "message": "Idempotency key already used for a different operation",
                                "details": {
                                    "key": idempotency_key,
                                    "original_endpoint": existing.endpoint,
                                    "original_user": str(existing.user_id),
                                },
                            }
                        },
                    )

                # Return cached response
                return JSONResponse(
                    status_code=existing.response_status,
                    content=existing.response_body,
                )

            # Process the request
            response = await call_next(request)

            # Cache the response if it's a successful creation (2xx status)
            if 200 <= response.status_code < 300:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                try:
                    response_data = json.loads(response_body.decode())
                except Exception:
                    response_data = {}

                # Store idempotency record
                idempotency_record = IdempotencyKey(
                    key=idempotency_key,
                    service="social-service",
                    endpoint=str(request.url.path),
                    user_id=user_uuid,
                    response_status=response.status_code,
                    response_body=response_data,
                    created_at=utcnow(),
                )
                db.add(idempotency_record)
                db.commit()

                # Return new response with the body
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            return response

        finally:
            db.close()


def cleanup_expired_idempotency_keys(db: Session, hours: int = 24) -> int:
    """Clean up idempotency keys older than TTL.

    Args:
        db: Database session.
        hours: TTL in hours.

    Returns:
        Number of deleted records.
    """
    cutoff_time = utcnow() - timedelta(hours=hours)
    deleted = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.created_at < cutoff_time)
        .delete()
    )
    db.commit()
    return deleted


def get_idempotency_record(db: Session, key: str) -> IdempotencyKey | None:
    """Get idempotency record by key.

    Args:
        db: Database session.
        key: Idempotency key.

    Returns:
        IdempotencyKey record or None.
    """
    return db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
