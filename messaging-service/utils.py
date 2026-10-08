from uuid import NAMESPACE_DNS, UUID, uuid5


def firebase_uid_to_uuid(firebase_uid: str) -> UUID:
    """Convert Firebase UID to deterministic UUID using UUID5.
    
    Args:
        firebase_uid: Firebase user ID (string)
        
    Returns:
        UUID generated from Firebase UID
    """
    return uuid5(NAMESPACE_DNS, f"firebase:{firebase_uid}")
