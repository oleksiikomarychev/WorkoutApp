from __future__ import annotations

from uuid import NAMESPACE_DNS, UUID, uuid5


def firebase_uid_to_uuid(firebase_uid: str | UUID) -> UUID:
    """Convert Firebase UID or existing UUID to deterministic UUID using UUID5.

    If already a valid UUID instance or standard UUID hex string, returns it directly.
    Otherwise hashes the Firebase UID string into a deterministic UUID5.

    Args:
        firebase_uid: Firebase user ID or UUID.

    Returns:
        Deterministic UUID.
    """
    if isinstance(firebase_uid, UUID):
        return firebase_uid
    try:
        return UUID(str(firebase_uid))
    except (ValueError, AttributeError):
        return uuid5(NAMESPACE_DNS, f"firebase:{firebase_uid}")
