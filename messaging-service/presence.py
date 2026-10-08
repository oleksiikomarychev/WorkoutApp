"""Presence management using Redis."""
import json
from datetime import datetime
from uuid import UUID

import redis
from config import settings


def get_redis_client() -> redis.Redis:
    """Get Redis client instance.
    
    Returns:
        Redis client
    """
    return redis.from_url(settings.redis_url, decode_responses=True)


def set_user_presence(user_id: UUID, status: str = "online") -> bool:
    """Set user presence status in Redis with TTL.
    
    Args:
        user_id: User UUID
        status: Presence status (default: "online")
        
    Returns:
        True if successful
    """
    client = get_redis_client()
    key = f"presence:{user_id}"
    
    presence_data = {
        "status": status,
        "last_seen": datetime.utcnow().isoformat()
    }
    
    # Set presence with TTL from settings (90 seconds)
    client.setex(
        key,
        settings.presence_ttl,
        json.dumps(presence_data)
    )
    
    return True


def get_user_presence(user_id: UUID) -> dict[str, str] | None:
    """Get user presence status from Redis.
    
    Args:
        user_id: User UUID
        
    Returns:
        Presence data dict with status and last_seen, or None if not found
    """
    client = get_redis_client()
    key = f"presence:{user_id}"
    
    data = client.get(key)
    if not data:
        return None
    
    return json.loads(data)


def get_multiple_user_presence(user_ids: list[UUID]) -> dict[str, dict[str, str] | None]:
    """Get presence status for multiple users.
    
    Args:
        user_ids: List of user UUIDs
        
    Returns:
        Dict mapping user_id (as string) to presence data or None
    """
    if not user_ids:
        return {}
    
    client = get_redis_client()
    
    # Build keys for pipeline
    keys = [f"presence:{user_id}" for user_id in user_ids]
    
    # Use pipeline for efficient batch retrieval
    pipe = client.pipeline()
    for key in keys:
        pipe.get(key)
    
    results = pipe.execute()
    
    # Build result dict
    presence_map = {}
    for user_id, data in zip(user_ids, results):
        if data:
            presence_map[str(user_id)] = json.loads(data)
        else:
            presence_map[str(user_id)] = None
    
    return presence_map


def delete_user_presence(user_id: UUID) -> bool:
    """Delete user presence from Redis.
    
    Args:
        user_id: User UUID
        
    Returns:
        True if deleted, False if not found
    """
    client = get_redis_client()
    key = f"presence:{user_id}"
    
    result = client.delete(key)
    return result > 0


def update_user_presence_ttl(user_id: UUID) -> bool:
    """Update TTL for user presence (refresh heartbeat).
    
    Args:
        user_id: User UUID
        
    Returns:
        True if successful, False if key doesn't exist
    """
    client = get_redis_client()
    key = f"presence:{user_id}"
    
    # Check if key exists
    if not client.exists(key):
        # If key doesn't exist, create it
        return set_user_presence(user_id, "online")
    
    # Update last_seen timestamp
    presence_data = get_user_presence(user_id)
    if presence_data:
        presence_data["last_seen"] = datetime.utcnow().isoformat()
        client.setex(
            key,
            settings.presence_ttl,
            json.dumps(presence_data)
        )
        return True
    
    return False
