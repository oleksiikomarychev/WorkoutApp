"""Event schemas for Redis Streams.

This module defines the payload schemas for all events published to Redis Streams
from the Messaging Service. These events follow the outbox pattern and are published
by the redis_publisher background worker.

All events are published to Redis Streams with the following structure:
- stream_name: The Redis stream key (e.g., "app.messaging.message.created")
- event_type: The event type identifier
- payload: Event-specific data (defined below)
- Additional metadata: event_id, timestamp (added by publisher)

Event naming convention: app.{domain}.{entity}.{action}
"""

from datetime import datetime
from typing import Literal, TypedDict

# ============================================================================
# Message Events
# ============================================================================

class MessageCreatedPayload(TypedDict):
    """Payload for app.messaging.message.created event.
    
    Published when a new message is created in a channel.
    
    Stream: app.messaging.message.created
    Event Type: message.created
    
    Example:
        {
            "message_id": "550e8400-e29b-41d4-a716-446655440000",
            "channel_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "sender_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "content_preview": "Hey, how are you...",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    message_id: str  # UUID as string
    channel_id: str  # UUID as string
    sender_id: str  # UUID as string
    content_preview: str  # First 100 characters of content
    ts: str  # ISO 8601 timestamp


class MessageAcknowledgedPayload(TypedDict):
    """Payload for app.messaging.message.acknowledged event.
    
    Published when a message is acknowledged (delivered or read).
    
    Stream: app.messaging.message.acknowledged
    Event Type: message.acknowledged
    
    Example:
        {
            "message_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "status": "read",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    message_id: str  # UUID as string
    user_id: str  # UUID as string
    status: Literal["delivered", "read"]  # Acknowledgment status
    ts: str  # ISO 8601 timestamp


# ============================================================================
# Channel Events
# ============================================================================

class ChannelCreatedPayload(TypedDict):
    """Payload for app.messaging.channel.created event.
    
    Published when a new channel is created.
    
    Stream: app.messaging.channel.created
    Event Type: channel.created
    
    Example:
        {
            "channel_id": "550e8400-e29b-41d4-a716-446655440000",
            "type": "group",
            "members": ["6ba7b810-9dad-11d1-80b4-00c04fd430c8", "7ca8c920-aeae-22e2-91c5-11d15fe541d9"],
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    channel_id: str  # UUID as string
    type: Literal["direct", "group"]  # Channel type
    members: list[str]  # List of member UUIDs as strings
    ts: str  # ISO 8601 timestamp


class ChannelMemberAddedPayload(TypedDict):
    """Payload for app.messaging.channel.member_added event.
    
    Published when a member is added to a channel.
    
    Stream: app.messaging.channel.member_added
    Event Type: channel.member_added
    
    Example:
        {
            "channel_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "added_by": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    channel_id: str  # UUID as string
    user_id: str  # UUID as string - member being added
    added_by: str  # UUID as string - user who added the member
    ts: str  # ISO 8601 timestamp


# ============================================================================
# Presence Events
# ============================================================================

class PresenceUpdatedPayload(TypedDict):
    """Payload for app.messaging.presence.updated event.
    
    Published when a user's presence status changes.
    
    Stream: app.messaging.presence.updated
    Event Type: presence.updated
    
    Example:
        {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "online",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    user_id: str  # UUID as string
    status: Literal["online", "offline"]  # Presence status
    ts: str  # ISO 8601 timestamp


# ============================================================================
# Event Schema Registry
# ============================================================================

EVENT_SCHEMAS = {
    "app.messaging.message.created": {
        "event_type": "message.created",
        "description": "Published when a new message is created in a channel",
        "payload_type": MessageCreatedPayload,
        "example": {
            "message_id": "550e8400-e29b-41d4-a716-446655440000",
            "channel_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "sender_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "content_preview": "Hey, how are you...",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    },
    "app.messaging.message.acknowledged": {
        "event_type": "message.acknowledged",
        "description": "Published when a message is acknowledged (delivered or read)",
        "payload_type": MessageAcknowledgedPayload,
        "example": {
            "message_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "status": "read",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    },
    "app.messaging.channel.created": {
        "event_type": "channel.created",
        "description": "Published when a new channel is created",
        "payload_type": ChannelCreatedPayload,
        "example": {
            "channel_id": "550e8400-e29b-41d4-a716-446655440000",
            "type": "group",
            "members": ["6ba7b810-9dad-11d1-80b4-00c04fd430c8", "7ca8c920-aeae-22e2-91c5-11d15fe541d9"],
            "ts": "2025-11-07T10:30:00.123Z"
        }
    },
    "app.messaging.channel.member_added": {
        "event_type": "channel.member_added",
        "description": "Published when a member is added to a channel",
        "payload_type": ChannelMemberAddedPayload,
        "example": {
            "channel_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "added_by": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    },
    "app.messaging.presence.updated": {
        "event_type": "presence.updated",
        "description": "Published when a user's presence status changes",
        "payload_type": PresenceUpdatedPayload,
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "online",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    }
}


def get_event_schema(stream_name: str) -> dict | None:
    """Get event schema by stream name.
    
    Args:
        stream_name: Redis stream name (e.g., "app.messaging.message.created")
        
    Returns:
        Event schema dict or None if not found
    """
    return EVENT_SCHEMAS.get(stream_name)


def list_event_schemas() -> dict:
    """List all available event schemas.
    
    Returns:
        Dictionary of all event schemas
    """
    return EVENT_SCHEMAS.copy()


# ============================================================================
# Helper Functions for Event Creation
# ============================================================================

def create_message_created_payload(
    message_id: str,
    channel_id: str,
    sender_id: str,
    content: str,
    timestamp: datetime
) -> MessageCreatedPayload:
    """Create a message.created event payload.
    
    Args:
        message_id: Message UUID
        channel_id: Channel UUID
        sender_id: Sender UUID
        content: Full message content
        timestamp: Event timestamp
        
    Returns:
        MessageCreatedPayload dict
    """
    # Truncate content to 100 characters for preview
    content_preview = content[:100] + "..." if len(content) > 100 else content
    
    return {
        "message_id": message_id,
        "channel_id": channel_id,
        "sender_id": sender_id,
        "content_preview": content_preview,
        "ts": timestamp.isoformat()
    }


def create_message_acknowledged_payload(
    message_id: str,
    user_id: str,
    status: Literal["delivered", "read"],
    timestamp: datetime
) -> MessageAcknowledgedPayload:
    """Create a message.acknowledged event payload.
    
    Args:
        message_id: Message UUID
        user_id: User UUID
        status: Acknowledgment status (delivered or read)
        timestamp: Event timestamp
        
    Returns:
        MessageAcknowledgedPayload dict
    """
    return {
        "message_id": message_id,
        "user_id": user_id,
        "status": status,
        "ts": timestamp.isoformat()
    }


def create_channel_created_payload(
    channel_id: str,
    channel_type: Literal["direct", "group"],
    members: list[str],
    timestamp: datetime
) -> ChannelCreatedPayload:
    """Create a channel.created event payload.
    
    Args:
        channel_id: Channel UUID
        channel_type: Channel type (direct or group)
        members: List of member UUIDs
        timestamp: Event timestamp
        
    Returns:
        ChannelCreatedPayload dict
    """
    return {
        "channel_id": channel_id,
        "type": channel_type,
        "members": members,
        "ts": timestamp.isoformat()
    }


def create_channel_member_added_payload(
    channel_id: str,
    user_id: str,
    added_by: str,
    timestamp: datetime
) -> ChannelMemberAddedPayload:
    """Create a channel.member_added event payload.
    
    Args:
        channel_id: Channel UUID
        user_id: User UUID being added
        added_by: User UUID who added the member
        timestamp: Event timestamp
        
    Returns:
        ChannelMemberAddedPayload dict
    """
    return {
        "channel_id": channel_id,
        "user_id": user_id,
        "added_by": added_by,
        "ts": timestamp.isoformat()
    }


def create_presence_updated_payload(
    user_id: str,
    status: Literal["online", "offline"],
    timestamp: datetime
) -> PresenceUpdatedPayload:
    """Create a presence.updated event payload.
    
    Args:
        user_id: User UUID
        status: Presence status (online or offline)
        timestamp: Event timestamp
        
    Returns:
        PresenceUpdatedPayload dict
    """
    return {
        "user_id": user_id,
        "status": status,
        "ts": timestamp.isoformat()
    }
