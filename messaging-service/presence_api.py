"""Presence API endpoints for Messaging Service."""
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException
from models import ChannelMember
from presence import get_multiple_user_presence
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

router = APIRouter(prefix="/messaging", tags=["presence"])


# Response Models

class PresenceStatus(BaseModel):
    """Presence status for a user."""
    user_id: str
    status: str | None = None
    last_seen: str | None = None


class PresenceResponse(BaseModel):
    """Response model for presence endpoint."""
    presence: list[PresenceStatus]


# Endpoints

@router.get("/presence", response_model=PresenceResponse)
async def get_presence(
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Get online status of participants in user's channels.
    
    Returns presence information for all users who are members of channels
    that the requesting user is also a member of.
    
    Args:
        x_user_id: User ID from header (set by Gateway)
        db: Database session
        
    Returns:
        PresenceResponse with list of user presence statuses
    """
    try:
        user_uuid = UUID(x_user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    # Get all channels the user is a member of
    user_channels = db.query(ChannelMember.channel_id).filter(
        and_(
            ChannelMember.user_id == user_uuid,
            ChannelMember.left_at.is_(None)
        )
    ).all()
    
    if not user_channels:
        # User is not a member of any channels
        return PresenceResponse(presence=[])
    
    channel_ids = [channel.channel_id for channel in user_channels]
    
    # Get all unique members from these channels (excluding the requesting user)
    channel_members = db.query(ChannelMember.user_id).filter(
        and_(
            ChannelMember.channel_id.in_(channel_ids),
            ChannelMember.user_id != user_uuid,
            ChannelMember.left_at.is_(None)
        )
    ).distinct().all()
    
    if not channel_members:
        # No other members in user's channels
        return PresenceResponse(presence=[])
    
    # Extract user IDs
    member_user_ids = [member.user_id for member in channel_members]
    
    # Get presence data from Redis
    presence_data = get_multiple_user_presence(member_user_ids)
    
    # Build response
    presence_list = []
    for user_id_str, presence_info in presence_data.items():
        if presence_info:
            presence_list.append(
                PresenceStatus(
                    user_id=user_id_str,
                    status=presence_info.get("status"),
                    last_seen=presence_info.get("last_seen")
                )
            )
        else:
            # User is offline (no presence data in Redis)
            presence_list.append(
                PresenceStatus(
                    user_id=user_id_str,
                    status="offline",
                    last_seen=None
                )
            )
    
    return PresenceResponse(presence=presence_list)
