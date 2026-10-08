"""Subscriptions API endpoints."""
from datetime import datetime
from uuid import NAMESPACE_DNS, UUID, uuid5

from database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from models import Follow
from outbox import create_outbox_event
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/social", tags=["subscriptions"])


def firebase_uid_to_uuid(firebase_uid: str) -> UUID:
    """Convert Firebase UID to deterministic UUID using UUID5.
    
    Args:
        firebase_uid: Firebase user ID (string)
        
    Returns:
        UUID generated from Firebase UID
    """
    return uuid5(NAMESPACE_DNS, f"firebase:{firebase_uid}")


# Pydantic models for request/response
class FollowResponse(BaseModel):
    """Response model for follow operation."""
    follower_id: UUID
    followee_id: UUID
    created_at: datetime
    action: str  # "created" or "deleted"
    
    class Config:
        from_attributes = True


class FollowListItem(BaseModel):
    """Response model for a follow list item."""
    user_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class FollowListResponse(BaseModel):
    """Response model for follow list endpoints."""
    users: list[FollowListItem]
    cursor: str | None = None
    has_more: bool = False


@router.post("/follow/{user_id}", response_model=FollowResponse, status_code=201)
async def follow_user(
    user_id: UUID,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Follow a user.
    
    Creates a subscription relationship between the current user and the target user.
    Users cannot follow themselves.
    
    This endpoint supports idempotency via the Idempotency-Key header.
    The idempotency is handled by the IdempotencyMiddleware.
    
    Args:
        user_id: UUID of the user to follow
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        Follow relationship with action "created"
        
    Raises:
        HTTPException: 401 if X-User-Id missing, 400 if trying to self-follow, 409 if already following
    """
    # Validate X-User-Id header
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_USER_ID",
                    "message": "X-User-Id header is required"
                }
            }
        )
    
    try:
        follower_id = firebase_uid_to_uuid(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": "X-User-Id must be a valid UUID"
                }
            }
        )
    
    # Prevent self-follow
    if follower_id == user_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "SELF_FOLLOW_NOT_ALLOWED",
                    "message": "You cannot follow yourself"
                }
            }
        )
    
    # Check if already following
    existing_follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.followee_id == user_id
    ).first()
    
    if existing_follow:
        # Already following - return existing relationship (idempotent)
        return FollowResponse(
            follower_id=existing_follow.follower_id,
            followee_id=existing_follow.followee_id,
            created_at=existing_follow.created_at,
            action="created"
        )
    
    # Create new follow relationship
    follow = Follow(
        follower_id=follower_id,
        followee_id=user_id,
        created_at=datetime.utcnow()
    )
    
    try:
        # Add follow to database
        db.add(follow)
        db.flush()  # Flush to ensure the follow is created
        
        # Create outbox event in the same transaction
        event_payload = {
            "follower_id": str(follow.follower_id),
            "followee_id": str(follow.followee_id),
            "action": "created",
            "ts": follow.created_at.isoformat()
        }
        
        create_outbox_event(
            db=db,
            stream_name="app.social.follow.changed",
            event_type="follow.changed",
            payload=event_payload
        )
        
        # Commit transaction
        db.commit()
        db.refresh(follow)
        
        return FollowResponse(
            follower_id=follow.follower_id,
            followee_id=follow.followee_id,
            created_at=follow.created_at,
            action="created"
        )
        
    except IntegrityError as e:
        db.rollback()
        # Handle race condition where follow was created between check and insert
        existing_follow = db.query(Follow).filter(
            Follow.follower_id == follower_id,
            Follow.followee_id == user_id
        ).first()
        
        if existing_follow:
            return FollowResponse(
                follower_id=existing_follow.follower_id,
                followee_id=existing_follow.followee_id,
                created_at=existing_follow.created_at,
                action="created"
            )
        
        # Some other integrity error
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "FOLLOW_CREATION_FAILED",
                    "message": "Failed to create follow relationship",
                    "details": str(e)
                }
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "FOLLOW_CREATION_FAILED",
                    "message": "Failed to create follow relationship",
                    "details": str(e)
                }
            }
        )



@router.delete("/follow/{user_id}", response_model=FollowResponse, status_code=200)
async def unfollow_user(
    user_id: UUID,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Unfollow a user.
    
    Removes the subscription relationship between the current user and the target user.
    
    This endpoint supports idempotency via the Idempotency-Key header.
    The idempotency is handled by the IdempotencyMiddleware.
    
    Args:
        user_id: UUID of the user to unfollow
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        Follow relationship with action "deleted"
        
    Raises:
        HTTPException: 401 if X-User-Id missing, 404 if not following
    """
    # Validate X-User-Id header
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_USER_ID",
                    "message": "X-User-Id header is required"
                }
            }
        )
    
    try:
        follower_id = firebase_uid_to_uuid(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": "X-User-Id must be a valid UUID"
                }
            }
        )
    
    # Find existing follow relationship
    follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.followee_id == user_id
    ).first()
    
    if not follow:
        # Not following - return 404
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FOLLOW_NOT_FOUND",
                    "message": "You are not following this user"
                }
            }
        )
    
    # Store follow data before deletion
    follow_data = {
        "follower_id": follow.follower_id,
        "followee_id": follow.followee_id,
        "created_at": follow.created_at
    }
    timestamp = datetime.utcnow()
    
    try:
        # Delete follow relationship
        db.delete(follow)
        db.flush()
        
        # Create outbox event in the same transaction
        event_payload = {
            "follower_id": str(follow_data["follower_id"]),
            "followee_id": str(follow_data["followee_id"]),
            "action": "deleted",
            "ts": timestamp.isoformat()
        }
        
        create_outbox_event(
            db=db,
            stream_name="app.social.follow.changed",
            event_type="follow.changed",
            payload=event_payload
        )
        
        # Commit transaction
        db.commit()
        
        return FollowResponse(
            follower_id=follow_data["follower_id"],
            followee_id=follow_data["followee_id"],
            created_at=follow_data["created_at"],
            action="deleted"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "UNFOLLOW_FAILED",
                    "message": "Failed to unfollow user",
                    "details": str(e)
                }
            }
        )



@router.get("/subscriptions", response_model=FollowListResponse)
async def get_subscriptions(
    limit: int = Query(20, ge=1, le=100, description="Number of subscriptions to return"),
    cursor: str | None = Query(None, description="Cursor for pagination (user_id:timestamp)"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Get list of users that the current user is following (subscriptions).
    
    Returns a paginated list of users that the current user has subscribed to.
    
    Args:
        limit: Number of subscriptions to return (1-100)
        cursor: Pagination cursor (user_id:timestamp)
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        List of subscriptions with pagination cursor
        
    Raises:
        HTTPException: 401 if X-User-Id missing
    """
    # Validate X-User-Id header
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_USER_ID",
                    "message": "X-User-Id header is required"
                }
            }
        )
    
    try:
        user_id = firebase_uid_to_uuid(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": "X-User-Id must be a valid UUID"
                }
            }
        )
    
    # Build query for subscriptions (users that current user follows)
    query_builder = db.query(Follow).filter(
        Follow.follower_id == user_id
    )
    
    # Apply cursor pagination
    if cursor:
        try:
            # Cursor format: "user_id:timestamp"
            cursor_parts = cursor.split(":")
            cursor_user_id = UUID(cursor_parts[0])
            cursor_timestamp = datetime.fromisoformat(cursor_parts[1])
            
            # Paginate by created_at descending (newest first)
            query_builder = query_builder.filter(
                or_(
                    Follow.created_at < cursor_timestamp,
                    and_(
                        Follow.created_at == cursor_timestamp,
                        Follow.followee_id < cursor_user_id
                    )
                )
            )
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_CURSOR",
                        "message": "Invalid cursor format"
                    }
                }
            )
    
    # Order by created_at descending (newest first)
    query_builder = query_builder.order_by(Follow.created_at.desc(), Follow.followee_id.desc())
    
    # Fetch limit + 1 to check if there are more results
    follows = query_builder.limit(limit + 1).all()
    
    # Check if there are more results
    has_more = len(follows) > limit
    if has_more:
        follows = follows[:limit]
    
    # Build response
    users = [
        FollowListItem(
            user_id=follow.followee_id,
            created_at=follow.created_at
        )
        for follow in follows
    ]
    
    # Generate next cursor
    next_cursor = None
    if has_more and follows:
        last_follow = follows[-1]
        next_cursor = f"{last_follow.followee_id}:{last_follow.created_at.isoformat()}"
    
    return FollowListResponse(
        users=users,
        cursor=next_cursor,
        has_more=has_more
    )


@router.get("/followers", response_model=FollowListResponse)
async def get_followers(
    limit: int = Query(20, ge=1, le=100, description="Number of followers to return"),
    cursor: str | None = Query(None, description="Cursor for pagination (user_id:timestamp)"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Get list of users that are following the current user (followers).
    
    Returns a paginated list of users that have subscribed to the current user.
    
    Args:
        limit: Number of followers to return (1-100)
        cursor: Pagination cursor (user_id:timestamp)
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        List of followers with pagination cursor
        
    Raises:
        HTTPException: 401 if X-User-Id missing
    """
    # Validate X-User-Id header
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "MISSING_USER_ID",
                    "message": "X-User-Id header is required"
                }
            }
        )
    
    try:
        user_id = firebase_uid_to_uuid(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": "X-User-Id must be a valid UUID"
                }
            }
        )
    
    # Build query for followers (users that follow current user)
    query_builder = db.query(Follow).filter(
        Follow.followee_id == user_id
    )
    
    # Apply cursor pagination
    if cursor:
        try:
            # Cursor format: "user_id:timestamp"
            cursor_parts = cursor.split(":")
            cursor_user_id = UUID(cursor_parts[0])
            cursor_timestamp = datetime.fromisoformat(cursor_parts[1])
            
            # Paginate by created_at descending (newest first)
            query_builder = query_builder.filter(
                or_(
                    Follow.created_at < cursor_timestamp,
                    and_(
                        Follow.created_at == cursor_timestamp,
                        Follow.follower_id < cursor_user_id
                    )
                )
            )
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_CURSOR",
                        "message": "Invalid cursor format"
                    }
                }
            )
    
    # Order by created_at descending (newest first)
    query_builder = query_builder.order_by(Follow.created_at.desc(), Follow.follower_id.desc())
    
    # Fetch limit + 1 to check if there are more results
    follows = query_builder.limit(limit + 1).all()
    
    # Check if there are more results
    has_more = len(follows) > limit
    if has_more:
        follows = follows[:limit]
    
    # Build response
    users = [
        FollowListItem(
            user_id=follow.follower_id,
            created_at=follow.created_at
        )
        for follow in follows
    ]
    
    # Generate next cursor
    next_cursor = None
    if has_more and follows:
        last_follow = follows[-1]
        next_cursor = f"{last_follow.follower_id}:{last_follow.created_at.isoformat()}"
    
    return FollowListResponse(
        users=users,
        cursor=next_cursor,
        has_more=has_more
    )
