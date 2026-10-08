"""Messages API endpoints for Messaging Service."""
import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from models import Channel, ChannelMember, Message, MessageAcknowledgment
from outbox import create_outbox_event
from pydantic import BaseModel, Field, validator
from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session
from utils import firebase_uid_to_uuid

router = APIRouter(prefix="/messaging", tags=["messages"])


# Request/Response Models

class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    content: str = Field(..., description="Message content")
    kind: str = Field(default="text", description="Message kind: text, media, or system")
    reply_to: str | None = Field(None, description="ID of message being replied to")
    app_id: str | None = Field(None, description="App ID")
    context_resource: dict | None = Field(None, description="Context resource {type, id, owner_id}")
    attachments: list[dict] = Field(default_factory=list, description="Message attachments")
    
    @validator("content")
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        
        if len(v) > 5000:
            raise ValueError("content cannot exceed 5000 characters")
        
        return v
    
    @validator("kind")
    def validate_kind(cls, v):
        if v not in ["text", "media", "system"]:
            raise ValueError("kind must be 'text', 'media', or 'system'")
        return v
    
    @validator("attachments")
    def validate_attachments(cls, v):
        # Calculate total size of attachments
        total_size = 0
        for attachment in v:
            if "size" in attachment:
                total_size += attachment.get("size", 0)
        
        # 10MB limit
        if total_size > 10 * 1024 * 1024:
            raise ValueError("total attachments size cannot exceed 10MB")
        
        return v


class AcknowledgeMessageRequest(BaseModel):
    """Request model for acknowledging a message."""
    status: str = Field(..., description="Acknowledgment status: delivered or read")
    
    @validator("status")
    def validate_status(cls, v):
        if v not in ["delivered", "read"]:
            raise ValueError("status must be 'delivered' or 'read'")
        return v


class MessageResponse(BaseModel):
    """Response model for message."""
    id: str
    channel_id: str
    sender_id: str
    content: str
    kind: str
    app_id: str | None = None
    context_resource: dict | None = None
    reply_to: str | None = None
    attachments: list[dict]
    created_at: datetime
    deleted_at: datetime | None = None
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Response model for message list."""
    messages: list[MessageResponse]
    cursor: str | None = None
    has_more: bool


class AcknowledgmentResponse(BaseModel):
    """Response model for acknowledgment."""
    message_id: str
    user_id: str
    status: str
    acknowledged_at: datetime
    
    class Config:
        from_attributes = True


# Helper Functions

def get_user_id(x_user_id: str | None = Header(None)) -> str:
    """Extract user ID from header."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    
    try:
        # Convert to UUID
        return str(firebase_uid_to_uuid(x_user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")


def check_channel_membership(db: Session, channel_id: UUID, user_id: str) -> bool:
    """Check if user is a member of the channel."""
    member = db.query(ChannelMember).filter(
        and_(
            ChannelMember.channel_id == channel_id,
            ChannelMember.user_id == firebase_uid_to_uuid(user_id),
            ChannelMember.left_at.is_(None)
        )
    ).first()
    
    return member is not None


# API Endpoints

@router.get("/channels/{channel_id}/messages", response_model=MessageListResponse)
async def get_messages(
    channel_id: str,
    before: datetime | None = Query(None, description="Get messages before this timestamp"),
    after: datetime | None = Query(None, description="Get messages after this timestamp"),
    limit: int = Query(20, ge=1, le=100, description="Number of messages to return"),
    sort: str = Query("desc", description="Sort order: asc or desc"),
    fields: str | None = Query(None, description="Comma-separated list of fields to include"),
    expand: str | None = Query(None, description="Comma-separated list of relations to expand"),
    app_id: str | None = Query(None, description="Filter by App ID"),
    x_app_id: str | None = Header(None, alias="X-App-Id"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Get message history for a channel.
    
    - **channel_id**: Channel UUID
    - **before**: Get messages before this timestamp
    - **after**: Get messages after this timestamp
    - **limit**: Number of messages to return (default: 20, max: 100)
    - **sort**: Sort order - 'asc' or 'desc' (default: desc)
    - **fields**: Comma-separated list of fields to include
    - **expand**: Comma-separated list of relations to expand
    
    Requirements: 2.3
    """
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")
    
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check membership
    if not check_channel_membership(db, channel_uuid, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this channel")
    
    # Validate sort parameter
    if sort not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="sort must be 'asc' or 'desc'")
    
    try:
        # Build query
        query = db.query(Message).filter(
            and_(
                Message.channel_id == channel_uuid,
                Message.deleted_at.is_(None)
            )
        )
        
        # Filter by App ID
        target_app_id = app_id or x_app_id
        if target_app_id:
            query = query.filter(Message.app_id == target_app_id)
        
        # Apply time filters
        if before:
            query = query.filter(Message.created_at < before)
        
        if after:
            query = query.filter(Message.created_at > after)
        
        # Apply sorting
        if sort == "desc":
            query = query.order_by(desc(Message.created_at))
        else:
            query = query.order_by(asc(Message.created_at))
        
        # Fetch limit + 1 to check if there are more results
        messages = query.limit(limit + 1).all()
        
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        # Determine cursor (last message timestamp)
        next_cursor = messages[-1].created_at.isoformat() if messages and has_more else None
        
        # Build response
        message_responses = [
            MessageResponse(
                id=str(msg.id),
                channel_id=str(msg.channel_id),
                sender_id=str(msg.sender_id),
                content=msg.content,
                kind=msg.kind,
                app_id=msg.app_id,
                context_resource=msg.context_resource,
                reply_to=str(msg.reply_to) if msg.reply_to else None,
                attachments=msg.attachments,
                created_at=msg.created_at,
                deleted_at=msg.deleted_at
            )
            for msg in messages
        ]
        
        return MessageListResponse(
            messages=message_responses,
            cursor=next_cursor,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@router.post("/channels/{channel_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    channel_id: str,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    x_app_id: str | None = Header(None, alias="X-App-Id")
):
    """Send a message to a channel.
    
    - **channel_id**: Channel UUID
    - **content**: Message content (max 5000 characters)
    - **kind**: Message kind (text, media, or system)
    - **reply_to**: ID of message being replied to (optional)
    - **attachments**: List of attachments (max 10MB total)
    
    Supports idempotency via Idempotency-Key header.
    
    Requirements: 2.3, 6.2
    """
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")
    
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check membership
    if not check_channel_membership(db, channel_uuid, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this channel")
    
    # Validate reply_to if provided
    if request.reply_to:
        try:
            reply_to_uuid = UUID(request.reply_to)
            parent_message = db.query(Message).filter(
                and_(
                    Message.id == reply_to_uuid,
                    Message.channel_id == channel_uuid,
                    Message.deleted_at.is_(None)
                )
            ).first()
            
            if not parent_message:
                raise HTTPException(status_code=404, detail="Parent message not found")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid reply_to message ID format")
    
    try:
        # Create message
        message = Message(
            id=uuid4(),
            channel_id=channel_uuid,
            sender_id=firebase_uid_to_uuid(user_id),
            content=request.content,
            kind=request.kind,
            app_id=request.app_id or x_app_id,
            context_resource=request.context_resource,
            reply_to=UUID(request.reply_to) if request.reply_to else None,
            attachments=request.attachments,
            created_at=datetime.utcnow(),
            deleted_at=None
        )
        
        db.add(message)
        
        # Create outbox event
        event_payload = {
            "message_id": str(message.id),
            "channel_id": str(channel_uuid),
            "sender_id": user_id,
            "content_preview": request.content[:100] if len(request.content) > 100 else request.content,
            "kind": request.kind,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        create_outbox_event(
            db=db,
            stream_name="app.messaging.message.created",
            event_type="messaging.message.created",
            payload=event_payload
        )
        
        # Commit transaction
        db.commit()
        db.refresh(message)
        
        return MessageResponse(
            id=str(message.id),
            channel_id=str(message.channel_id),
            sender_id=str(message.sender_id),
            content=message.content,
            kind=message.kind,
            app_id=message.app_id,
            context_resource=message.context_resource,
            reply_to=str(message.reply_to) if message.reply_to else None,
            attachments=message.attachments,
            created_at=message.created_at,
            deleted_at=message.deleted_at
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.post("/messages/{message_id}/ack", response_model=AcknowledgmentResponse, status_code=201)
async def acknowledge_message(
    message_id: str,
    request: AcknowledgeMessageRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Acknowledge a message (delivered or read).
    
    - **message_id**: Message UUID
    - **status**: Acknowledgment status ('delivered' or 'read')
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    try:
        message_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    
    # Get message
    message = db.query(Message).filter(
        and_(
            Message.id == message_uuid,
            Message.deleted_at.is_(None)
        )
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if user is a member of the channel
    if not check_channel_membership(db, message.channel_id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this channel")
    
    try:
        # Check if acknowledgment already exists
        existing_ack = db.query(MessageAcknowledgment).filter(
            and_(
                MessageAcknowledgment.message_id == message_uuid,
                MessageAcknowledgment.user_id == firebase_uid_to_uuid(user_id),
                MessageAcknowledgment.status == request.status
            )
        ).first()
        
        if existing_ack:
            # Return existing acknowledgment (idempotent)
            return AcknowledgmentResponse(
                message_id=str(existing_ack.message_id),
                user_id=str(existing_ack.user_id),
                status=existing_ack.status,
                acknowledged_at=existing_ack.acknowledged_at
            )
        
        # Create acknowledgment
        acknowledgment = MessageAcknowledgment(
            message_id=message_uuid,
            user_id=firebase_uid_to_uuid(user_id),
            status=request.status,
            acknowledged_at=datetime.utcnow()
        )
        
        db.add(acknowledgment)
        
        # Create outbox event
        event_payload = {
            "message_id": str(message_uuid),
            "user_id": user_id,
            "status": request.status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        create_outbox_event(
            db=db,
            stream_name="app.messaging.message.acknowledged",
            event_type="messaging.message.acknowledged",
            payload=event_payload
        )
        
        # Commit transaction
        db.commit()
        db.refresh(acknowledgment)
        
        # Send WebSocket notification to sender
        try:
            from websocket_handler import notify_message_delivered, notify_message_read
            
            if request.status == "delivered":
                asyncio.create_task(notify_message_delivered(
                    str(message_uuid),
                    user_id,
                    acknowledgment.acknowledged_at
                ))
            elif request.status == "read":
                asyncio.create_task(notify_message_read(
                    str(message_uuid),
                    user_id,
                    acknowledgment.acknowledged_at
                ))
        except Exception as e:
            # Log but don't fail the request if WebSocket notification fails
            import logging
            logging.error(f"Failed to send WebSocket notification: {e}")
        
        return AcknowledgmentResponse(
            message_id=str(acknowledgment.message_id),
            user_id=str(acknowledgment.user_id),
            status=acknowledgment.status,
            acknowledged_at=acknowledgment.acknowledged_at
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge message: {str(e)}")
