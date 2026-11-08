"""Subscriptions API endpoints."""
from datetime import datetime
from uuid import UUID

from database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from models import Follow
from outbox import create_outbox_event
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from utils import parse_user_id, utcnow

router = APIRouter(prefix="/social", tags=["subscriptions"])


# Pydantic models for request/response
class FollowResponse(BaseModel):
    """Response model for follow operation."""

    follower_id: UUID
    followee_id: UUID
    created_at: datetime
    action: str  # "created" or "deleted"

    model_config = ConfigDict(from_attributes=True)


class FollowListItem(BaseModel):
    """Response model for a follow list item."""

    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FollowListResponse(BaseModel):
    """Response model for follow list endpoints."""

    users: list[FollowListItem]
    cursor: str | None = None
    has_more: bool = False


@router.post("/follow/{user_id}", response_model=FollowResponse, status_code=status.HTTP_201_CREATED)
async def follow_user(
    user_id: UUID,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> FollowResponse:
    """Follow a user.

    Creates a subscription relationship between the current user and the target user.
    Users cannot follow themselves.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_USER_ID",
                    "message": "X-User-Id header is required",
                }
            },
        )

    try:
        follower_id = parse_user_id(x_user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": "X-User-Id must be a valid user identifier",
                }
            },
        )

    # Prevent self-follow
    if follower_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SELF_FOLLOW_NOT_ALLOWED",
                    "message": "You cannot follow yourself",
                }
            },
        )

    # Check if already following
    existing_follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.followee_id == user_id,
    ).first()

    if existing_follow:
        return FollowResponse(
            follower_id=existing_follow.follower_id,
            followee_id=existing_follow.followee_id,
            created_at=existing_follow.created_at,
            action="created",
        )

    follow = Follow(
        follower_id=follower_id,
        followee_id=user_id,
        created_at=utcnow(),
    )

    try:
        db.add(follow)
        db.flush()

        event_payload = {
            "follower_id": str(follow.follower_id),
            "followee_id": str(follow.followee_id),
            "action": "created",
            "ts": follow.created_at.isoformat(),
        }

        create_outbox_event(
            db=db,
            stream_name="app.social.follow.changed",
            event_type="follow.changed",
            payload=event_payload,
        )

        db.commit()
        db.refresh(follow)

        return FollowResponse(
            follower_id=follow.follower_id,
            followee_id=follow.followee_id,
            created_at=follow.created_at,
            action="created",
        )

    except IntegrityError:
        db.rollback()
        existing_follow = db.query(Follow).filter(
            Follow.follower_id == follower_id,
            Follow.followee_id == user_id,
        ).first()

        if existing_follow:
            return FollowResponse(
                follower_id=existing_follow.follower_id,
                followee_id=existing_follow.followee_id,
                created_at=existing_follow.created_at,
                action="created",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "FOLLOW_CREATION_FAILED",
                    "message": "Failed to create follow relationship",
                }
            },
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "FOLLOW_CREATION_FAILED",
                    "message": "Failed to create follow relationship",
                    "details": str(e),
                }
            },
        )


@router.delete("/follow/{user_id}", response_model=FollowResponse, status_code=status.HTTP_200_OK)
async def unfollow_user(
    user_id: UUID,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> FollowResponse:
    """Unfollow a user."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_USER_ID",
                    "message": "X-User-Id header is required",
                }
            },
        )

    try:
        follower_id = parse_user_id(x_user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": "X-User-Id must be a valid user identifier",
                }
            },
        )

    follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.followee_id == user_id,
    ).first()

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "FOLLOW_NOT_FOUND",
                    "message": "You are not following this user",
                }
            },
        )

    follow_data = {
        "follower_id": follow.follower_id,
        "followee_id": follow.followee_id,
        "created_at": follow.created_at,
    }
    timestamp = utcnow()

    try:
        db.delete(follow)
        db.flush()

        event_payload = {
            "follower_id": str(follow_data["follower_id"]),
            "followee_id": str(follow_data["followee_id"]),
            "action": "deleted",
            "ts": timestamp.isoformat(),
        }

        create_outbox_event(
            db=db,
            stream_name="app.social.follow.changed",
            event_type="follow.changed",
            payload=event_payload,
        )

        db.commit()

        return FollowResponse(
            follower_id=follow_data["follower_id"],
            followee_id=follow_data["followee_id"],
            created_at=follow_data["created_at"],
            action="deleted",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "UNFOLLOW_FAILED",
                    "message": "Failed to unfollow user",
                    "details": str(e),
                }
            },
        )


@router.get("/subscriptions", response_model=FollowListResponse)
async def get_subscriptions(
    limit: int = Query(20, ge=1, le=100, description="Number of subscriptions to return"),
    cursor: str | None = Query(None, description="Cursor for pagination (user_id:timestamp)"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> FollowListResponse:
    """Get list of users that the current user is following (subscriptions)."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_USER_ID",
                    "message": "X-User-Id header is required",
                }
            },
        )

    try:
        user_id = parse_user_id(x_user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": "X-User-Id must be a valid user identifier",
                }
            },
        )

    query_builder = db.query(Follow).filter(
        Follow.follower_id == user_id
    )

    if cursor:
        try:
            cursor_parts = cursor.split(":", 1)
            cursor_user_id = UUID(cursor_parts[0])
            cursor_timestamp = datetime.fromisoformat(cursor_parts[1])

            query_builder = query_builder.filter(
                or_(
                    Follow.created_at < cursor_timestamp,
                    and_(
                        Follow.created_at == cursor_timestamp,
                        Follow.followee_id < cursor_user_id,
                    ),
                )
            )
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_CURSOR",
                        "message": "Invalid cursor format",
                    }
                },
            )

    query_builder = query_builder.order_by(Follow.created_at.desc(), Follow.followee_id.desc())
    follows = query_builder.limit(limit + 1).all()

    has_more = len(follows) > limit
    if has_more:
        follows = follows[:limit]

    users = [
        FollowListItem(
            user_id=follow.followee_id,
            created_at=follow.created_at,
        )
        for follow in follows
    ]

    next_cursor = None
    if has_more and follows:
        last_follow = follows[-1]
        next_cursor = f"{last_follow.followee_id}:{last_follow.created_at.isoformat()}"

    return FollowListResponse(
        users=users,
        cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/followers", response_model=FollowListResponse)
async def get_followers(
    limit: int = Query(20, ge=1, le=100, description="Number of followers to return"),
    cursor: str | None = Query(None, description="Cursor for pagination (user_id:timestamp)"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> FollowListResponse:
    """Get list of users that are following the current user (followers)."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_USER_ID",
                    "message": "X-User-Id header is required",
                }
            },
        )

    try:
        user_id = parse_user_id(x_user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_USER_ID",
                    "message": "X-User-Id must be a valid user identifier",
                }
            },
        )

    query_builder = db.query(Follow).filter(
        Follow.followee_id == user_id
    )

    if cursor:
        try:
            cursor_parts = cursor.split(":", 1)
            cursor_user_id = UUID(cursor_parts[0])
            cursor_timestamp = datetime.fromisoformat(cursor_parts[1])

            query_builder = query_builder.filter(
                or_(
                    Follow.created_at < cursor_timestamp,
                    and_(
                        Follow.created_at == cursor_timestamp,
                        Follow.follower_id < cursor_user_id,
                    ),
                )
            )
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_CURSOR",
                        "message": "Invalid cursor format",
                    }
                },
            )

    query_builder = query_builder.order_by(Follow.created_at.desc(), Follow.follower_id.desc())
    follows = query_builder.limit(limit + 1).all()

    has_more = len(follows) > limit
    if has_more:
        follows = follows[:limit]

    users = [
        FollowListItem(
            user_id=follow.follower_id,
            created_at=follow.created_at,
        )
        for follow in follows
    ]

    next_cursor = None
    if has_more and follows:
        last_follow = follows[-1]
        next_cursor = f"{last_follow.follower_id}:{last_follow.created_at.isoformat()}"

    return FollowListResponse(
        users=users,
        cursor=next_cursor,
        has_more=has_more,
    )
