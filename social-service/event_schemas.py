"""Event schemas for Redis Streams.

This module defines the payload schemas for all events published to Redis Streams
from the Social Service. These events follow the outbox pattern and are published
by the redis_publisher background worker.

All events are published to Redis Streams with the following structure:
- stream_name: The Redis stream key (e.g., "app.social.post.created")
- event_type: The event type identifier
- payload: Event-specific data (defined below)
- Additional metadata: event_id, timestamp (added by publisher)

Event naming convention: app.{domain}.{entity}.{action}
"""

from datetime import datetime
from typing import Literal, TypedDict

# ============================================================================
# Post Events
# ============================================================================

class PostCreatedPayload(TypedDict):
    """Payload for app.social.post.created event.
    
    Published when a new post is created.
    
    Stream: app.social.post.created
    Event Type: post.created
    
    Example:
        {
            "post_id": "550e8400-e29b-41d4-a716-446655440000",
            "author_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "scope": "public",
            "content_preview": "This is a great workout...",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    post_id: str  # UUID as string
    author_id: str  # UUID as string
    scope: Literal["public", "followers", "private", "coach_only"]
    content_preview: str  # First 200 characters of content
    ts: str  # ISO 8601 timestamp


# ============================================================================
# Comment Events
# ============================================================================

class CommentCreatedPayload(TypedDict):
    """Payload for app.social.comment.created event.
    
    Published when a new comment is created on a post.
    
    Stream: app.social.comment.created
    Event Type: comment.created
    
    Example:
        {
            "comment_id": "550e8400-e29b-41d4-a716-446655440000",
            "post_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "author_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    comment_id: str  # UUID as string
    post_id: str  # UUID as string
    author_id: str  # UUID as string
    ts: str  # ISO 8601 timestamp


# ============================================================================
# Reaction Events
# ============================================================================

class ReactionToggledPayload(TypedDict):
    """Payload for app.social.reaction.toggled event.
    
    Published when a reaction is added or removed (toggled).
    
    Stream: app.social.reaction.toggled
    Event Type: reaction.toggled
    
    Example (creation):
        {
            "reaction_id": "550e8400-e29b-41d4-a716-446655440000",
            "post_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "user_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "type": "like",
            "action": "created",
            "ts": "2025-11-07T10:30:00.123Z"
        }
        
    Example (deletion):
        {
            "reaction_id": "550e8400-e29b-41d4-a716-446655440000",
            "post_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "user_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "type": "like",
            "action": "deleted",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    reaction_id: str  # UUID as string
    post_id: str | None  # UUID as string (null if reaction is on comment)
    comment_id: str | None  # UUID as string (null if reaction is on post)
    user_id: str  # UUID as string
    type: str  # Reaction type (like, love, fire, etc.)
    action: Literal["created", "deleted"]  # Whether reaction was added or removed
    ts: str  # ISO 8601 timestamp


# ============================================================================
# Follow Events
# ============================================================================

class FollowChangedPayload(TypedDict):
    """Payload for app.social.follow.changed event.
    
    Published when a user follows or unfollows another user.
    
    Stream: app.social.follow.changed
    Event Type: follow.changed
    
    Example (follow):
        {
            "follower_id": "550e8400-e29b-41d4-a716-446655440000",
            "followee_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "action": "followed",
            "ts": "2025-11-07T10:30:00.123Z"
        }
        
    Example (unfollow):
        {
            "follower_id": "550e8400-e29b-41d4-a716-446655440000",
            "followee_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "action": "unfollowed",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    """
    follower_id: str  # UUID as string - user who is following
    followee_id: str  # UUID as string - user being followed
    action: Literal["followed", "unfollowed"]  # Follow or unfollow action
    ts: str  # ISO 8601 timestamp


# ============================================================================
# Event Schema Registry
# ============================================================================

EVENT_SCHEMAS = {
    "app.social.post.created": {
        "event_type": "post.created",
        "description": "Published when a new post is created",
        "payload_type": PostCreatedPayload,
        "example": {
            "post_id": "550e8400-e29b-41d4-a716-446655440000",
            "author_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "scope": "public",
            "content_preview": "This is a great workout...",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    },
    "app.social.comment.created": {
        "event_type": "comment.created",
        "description": "Published when a new comment is created on a post",
        "payload_type": CommentCreatedPayload,
        "example": {
            "comment_id": "550e8400-e29b-41d4-a716-446655440000",
            "post_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "author_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    },
    "app.social.reaction.toggled": {
        "event_type": "reaction.toggled",
        "description": "Published when a reaction is added or removed",
        "payload_type": ReactionToggledPayload,
        "example": {
            "reaction_id": "550e8400-e29b-41d4-a716-446655440000",
            "post_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "comment_id": None,
            "user_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9",
            "type": "like",
            "action": "created",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    },
    "app.social.follow.changed": {
        "event_type": "follow.changed",
        "description": "Published when a user follows or unfollows another user",
        "payload_type": FollowChangedPayload,
        "example": {
            "follower_id": "550e8400-e29b-41d4-a716-446655440000",
            "followee_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "action": "followed",
            "ts": "2025-11-07T10:30:00.123Z"
        }
    }
}


def get_event_schema(stream_name: str) -> dict | None:
    """Get event schema by stream name.
    
    Args:
        stream_name: Redis stream name (e.g., "app.social.post.created")
        
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

def create_post_created_payload(
    post_id: str,
    author_id: str,
    scope: str,
    content: str,
    timestamp: datetime
) -> PostCreatedPayload:
    """Create a post.created event payload.
    
    Args:
        post_id: Post UUID
        author_id: Author UUID
        scope: Post scope (public, followers, private, coach_only)
        content: Full post content
        timestamp: Event timestamp
        
    Returns:
        PostCreatedPayload dict
    """
    # Truncate content to 200 characters for preview
    content_preview = content[:200] + "..." if len(content) > 200 else content
    
    return {
        "post_id": post_id,
        "author_id": author_id,
        "scope": scope,
        "content_preview": content_preview,
        "ts": timestamp.isoformat()
    }


def create_comment_created_payload(
    comment_id: str,
    post_id: str,
    author_id: str,
    timestamp: datetime
) -> CommentCreatedPayload:
    """Create a comment.created event payload.
    
    Args:
        comment_id: Comment UUID
        post_id: Post UUID
        author_id: Author UUID
        timestamp: Event timestamp
        
    Returns:
        CommentCreatedPayload dict
    """
    return {
        "comment_id": comment_id,
        "post_id": post_id,
        "author_id": author_id,
        "ts": timestamp.isoformat()
    }


def create_reaction_toggled_payload(
    reaction_id: str,
    user_id: str,
    reaction_type: str,
    action: Literal["created", "deleted"],
    timestamp: datetime,
    post_id: str | None = None,
    comment_id: str | None = None
) -> ReactionToggledPayload:
    """Create a reaction.toggled event payload.
    
    Args:
        reaction_id: Reaction UUID
        user_id: User UUID
        reaction_type: Type of reaction (like, love, fire, etc.)
        action: Whether reaction was created or deleted
        timestamp: Event timestamp
        post_id: Post UUID (if reaction is on post)
        comment_id: Comment UUID (if reaction is on comment)
        
    Returns:
        ReactionToggledPayload dict
    """
    return {
        "reaction_id": reaction_id,
        "post_id": post_id,
        "comment_id": comment_id,
        "user_id": user_id,
        "type": reaction_type,
        "action": action,
        "ts": timestamp.isoformat()
    }


def create_follow_changed_payload(
    follower_id: str,
    followee_id: str,
    action: Literal["followed", "unfollowed"],
    timestamp: datetime
) -> FollowChangedPayload:
    """Create a follow.changed event payload.
    
    Args:
        follower_id: Follower user UUID
        followee_id: Followee user UUID
        action: Whether user followed or unfollowed
        timestamp: Event timestamp
        
    Returns:
        FollowChangedPayload dict
    """
    return {
        "follower_id": follower_id,
        "followee_id": followee_id,
        "action": action,
        "ts": timestamp.isoformat()
    }
