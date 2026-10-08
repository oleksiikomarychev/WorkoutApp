"""WebSocket handler for real-time messaging."""
import asyncio
import json
import logging
from datetime import datetime
from uuid import UUID

from config import settings
from database import SessionLocal
from fastapi import Query, WebSocket, WebSocketDisconnect
from models import Channel, ChannelMember, Message
from outbox import create_outbox_event
from presence import delete_user_presence, get_redis_client, set_user_presence, update_user_presence_ttl
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and channel subscriptions."""
    
    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.user_connections: dict[str, set[WebSocket]] = {}
        
        # Map of channel_id -> set of WebSocket connections
        self.channel_rooms: dict[str, set[WebSocket]] = {}
        
        # Map of WebSocket -> user_id
        self.connection_users: dict[WebSocket, str] = {}
        
        # Map of WebSocket -> last heartbeat timestamp
        self.connection_heartbeats: dict[WebSocket, datetime] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        # Check if this is the first connection for this user
        is_first_connection = user_id not in self.user_connections or len(self.user_connections[user_id]) == 0
        
        # Register connection
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        
        self.user_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        self.connection_heartbeats[websocket] = datetime.utcnow()
        
        # Set user presence
        set_user_presence(UUID(user_id), "online")
        
        # Notify presence change if this is the first connection
        if is_first_connection:
            asyncio.create_task(notify_presence_change(user_id, "online"))
        
        logger.info(f"WebSocket connected: user_id={user_id}, total_connections={len(self.user_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket):
        """Unregister a WebSocket connection and clean up."""
        user_id = self.connection_users.get(websocket)
        
        if not user_id:
            return
        
        # Check if this is the last connection for this user
        is_last_connection = (user_id in self.user_connections and 
                             len(self.user_connections[user_id]) == 1 and 
                             websocket in self.user_connections[user_id])
        
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            
            # Clean up empty sets
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                # Delete presence if no more connections
                delete_user_presence(UUID(user_id))
        
        # Remove from all channel rooms
        for channel_id, connections in list(self.channel_rooms.items()):
            if websocket in connections:
                connections.discard(websocket)
                
                # Clean up empty rooms
                if not connections:
                    del self.channel_rooms[channel_id]
        
        # Clean up mappings
        self.connection_users.pop(websocket, None)
        self.connection_heartbeats.pop(websocket, None)
        
        # Notify presence change if this was the last connection
        if is_last_connection:
            asyncio.create_task(notify_presence_change(user_id, "offline"))
        
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    def join_channel(self, websocket: WebSocket, channel_id: str):
        """Add a WebSocket connection to a channel room."""
        if channel_id not in self.channel_rooms:
            self.channel_rooms[channel_id] = set()
        
        self.channel_rooms[channel_id].add(websocket)
        
        user_id = self.connection_users.get(websocket)
        logger.info(f"User {user_id} joined channel {channel_id}")
    
    def leave_channel(self, websocket: WebSocket, channel_id: str):
        """Remove a WebSocket connection from a channel room."""
        if channel_id in self.channel_rooms:
            self.channel_rooms[channel_id].discard(websocket)
            
            # Clean up empty rooms
            if not self.channel_rooms[channel_id]:
                del self.channel_rooms[channel_id]
        
        user_id = self.connection_users.get(websocket)
        logger.info(f"User {user_id} left channel {channel_id}")
    
    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to connection: {e}")
    
    async def broadcast_to_channel(self, channel_id: str, message: dict, exclude: WebSocket | None = None):
        """Broadcast a message to all connections in a channel room."""
        if channel_id not in self.channel_rooms:
            return
        
        connections = self.channel_rooms[channel_id].copy()
        
        for connection in connections:
            if connection != exclude:
                await self.send_to_connection(connection, message)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections of a specific user."""
        if user_id not in self.user_connections:
            return
        
        connections = self.user_connections[user_id].copy()
        
        for connection in connections:
            await self.send_to_connection(connection, message)
    
    def update_heartbeat(self, websocket: WebSocket):
        """Update the last heartbeat timestamp for a connection."""
        self.connection_heartbeats[websocket] = datetime.utcnow()
        
        # Update presence TTL
        user_id = self.connection_users.get(websocket)
        if user_id:
            update_user_presence_ttl(UUID(user_id))
    
    def get_stale_connections(self) -> list[WebSocket]:
        """Get connections that haven't sent a heartbeat within the timeout period."""
        timeout_seconds = settings.ws_heartbeat_timeout
        now = datetime.utcnow()
        stale = []
        
        for websocket, last_heartbeat in self.connection_heartbeats.items():
            elapsed = (now - last_heartbeat).total_seconds()
            if elapsed > timeout_seconds:
                stale.append(websocket)
        
        return stale
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user."""
        return len(self.user_connections.get(user_id, set()))


# Global connection manager instance
manager = ConnectionManager()


def get_db_session() -> Session:
    """Get a database session."""
    return SessionLocal()


def check_channel_membership(db: Session, channel_id: UUID, user_id: str) -> bool:
    """Check if user is a member of the channel."""
    member = db.query(ChannelMember).filter(
        ChannelMember.channel_id == channel_id,
        ChannelMember.user_id == UUID(user_id),
        ChannelMember.left_at.is_(None)
    ).first()
    
    return member is not None


async def handle_websocket(websocket: WebSocket, user_id: str | None = Query(None)):
    """Handle WebSocket connection for messaging.
    
    Args:
        websocket: WebSocket connection
        user_id: User ID from query parameter or X-User-Id header
    """
    # Extract user_id from query parameter or header
    if not user_id:
        # Try to get from headers
        user_id = websocket.headers.get("x-user-id")
    
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized: user_id required")
        return
    
    # Validate user_id format
    try:
        UUID(user_id)
    except ValueError:
        await websocket.close(code=4001, reason="Unauthorized: invalid user_id format")
        return
    
    # Connect to manager
    await manager.connect(websocket, user_id)
    
    db = get_db_session()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Check message size (64KB limit)
            if len(data.encode('utf-8')) > settings.ws_max_message_size:
                await websocket.close(code=4009, reason="Message too large")
                break
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_to_connection(websocket, {
                    "type": "error",
                    "code": "INVALID_JSON",
                    "message": "Invalid JSON format"
                })
                continue
            
            # Handle different message types
            message_type = message.get("type")
            
            if message_type == "heartbeat":
                await handle_heartbeat(websocket, user_id, message)
            
            elif message_type == "join_channel":
                await handle_join_channel(websocket, user_id, message, db)
            
            elif message_type == "leave_channel":
                await handle_leave_channel(websocket, user_id, message, db)
            
            elif message_type == "send_message":
                await handle_send_message(websocket, user_id, message, db)
            
            elif message_type == "typing":
                await handle_typing(websocket, user_id, message, db)
            
            else:
                await manager.send_to_connection(websocket, {
                    "type": "error",
                    "code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: user_id={user_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    
    finally:
        manager.disconnect(websocket)
        db.close()


async def handle_heartbeat(websocket: WebSocket, user_id: str, message: dict):
    """Handle heartbeat message to keep connection alive."""
    manager.update_heartbeat(websocket)
    
    # Optionally send acknowledgment
    # await manager.send_to_connection(websocket, {"type": "heartbeat_ack"})


async def handle_join_channel(websocket: WebSocket, user_id: str, message: dict, db: Session):
    """Handle join_channel message."""
    channel_id = message.get("channel_id")
    
    if not channel_id:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "MISSING_CHANNEL_ID",
            "message": "channel_id is required"
        })
        return
    
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "INVALID_CHANNEL_ID",
            "message": "Invalid channel_id format"
        })
        return
    
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
    if not channel:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "CHANNEL_NOT_FOUND",
            "message": "Channel not found"
        })
        return
    
    # Check membership
    if not check_channel_membership(db, channel_uuid, user_id):
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "NOT_MEMBER",
            "message": "You are not a member of this channel"
        })
        return
    
    # Join the channel room
    manager.join_channel(websocket, channel_id)
    
    # Notify other members
    await manager.broadcast_to_channel(channel_id, {
        "type": "user_joined",
        "channel_id": channel_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }, exclude=websocket)


async def handle_leave_channel(websocket: WebSocket, user_id: str, message: dict, db: Session):
    """Handle leave_channel message."""
    channel_id = message.get("channel_id")
    
    if not channel_id:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "MISSING_CHANNEL_ID",
            "message": "channel_id is required"
        })
        return
    
    # Leave the channel room
    manager.leave_channel(websocket, channel_id)
    
    # Notify other members
    await manager.broadcast_to_channel(channel_id, {
        "type": "user_left",
        "channel_id": channel_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    })


async def handle_send_message(websocket: WebSocket, user_id: str, message: dict, db: Session):
    """Handle send_message to create and broadcast a message."""
    channel_id = message.get("channel_id")
    content = message.get("content")
    kind = message.get("kind", "text")
    
    if not channel_id:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "MISSING_CHANNEL_ID",
            "message": "channel_id is required"
        })
        return
    
    if not content:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "MISSING_CONTENT",
            "message": "content is required"
        })
        return
    
    # Validate content length
    if len(content) > 5000:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "CONTENT_TOO_LONG",
            "message": "content cannot exceed 5000 characters"
        })
        return
    
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "INVALID_CHANNEL_ID",
            "message": "Invalid channel_id format"
        })
        return
    
    # Check membership
    if not check_channel_membership(db, channel_uuid, user_id):
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "NOT_MEMBER",
            "message": "You are not a member of this channel"
        })
        return
    
    try:
        # Create message in database
        new_message = Message(
            channel_id=channel_uuid,
            sender_id=UUID(user_id),
            content=content,
            kind=kind,
            reply_to=None,
            attachments=[],
            created_at=datetime.utcnow()
        )
        
        db.add(new_message)
        
        # Create outbox event
        event_payload = {
            "message_id": str(new_message.id),
            "channel_id": channel_id,
            "sender_id": user_id,
            "content_preview": content[:100] if len(content) > 100 else content,
            "kind": kind,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        create_outbox_event(
            db=db,
            stream_name="app.messaging.message.created",
            event_type="messaging.message.created",
            payload=event_payload
        )
        
        db.commit()
        db.refresh(new_message)
        
        # Broadcast to all channel members
        await manager.broadcast_to_channel(channel_id, {
            "type": "message",
            "message_id": str(new_message.id),
            "channel_id": channel_id,
            "sender_id": user_id,
            "content": content,
            "kind": kind,
            "timestamp": new_message.created_at.isoformat()
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send message: {e}", exc_info=True)
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "MESSAGE_SEND_FAILED",
            "message": f"Failed to send message: {str(e)}"
        })


async def handle_typing(websocket: WebSocket, user_id: str, message: dict, db: Session):
    """Handle typing indicator."""
    channel_id = message.get("channel_id")
    
    if not channel_id:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "MISSING_CHANNEL_ID",
            "message": "channel_id is required"
        })
        return
    
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        await manager.send_to_connection(websocket, {
            "type": "error",
            "code": "INVALID_CHANNEL_ID",
            "message": "Invalid channel_id format"
        })
        return
    
    # Check membership
    if not check_channel_membership(db, channel_uuid, user_id):
        return
    
    # Store typing indicator in Redis with TTL
    redis_client = get_redis_client()
    typing_key = f"typing:{channel_id}:{user_id}"
    redis_client.setex(typing_key, settings.typing_ttl, "1")
    
    # Broadcast typing indicator to other channel members
    await manager.broadcast_to_channel(channel_id, {
        "type": "typing",
        "channel_id": channel_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }, exclude=websocket)


async def heartbeat_monitor():
    """Background task to monitor and close stale connections."""
    while True:
        try:
            stale_connections = manager.get_stale_connections()
            
            for websocket in stale_connections:
                user_id = manager.connection_users.get(websocket)
                logger.warning(f"Closing stale connection for user {user_id}")
                
                try:
                    await websocket.close(code=4000, reason="Heartbeat timeout")
                except Exception as e:
                    logger.error(f"Error closing stale connection: {e}")
                
                manager.disconnect(websocket)
            
            # Check every 10 seconds
            await asyncio.sleep(10)
        
        except Exception as e:
            logger.error(f"Error in heartbeat monitor: {e}", exc_info=True)
            await asyncio.sleep(10)


# Public API functions for sending server-to-client messages

async def notify_message_delivered(message_id: str, user_id: str, timestamp: datetime):
    """Send delivered notification to message sender.
    
    Args:
        message_id: Message UUID
        user_id: User who received the message
        timestamp: Acknowledgment timestamp
    """
    # Get the message to find the sender
    db = get_db_session()
    try:
        message = db.query(Message).filter(Message.id == UUID(message_id)).first()
        if message:
            sender_id = str(message.sender_id)
            await manager.send_to_user(sender_id, {
                "type": "delivered",
                "message_id": message_id,
                "user_id": user_id,
                "timestamp": timestamp.isoformat()
            })
    finally:
        db.close()


async def notify_message_read(message_id: str, user_id: str, timestamp: datetime):
    """Send read notification to message sender.
    
    Args:
        message_id: Message UUID
        user_id: User who read the message
        timestamp: Acknowledgment timestamp
    """
    # Get the message to find the sender
    db = get_db_session()
    try:
        message = db.query(Message).filter(Message.id == UUID(message_id)).first()
        if message:
            sender_id = str(message.sender_id)
            await manager.send_to_user(sender_id, {
                "type": "read",
                "message_id": message_id,
                "user_id": user_id,
                "timestamp": timestamp.isoformat()
            })
    finally:
        db.close()


async def notify_channel_member_added(channel_id: str, user_id: str, added_by: str):
    """Notify channel members when a new member is added.
    
    Args:
        channel_id: Channel UUID
        user_id: User who was added
        added_by: User who added the member
    """
    await manager.broadcast_to_channel(channel_id, {
        "type": "user_joined",
        "channel_id": channel_id,
        "user_id": user_id,
        "added_by": added_by,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_channel_member_removed(channel_id: str, user_id: str):
    """Notify channel members when a member is removed.
    
    Args:
        channel_id: Channel UUID
        user_id: User who was removed
    """
    await manager.broadcast_to_channel(channel_id, {
        "type": "user_left",
        "channel_id": channel_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_presence_change(user_id: str, status: str):
    """Notify relevant users about presence status change.
    
    Args:
        user_id: User whose presence changed
        status: New presence status (online/offline)
    """
    # Get all channels the user is a member of
    db = get_db_session()
    try:
        memberships = db.query(ChannelMember).filter(
            ChannelMember.user_id == UUID(user_id),
            ChannelMember.left_at.is_(None)
        ).all()
        
        # Notify all members of those channels
        notified_users = set()
        for membership in memberships:
            channel_id = str(membership.channel_id)
            
            # Get all members of this channel
            channel_members = db.query(ChannelMember).filter(
                ChannelMember.channel_id == membership.channel_id,
                ChannelMember.left_at.is_(None)
            ).all()
            
            for member in channel_members:
                member_user_id = str(member.user_id)
                if member_user_id != user_id and member_user_id not in notified_users:
                    await manager.send_to_user(member_user_id, {
                        "type": "presence",
                        "user_id": user_id,
                        "status": status,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    notified_users.add(member_user_id)
    finally:
        db.close()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance.
    
    Returns:
        ConnectionManager instance
    """
    return manager
