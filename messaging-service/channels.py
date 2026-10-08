"""Channels API endpoints for Messaging Service."""
import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from models import Channel, ChannelMember
from outbox import create_outbox_event
from pydantic import BaseModel, Field, validator
from sqlalchemy import and_
from sqlalchemy.orm import Session
from utils import firebase_uid_to_uuid

router = APIRouter(prefix="/messaging/channels", tags=["channels"])


# Request/Response Models

class CreateChannelRequest(BaseModel):
    """Request model for creating a channel."""
    type: str = Field(..., description="Channel type: direct or group")
    name: str | None = Field(None, description="Channel name (required for group channels)")
    members: list[str] = Field(..., description="List of user IDs to add as members")
    app_id: str | None = Field(None, description="App ID")
    context_resource: dict | None = Field(None, description="Context resource {type, id, owner_id}")
    metadata: dict = Field(default_factory=dict, description="Additional channel metadata")
    
    @validator("type")
    def validate_type(cls, v):
        if v not in ["direct", "group"]:
            raise ValueError("type must be 'direct' or 'group'")
        return v
    
    @validator("members")
    def validate_members(cls, v, values):
        channel_type = values.get("type")
        
        if channel_type == "direct" and len(v) != 2:
            raise ValueError("direct channels must have exactly 2 members")
        
        if channel_type == "group" and len(v) > 100:
            raise ValueError("group channels cannot have more than 100 members")
        
        if len(v) == 0:
            raise ValueError("channels must have at least one member")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("members list contains duplicates")
        
        return v
    
    @validator("name")
    def validate_name(cls, v, values):
        channel_type = values.get("type")
        
        if channel_type == "group" and not v:
            raise ValueError("group channels must have a name")
        
        return v


class ChannelMemberResponse(BaseModel):
    """Response model for channel member."""
    user_id: str
    joined_at: datetime
    left_at: datetime | None = None
    
    class Config:
        from_attributes = True


class ChannelResponse(BaseModel):
    """Response model for channel."""
    id: str
    type: str
    name: str | None
    app_id: str | None
    context_resource: dict | None
    metadata: dict
    created_at: datetime
    updated_at: datetime
    members: list[ChannelMemberResponse] | None = None
    
    class Config:
        from_attributes = True


class ChannelListResponse(BaseModel):
    """Response model for channel list."""
    channels: list[ChannelResponse]
    cursor: str | None = None
    has_more: bool


class ManageMembersRequest(BaseModel):
    """Request model for managing channel members."""
    operation: str = Field(..., description="Operation: add, remove, or leave")
    user_ids: list[str] | None = Field(None, description="User IDs for add/remove operations")
    
    @validator("operation")
    def validate_operation(cls, v):
        if v not in ["add", "remove", "leave"]:
            raise ValueError("operation must be 'add', 'remove', or 'leave'")
        return v
    
    @validator("user_ids")
    def validate_user_ids(cls, v, values):
        operation = values.get("operation")
        
        if operation in ["add", "remove"] and not v:
            raise ValueError(f"{operation} operation requires user_ids")
        
        if operation == "leave" and v:
            raise ValueError("leave operation does not accept user_ids")
        
        return v


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


def get_active_members_count(db: Session, channel_id: UUID) -> int:
    """Get count of active members in a channel."""
    return db.query(ChannelMember).filter(
        and_(
            ChannelMember.channel_id == channel_id,
            ChannelMember.left_at.is_(None)
        )
    ).count()


# API Endpoints

@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(
    request: CreateChannelRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    x_app_id: str | None = Header(None, alias="X-App-Id")
):
    """Create a new channel.
    
    - **type**: Channel type (direct or group)
    - **name**: Channel name (required for group channels)
    - **members**: List of user IDs to add as members (including creator)
    - **metadata**: Additional channel metadata
    
    Requirements: 7.1, 7.2, 7.3, 7.5
    """
    try:
        # Ensure creator is in members list
        if user_id not in request.members:
            request.members.append(user_id)
        
        # Re-validate member count after adding creator
        if request.type == "direct" and len(request.members) != 2:
            raise HTTPException(
                status_code=422,
                detail="Direct channels must have exactly 2 members"
            )
        
        if request.type == "group" and len(request.members) > 100:
            raise HTTPException(
                status_code=422,
                detail="Group channels cannot have more than 100 members"
            )
        
        # Create channel
        channel = Channel(
            id=uuid4(),
            type=request.type,
            name=request.name,
            app_id=request.app_id or x_app_id,
            context_resource=request.context_resource,
            channel_metadata=request.metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(channel)
        
        # Add members
        for member_id in request.members:
            try:
                member_uuid = firebase_uid_to_uuid(member_id)
            except ValueError:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid user ID format: {member_id}"
                )
            
            channel_member = ChannelMember(
                channel_id=channel.id,
                user_id=member_uuid,
                joined_at=datetime.utcnow(),
                left_at=None
            )
            db.add(channel_member)
        
        # Create outbox event
        event_payload = {
            "channel_id": str(channel.id),
            "type": channel.type,
            "members": request.members,
            "created_by": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        create_outbox_event(
            db=db,
            stream_name="app.messaging.channel.created",
            event_type="messaging.channel.created",
            payload=event_payload
        )
        
        # Commit transaction
        db.commit()
        db.refresh(channel)
        
        # Load members for response
        members = db.query(ChannelMember).filter(
            ChannelMember.channel_id == channel.id
        ).all()
        
        return ChannelResponse(
            id=str(channel.id),
            type=channel.type,
            name=channel.name,
            app_id=channel.app_id,
            context_resource=channel.context_resource,
            metadata=channel.channel_metadata,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
            members=[
                ChannelMemberResponse(
                    user_id=str(m.user_id),
                    joined_at=m.joined_at,
                    left_at=m.left_at
                )
                for m in members
            ]
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create channel: {str(e)}")


@router.get("", response_model=ChannelListResponse)
async def list_channels(
    type: str | None = Query(None, description="Filter by channel type"),
    member: str | None = Query(None, description="Filter by member user ID"),
    updated_since: datetime | None = Query(None, description="Filter by updated_at timestamp"),
    limit: int = Query(20, ge=1, le=100, description="Number of channels to return"),
    cursor: str | None = Query(None, description="Cursor for pagination"),
    fields: str | None = Query(None, description="Comma-separated list of fields to include"),
    expand: str | None = Query(None, description="Comma-separated list of relations to expand"),
    app_id: str | None = Query(None, description="Filter by App ID"),
    x_app_id: str | None = Header(None, alias="X-App-Id"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Get list of channels.
    
    - **type**: Filter by channel type (direct or group)
    - **member**: Filter by member user ID
    - **updated_since**: Filter by updated_at timestamp
    - **limit**: Number of channels to return (default: 20, max: 100)
    - **cursor**: Cursor for pagination
    - **fields**: Comma-separated list of fields to include
    - **expand**: Comma-separated list of relations to expand (e.g., "members")
    
    Requirements: 7.1
    """
    try:
        # Build base query - only channels where user is a member
        query = db.query(Channel).join(
            ChannelMember,
            and_(
                ChannelMember.channel_id == Channel.id,
                ChannelMember.user_id == firebase_uid_to_uuid(user_id),
                ChannelMember.left_at.is_(None)
            )
        )
        
        # Filter by App ID
        target_app_id = app_id or x_app_id
        if target_app_id:
            query = query.filter(Channel.app_id == target_app_id)
        
        # Apply filters
        if type:
            if type not in ["direct", "group"]:
                raise HTTPException(status_code=400, detail="Invalid channel type")
            query = query.filter(Channel.type == type)
        
        if member:
            try:
                member_uuid = firebase_uid_to_uuid(member)
                # Join again to filter by another member
                query = query.join(
                    ChannelMember,
                    and_(
                        ChannelMember.channel_id == Channel.id,
                        ChannelMember.user_id == member_uuid,
                        ChannelMember.left_at.is_(None)
                    ),
                    isouter=False
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid member user ID format")
        
        if updated_since:
            query = query.filter(Channel.updated_at >= updated_since)
        
        # Apply cursor pagination
        if cursor:
            try:
                cursor_id = UUID(cursor)
                query = query.filter(Channel.id > cursor_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid cursor format")
        
        # Order by ID for consistent pagination
        query = query.order_by(Channel.id)
        
        # Fetch limit + 1 to check if there are more results
        channels = query.limit(limit + 1).all()
        
        has_more = len(channels) > limit
        if has_more:
            channels = channels[:limit]
        
        next_cursor = str(channels[-1].id) if channels and has_more else None
        
        # Determine if we should expand members
        expand_members = expand and "members" in expand.split(",")
        
        # Build response
        channel_responses = []
        for channel in channels:
            members_data = None
            if expand_members:
                members = db.query(ChannelMember).filter(
                    and_(
                        ChannelMember.channel_id == channel.id,
                        ChannelMember.left_at.is_(None)
                    )
                ).all()
                members_data = [
                    ChannelMemberResponse(
                        user_id=str(m.user_id),
                        joined_at=m.joined_at,
                        left_at=m.left_at
                    )
                    for m in members
                ]
            
            channel_responses.append(
                ChannelResponse(
                    id=str(channel.id),
                    type=channel.type,
                    name=channel.name,
                    app_id=channel.app_id,
                    context_resource=channel.context_resource,
                    metadata=channel.channel_metadata,
                    created_at=channel.created_at,
                    updated_at=channel.updated_at,
                    members=members_data
                )
            )
        
        return ChannelListResponse(
            channels=channel_responses,
            cursor=next_cursor,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list channels: {str(e)}")


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    expand: str | None = Query(None, description="Comma-separated list of relations to expand"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Get channel details.
    
    - **channel_id**: Channel UUID
    - **expand**: Comma-separated list of relations to expand (e.g., "members")
    
    Requirements: 7.1
    """
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")
    
    # Get channel
    channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check membership
    if not check_channel_membership(db, channel_uuid, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this channel")
    
    # Determine if we should expand members
    expand_members = expand and "members" in expand.split(",")
    
    members_data = None
    if expand_members:
        members = db.query(ChannelMember).filter(
            and_(
                ChannelMember.channel_id == channel.id,
                ChannelMember.left_at.is_(None)
            )
        ).all()
        members_data = [
            ChannelMemberResponse(
                user_id=str(m.user_id),
                joined_at=m.joined_at,
                left_at=m.left_at
            )
            for m in members
        ]
    
    return ChannelResponse(
        id=str(channel.id),
        type=channel.type,
        name=channel.name,
        app_id=channel.app_id,
        context_resource=channel.context_resource,
        metadata=channel.channel_metadata,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        members=members_data
    )


@router.post("/{channel_id}/members", status_code=200)
async def manage_members(
    channel_id: str,
    request: ManageMembersRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Manage channel members.
    
    - **operation**: Operation to perform (add, remove, leave)
    - **user_ids**: List of user IDs for add/remove operations
    
    Requirements: 7.4, 7.5
    """
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")
    
    # Get channel
    channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if user is a member (required for all operations)
    if not check_channel_membership(db, channel_uuid, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this channel")
    
    try:
        if request.operation == "add":
            # Add new members
            current_count = get_active_members_count(db, channel_uuid)
            
            # Check group size limit
            if channel.type == "group" and current_count + len(request.user_ids) > 100:
                raise HTTPException(
                    status_code=422,
                    detail="Cannot add members: would exceed maximum of 100 members"
                )
            
            # Direct channels cannot add members
            if channel.type == "direct":
                raise HTTPException(
                    status_code=422,
                    detail="Cannot add members to direct channels"
                )
            
            for member_id in request.user_ids:
                try:
                    member_uuid = firebase_uid_to_uuid(member_id)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid user ID format: {member_id}"
                    )
                
                # Check if already a member
                existing = db.query(ChannelMember).filter(
                    and_(
                        ChannelMember.channel_id == channel_uuid,
                        ChannelMember.user_id == member_uuid,
                        ChannelMember.left_at.is_(None)
                    )
                ).first()
                
                if existing:
                    continue  # Skip if already a member
                
                # Add member
                channel_member = ChannelMember(
                    channel_id=channel_uuid,
                    user_id=member_uuid,
                    joined_at=datetime.utcnow(),
                    left_at=None
                )
                db.add(channel_member)
                
                # Create outbox event
                event_payload = {
                    "channel_id": str(channel_uuid),
                    "user_id": member_id,
                    "added_by": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                create_outbox_event(
                    db=db,
                    stream_name="app.messaging.channel.member_added",
                    event_type="messaging.channel.member_added",
                    payload=event_payload
                )
                
                # Send WebSocket notification
                try:
                    from websocket_handler import notify_channel_member_added
                    asyncio.create_task(notify_channel_member_added(
                        str(channel_uuid),
                        member_id,
                        user_id
                    ))
                except Exception as e:
                    import logging
                    logging.error(f"Failed to send WebSocket notification: {e}")
            
            db.commit()
            return {"message": "Members added successfully"}
        
        elif request.operation == "remove":
            # Remove members (only in group channels)
            if channel.type == "direct":
                raise HTTPException(
                    status_code=422,
                    detail="Cannot remove members from direct channels"
                )
            
            for member_id in request.user_ids:
                try:
                    member_uuid = firebase_uid_to_uuid(member_id)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid user ID format: {member_id}"
                    )
                
                # Check if member exists
                member = db.query(ChannelMember).filter(
                    and_(
                        ChannelMember.channel_id == channel_uuid,
                        ChannelMember.user_id == member_uuid,
                        ChannelMember.left_at.is_(None)
                    )
                ).first()
                
                if member:
                    member.left_at = datetime.utcnow()
                    
                    # Send WebSocket notification
                    try:
                        from websocket_handler import notify_channel_member_removed
                        asyncio.create_task(notify_channel_member_removed(
                            str(channel_uuid),
                            member_id
                        ))
                    except Exception as e:
                        import logging
                        logging.error(f"Failed to send WebSocket notification: {e}")
            
            db.commit()
            return {"message": "Members removed successfully"}
        
        elif request.operation == "leave":
            # User leaves the channel
            member = db.query(ChannelMember).filter(
                and_(
                    ChannelMember.channel_id == channel_uuid,
                    ChannelMember.user_id == firebase_uid_to_uuid(user_id),
                    ChannelMember.left_at.is_(None)
                )
            ).first()
            
            if member:
                member.left_at = datetime.utcnow()
                
                # Send WebSocket notification
                try:
                    from websocket_handler import notify_channel_member_removed
                    asyncio.create_task(notify_channel_member_removed(
                        str(channel_uuid),
                        user_id
                    ))
                except Exception as e:
                    import logging
                    logging.error(f"Failed to send WebSocket notification: {e}")
                
                db.commit()
            
            return {"message": "Left channel successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to manage members: {str(e)}")
