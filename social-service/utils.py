"""Utility functions for Social Service."""
from datetime import UTC, datetime
from uuid import NAMESPACE_DNS, UUID, uuid5


def parse_user_id(user_id_val: str | UUID) -> UUID:
    """Convert user ID string or UUID to UUID.

    If already a UUID, return it directly.
    If the string is a valid UUID, parse and return it.
    Otherwise (e.g. Firebase UID), deterministically derive a UUID5 from it.

    Args:
        user_id_val: User ID (UUID instance or string).

    Returns:
        UUID corresponding to the user.
    """
    if isinstance(user_id_val, UUID):
        return user_id_val

    try:
        return UUID(str(user_id_val))
    except (ValueError, AttributeError):
        return uuid5(NAMESPACE_DNS, f"firebase:{user_id_val}")


# Alias for backward compatibility
firebase_uid_to_uuid = parse_user_id


def utcnow() -> datetime:
    """Return timezone-naive UTC datetime for SQLAlchemy DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)
