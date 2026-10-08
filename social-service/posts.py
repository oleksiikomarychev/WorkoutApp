"""Posts API endpoints."""
from datetime import datetime
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from models import Comment, Follow, Post, Reaction
from outbox import create_outbox_event
from pydantic import BaseModel, Field, validator
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

router = APIRouter(prefix="/social/posts", tags=["posts"])


def firebase_uid_to_uuid(firebase_uid: str) -> UUID:
    """Convert Firebase UID to deterministic UUID using UUID5.
    
    Args:
        firebase_uid: Firebase user ID (string)
        
    Returns:
        UUID generated from Firebase UID
    """
    return uuid5(NAMESPACE_DNS, f"firebase:{firebase_uid}")


# Pydantic models for request/response
class CommentCreate(BaseModel):
    """Request model for creating a comment."""
    content: str = Field(..., min_length=1, max_length=2000)
    reply_to: UUID | None = Field(None, description="ID of parent comment for nested replies")
    
    @validator("content")
    def validate_content(cls, v):
        """Validate content is not empty after stripping."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class CommentResponse(BaseModel):
    """Response model for a comment."""
    id: UUID
    post_id: UUID
    author_id: UUID
    content: str
    reply_to: UUID | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReactionToggle(BaseModel):
    """Request model for toggling a reaction."""
    type: str = Field(..., min_length=1, max_length=50, description="Reaction type (like, love, fire, etc.)")
    
    @validator("type")
    def validate_type(cls, v):
        """Validate reaction type is not empty after stripping."""
        if not v.strip():
            raise ValueError("Reaction type cannot be empty")
        return v.strip()


class ReactionResponse(BaseModel):
    """Response model for a reaction."""
    id: UUID
    post_id: UUID | None
    comment_id: UUID | None
    user_id: UUID
    type: str
    created_at: datetime
    action: str  # "created" or "deleted"
    
    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    """Request model for creating a post."""
    content: str = Field(..., min_length=1, max_length=10000)
    scope: str = Field(..., pattern="^(public|followers|private)$")
    app_id: str | None = Field(None, description="ID of the application/tenant")
    context_resource: dict[str, Any] | None = Field(None, description="Context resource {type, id, owner_id}")
    attachments: list[dict] = Field(default_factory=list)
    
    @validator("content")
    def validate_content(cls, v):
        """Validate content is not empty after stripping."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class PostResponse(BaseModel):
    """Response model for a post."""
    id: UUID
    author_id: UUID
    content: str
    scope: str
    app_id: str | None
    context_resource: dict[str, Any] | None
    attachments: list[dict]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CommentSummary(BaseModel):
    """Summary of a comment for expanded responses."""
    id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReactionSummary(BaseModel):
    """Summary of reactions for expanded responses."""
    type: str
    count: int
    user_reacted: bool = False


@router.post("", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreate,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_app_id: str | None = Header(None, alias="X-App-Id"),
    db: Session = Depends(get_db)
):
    """Create a new post.
    
    This endpoint supports idempotency via the Idempotency-Key header.
    The idempotency is handled by the IdempotencyMiddleware.
    
    Args:
        post_data: Post creation data
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        Created post
        
    Raises:
        HTTPException: 401 if X-User-Id header is missing
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
    
    author_id = firebase_uid_to_uuid(x_user_id)

    # Create post
    post = Post(
        author_id=author_id,
        firebase_uid=x_user_id,  # Store original Firebase UID for author lookup
        content=post_data.content,
        scope=post_data.scope,
        app_id=post_data.app_id or x_app_id,
        context_resource=post_data.context_resource,
        attachments=post_data.attachments,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    try:
        # Add post to database
        db.add(post)
        db.flush()  # Flush to generate the post ID
        
        # Create outbox event in the same transaction
        event_payload = {
            "post_id": str(post.id),
            "author_id": str(post.author_id),
            "scope": post.scope,
            "app_id": post.app_id,
            "context_resource": post.context_resource,
            "content_preview": post.content[:100] if len(post.content) > 100 else post.content,
            "ts": post.created_at.isoformat()
        }
        
        create_outbox_event(
            db=db,
            stream_name="app.social.post.created",
            event_type="post.created",
            payload=event_payload
        )
        
        # Commit transaction
        db.commit()
        db.refresh(post)
        
        return post
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "POST_CREATION_FAILED",
                    "message": "Failed to create post",
                    "details": str(e)
                }
            }
        )



def check_post_access(post: Post, user_id: UUID, db: Session) -> bool:
    """Check if user has access to view the post based on scope.
    
    Args:
        post: Post to check access for
        user_id: User requesting access
        db: Database session
        
    Returns:
        True if user has access, False otherwise
    """
    # Author always has access
    if post.author_id == user_id:
        return True
    
    # Public posts are accessible to everyone
    if post.scope == "public":
        return True
    
    # Private posts only accessible to author
    if post.scope == "private":
        return False
    
    # Followers scope - check if user follows the author
    if post.scope == "followers":
        follow = db.query(Follow).filter(
            Follow.follower_id == user_id,
            Follow.followee_id == post.author_id
        ).first()
        return follow is not None
    
    # Coach_only scope removed
    if post.scope == "coach_only":
        return False
    
    return False


def filter_fields(data: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    """Filter response data to only include requested fields.
    
    Args:
        data: Full response data
        fields: List of field names to include (None = all fields)
        
    Returns:
        Filtered data dictionary
    """
    if not fields:
        return data
    
    return {k: v for k, v in data.items() if k in fields}


def expand_post_data(post: Post, expand: list[str] | None, user_id: UUID, db: Session) -> dict[str, Any]:
    """Expand post data with related entities.
    
    Args:
        post: Post to expand
        expand: List of entities to expand (comments, reactions)
        user_id: Current user ID
        db: Database session
        
    Returns:
        Expanded post data
    """
    data = {
        "id": post.id,
        "author_id": post.author_id,
        "firebase_uid": post.firebase_uid,  # Include Firebase UID for author lookup
        "content": post.content,
        "scope": post.scope,
        "app_id": post.app_id,
        "context_resource": post.context_resource,
        "attachments": post.attachments,
        "created_at": post.created_at,
        "updated_at": post.updated_at
    }
    
    if not expand:
        return data
    
    # Expand comments
    if "comments" in expand:
        comments = db.query(Comment).filter(
            Comment.post_id == post.id,
            Comment.deleted_at.is_(None)
        ).order_by(Comment.created_at.desc()).limit(10).all()
        
        data["comments"] = [
            {
                "id": c.id,
                "author_id": c.author_id,
                "content": c.content,
                "created_at": c.created_at
            }
            for c in comments
        ]
    
    # Expand reactions
    if "reactions" in expand:
        reactions = db.query(
            Reaction.type,
            func.count(Reaction.id).label("count")
        ).filter(
            Reaction.post_id == post.id
        ).group_by(Reaction.type).all()
        
        # Check which reactions the current user has made
        user_reactions = db.query(Reaction.type).filter(
            Reaction.post_id == post.id,
            Reaction.user_id == user_id
        ).all()
        user_reaction_types = {r.type for r in user_reactions}
        
        data["reactions"] = [
            {
                "type": r.type,
                "count": r.count,
                "user_reacted": r.type in user_reaction_types
            }
            for r in reactions
        ]
    
    return data


@router.get("/{post_id}", response_model=dict[str, Any])
async def get_post(
    post_id: UUID,
    fields: str | None = Query(None, description="Comma-separated list of fields to return"),
    expand: str | None = Query(None, description="Comma-separated list of entities to expand (comments, reactions)"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Get a post by ID.
    
    Access control is applied based on post scope:
    - public: accessible to everyone
    - followers: accessible to author and followers
    - private: accessible only to author
    - coach_only: accessible to author and coaches
    
    Args:
        post_id: Post UUID
        fields: Optional comma-separated list of fields to return
        expand: Optional comma-separated list of entities to expand
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        Post data (filtered by fields if specified)
        
    Raises:
        HTTPException: 401 if X-User-Id missing, 404 if post not found, 403 if no access
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
    
    user_id = firebase_uid_to_uuid(x_user_id)
    
    # Get post
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.deleted_at.is_(None)
    ).first()
    
    if not post:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "POST_NOT_FOUND",
                    "message": "Post not found"
                }
            }
        )
    
    # Check access
    if not check_post_access(post, user_id, db):
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You do not have access to this post"
                }
            }
        )
    
    # Parse fields and expand parameters
    fields_list = fields.split(",") if fields else None
    expand_list = expand.split(",") if expand else None
    
    # Build response
    post_data = expand_post_data(post, expand_list, user_id, db)
    
    # Filter fields if requested
    if fields_list:
        post_data = filter_fields(post_data, fields_list)
    
    return post_data



class FeedResponse(BaseModel):
    """Response model for feed endpoint."""
    posts: list[dict[str, Any]]
    cursor: str | None = None
    has_more: bool = False


@router.get("", response_model=FeedResponse)
async def get_feed(
    scope: str = Query("home", description="Feed scope: home, user, coach"),
    authors: str | None = Query(None, description="Comma-separated list of author UUIDs to filter by"),
    since: datetime | None = Query(None, description="Only return posts created after this timestamp"),
    tags: str | None = Query(None, description="Comma-separated list of tags to filter by (future feature)"),
    query: str | None = Query(None, description="Search query for post content"),
    limit: int = Query(20, ge=1, le=100, description="Number of posts to return"),
    cursor: str | None = Query(None, description="Cursor for pagination"),
    fields: str | None = Query(None, description="Comma-separated list of fields to return"),
    expand: str | None = Query(None, description="Comma-separated list of entities to expand"),
    sort: str = Query("created_at:desc", description="Sort order (created_at:desc or created_at:asc)"),
    app_id: str | None = Query(None, description="Filter by App ID"),
    context_type: str | None = Query(None, description="Filter by context resource type"),
    context_id: str | None = Query(None, description="Filter by context resource ID"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_app_id: str | None = Header(None, alias="X-App-Id"),
    db: Session = Depends(get_db)
):
    """Get feed of posts based on scope and filters.
    
    Feed scopes:
    - home: Posts from users the current user follows (respecting scope rules)
    - user: Posts from specific author(s) (requires authors parameter)
    - coach: Posts from coaches (future feature)
    
    Args:
        scope: Feed scope (home, user, coach)
        authors: Comma-separated author UUIDs (required for user scope)
        since: Filter posts created after this timestamp
        tags: Comma-separated tags (future feature)
        query: Search query for content
        limit: Number of posts to return (1-100)
        cursor: Pagination cursor (post_id:timestamp)
        fields: Comma-separated fields to return
        expand: Comma-separated entities to expand
        sort: Sort order (created_at:desc or created_at:asc)
        x_user_id: User ID from Gateway
        db: Database session
        
    Returns:
        Feed response with posts and pagination cursor
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
    
    user_id = firebase_uid_to_uuid(x_user_id)
    
    # Validate scope
    if scope not in ["home", "user", "coach"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_SCOPE",
                    "message": "Scope must be one of: home, user, coach"
                }
            }
        )
    
    # Parse sort parameter
    sort_parts = sort.split(":")
    if len(sort_parts) != 2 or sort_parts[0] != "created_at" or sort_parts[1] not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_SORT",
                    "message": "Sort must be in format 'created_at:asc' or 'created_at:desc'"
                }
            }
        )
    
    sort_order = sort_parts[1]
    
    # Build base query
    query_builder = db.query(Post).filter(Post.deleted_at.is_(None))
    
    # Filter by App ID (header or query param)
    target_app_id = app_id or x_app_id
    if target_app_id:
        query_builder = query_builder.filter(Post.app_id == target_app_id)
        
    # Filter by Context Resource
    if context_type:
        query_builder = query_builder.filter(Post.context_resource['type'].astext == context_type)
    if context_id:
        query_builder = query_builder.filter(Post.context_resource['id'].astext == context_id)
    
    # Apply scope filtering
    if scope == "home":
        # Get users that current user follows
        following_ids = db.query(Follow.followee_id).filter(
            Follow.follower_id == user_id
        ).subquery()
        
        # Include posts from followed users (public or followers scope) and own posts
        query_builder = query_builder.filter(
            or_(
                # Own posts (all scopes)
                Post.author_id == user_id,
                # Public posts from anyone
                and_(
                    Post.scope == "public"
                ),
                # Followers-only posts from people we follow
                and_(
                    Post.author_id.in_(following_ids),
                    Post.scope == "followers"
                )
            )
        )
    
    elif scope == "user":
        # User scope requires authors parameter
        if not authors:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "AUTHORS_REQUIRED",
                        "message": "authors parameter is required for user scope"
                    }
                }
            )
        
        # Parse author UUIDs
        try:
            author_uuids = [UUID(a.strip()) for a in authors.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_AUTHORS",
                        "message": "authors must be comma-separated valid UUIDs"
                    }
                }
            )
        
        # Filter by authors
        query_builder = query_builder.filter(Post.author_id.in_(author_uuids))
        
        # Apply scope rules for each author
        # For simplicity, we'll fetch all and filter in Python
        # In production, this should be optimized with proper SQL
        
    elif scope == "coach":
        # Coach scope - future feature
        # For now, return empty feed
        return FeedResponse(posts=[], cursor=None, has_more=False)
    
    # Apply additional filters
    if since:
        query_builder = query_builder.filter(Post.created_at > since)
    
    if query:
        # Simple content search (case-insensitive)
        query_builder = query_builder.filter(
            Post.content.ilike(f"%{query}%")
        )
    
    # Apply cursor pagination
    if cursor:
        try:
            # Cursor format: "post_id:timestamp"
            cursor_parts = cursor.split(":")
            cursor_id = UUID(cursor_parts[0])
            cursor_timestamp = datetime.fromisoformat(cursor_parts[1])
            
            if sort_order == "desc":
                query_builder = query_builder.filter(
                    or_(
                        Post.created_at < cursor_timestamp,
                        and_(
                            Post.created_at == cursor_timestamp,
                            Post.id < cursor_id
                        )
                    )
                )
            else:
                query_builder = query_builder.filter(
                    or_(
                        Post.created_at > cursor_timestamp,
                        and_(
                            Post.created_at == cursor_timestamp,
                            Post.id > cursor_id
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
    
    # Apply sorting
    if sort_order == "desc":
        query_builder = query_builder.order_by(Post.created_at.desc(), Post.id.desc())
    else:
        query_builder = query_builder.order_by(Post.created_at.asc(), Post.id.asc())
    
    # Fetch limit + 1 to check if there are more results
    posts = query_builder.limit(limit + 1).all()
    
    # Check if there are more results
    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]
    
    # Filter posts by access control (for user scope)
    if scope == "user":
        accessible_posts = []
        for post in posts:
            if check_post_access(post, user_id, db):
                accessible_posts.append(post)
        posts = accessible_posts
    
    # Parse fields and expand parameters
    fields_list = fields.split(",") if fields else None
    expand_list = expand.split(",") if expand else None
    
    # Build response
    post_data_list = []
    for post in posts:
        post_data = expand_post_data(post, expand_list, user_id, db)
        if fields_list:
            post_data = filter_fields(post_data, fields_list)
        post_data_list.append(post_data)
    
    # Generate next cursor
    next_cursor = None
    if has_more and posts:
        last_post = posts[-1]
        next_cursor = f"{last_post.id}:{last_post.created_at.isoformat()}"
    
    return FeedResponse(
        posts=post_data_list,
        cursor=next_cursor,
        has_more=has_more
    )



@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(
    post_id: UUID,
    comment_data: CommentCreate,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Create a comment on a post.
    
    This endpoint supports idempotency via the Idempotency-Key header.
    The idempotency is handled by the IdempotencyMiddleware.
    
    Args:
        post_id: Post UUID to comment on
        comment_data: Comment creation data
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        Created comment
        
    Raises:
        HTTPException: 401 if X-User-Id missing, 404 if post not found, 403 if no access
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
    
    author_id = firebase_uid_to_uuid(x_user_id)
    
    # Get post and check if it exists
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.deleted_at.is_(None)
    ).first()
    
    if not post:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "POST_NOT_FOUND",
                    "message": "Post not found"
                }
            }
        )
    
    # Check access to post (must be able to view post to comment on it)
    if not check_post_access(post, author_id, db):
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You do not have access to this post"
                }
            }
        )
    
    # If reply_to is specified, validate that the parent comment exists
    if comment_data.reply_to:
        parent_comment = db.query(Comment).filter(
            Comment.id == comment_data.reply_to,
            Comment.post_id == post_id,
            Comment.deleted_at.is_(None)
        ).first()
        
        if not parent_comment:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "PARENT_COMMENT_NOT_FOUND",
                        "message": "Parent comment not found or does not belong to this post"
                    }
                }
            )
    
    # Validate content length
    if len(comment_data.content) > 2000:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "CONTENT_TOO_LONG",
                    "message": "Comment content must not exceed 2000 characters"
                }
            }
        )
    
    # Create comment
    comment = Comment(
        post_id=post_id,
        author_id=author_id,
        content=comment_data.content,
        reply_to=comment_data.reply_to,
        created_at=datetime.utcnow()
    )
    
    try:
        # Add comment to database
        db.add(comment)
        db.flush()  # Flush to generate the comment ID
        
        # Create outbox event in the same transaction
        event_payload = {
            "comment_id": str(comment.id),
            "post_id": str(comment.post_id),
            "author_id": str(comment.author_id),
            "ts": comment.created_at.isoformat()
        }
        
        create_outbox_event(
            db=db,
            stream_name="app.social.comment.created",
            event_type="comment.created",
            payload=event_payload
        )
        
        # Commit transaction
        db.commit()
        db.refresh(comment)
        
        return comment
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "COMMENT_CREATION_FAILED",
                    "message": "Failed to create comment",
                    "details": str(e)
                }
            }
        )



class CommentsListResponse(BaseModel):
    """Response model for comments list."""
    comments: list[CommentResponse]
    cursor: str | None = None
    has_more: bool = False


@router.get("/{post_id}/comments", response_model=CommentsListResponse)
async def get_comments(
    post_id: UUID,
    limit: int = Query(20, ge=1, le=100, description="Number of comments to return"),
    cursor: str | None = Query(None, description="Cursor for pagination (comment_id:timestamp)"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Get comments for a post.
    
    Access control is applied based on the post's scope rules.
    Only users who can view the post can view its comments.
    
    Args:
        post_id: Post UUID
        limit: Number of comments to return (1-100)
        cursor: Pagination cursor (comment_id:timestamp)
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        List of comments with pagination cursor
        
    Raises:
        HTTPException: 401 if X-User-Id missing, 404 if post not found, 403 if no access
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
    
    user_id = firebase_uid_to_uuid(x_user_id)
    
    # Get post and check if it exists
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.deleted_at.is_(None)
    ).first()
    
    if not post:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "POST_NOT_FOUND",
                    "message": "Post not found"
                }
            }
        )
    
    # Check access to post (must be able to view post to see comments)
    if not check_post_access(post, user_id, db):
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You do not have access to this post"
                }
            }
        )
    
    # Build query for comments
    query_builder = db.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.deleted_at.is_(None)
    )
    
    # Apply cursor pagination
    if cursor:
        try:
            # Cursor format: "comment_id:timestamp"
            cursor_parts = cursor.split(":")
            cursor_id = UUID(cursor_parts[0])
            cursor_timestamp = datetime.fromisoformat(cursor_parts[1])
            
            # Paginate by created_at descending
            query_builder = query_builder.filter(
                or_(
                    Comment.created_at < cursor_timestamp,
                    and_(
                        Comment.created_at == cursor_timestamp,
                        Comment.id < cursor_id
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
    query_builder = query_builder.order_by(Comment.created_at.desc(), Comment.id.desc())
    
    # Fetch limit + 1 to check if there are more results
    comments = query_builder.limit(limit + 1).all()
    
    # Check if there are more results
    has_more = len(comments) > limit
    if has_more:
        comments = comments[:limit]
    
    # Generate next cursor
    next_cursor = None
    if has_more and comments:
        last_comment = comments[-1]
        next_cursor = f"{last_comment.id}:{last_comment.created_at.isoformat()}"
    
    return CommentsListResponse(
        comments=comments,
        cursor=next_cursor,
        has_more=has_more
    )



@router.post("/{post_id}/reactions", status_code=200)
async def toggle_reaction(
    post_id: UUID,
    reaction_data: ReactionToggle,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """Toggle a reaction on a post.
    
    If the user has already reacted with this type, the reaction is removed.
    If the user has not reacted with this type, a new reaction is created.
    
    This endpoint supports idempotency via the Idempotency-Key header.
    The idempotency is handled by the IdempotencyMiddleware.
    
    Args:
        post_id: Post UUID to react to
        reaction_data: Reaction toggle data
        x_user_id: User ID from Gateway (required)
        db: Database session
        
    Returns:
        Reaction response with action (created or deleted)
        
    Raises:
        HTTPException: 401 if X-User-Id missing, 404 if post not found, 403 if no access
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
    
    user_id = firebase_uid_to_uuid(x_user_id)
    
    # Get post and check if it exists
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.deleted_at.is_(None)
    ).first()
    
    if not post:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "POST_NOT_FOUND",
                    "message": "Post not found"
                }
            }
        )
    
    # Check access to post (must be able to view post to react to it)
    if not check_post_access(post, user_id, db):
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You do not have access to this post"
                }
            }
        )
    
    # Check if reaction already exists
    existing_reaction = db.query(Reaction).filter(
        Reaction.post_id == post_id,
        Reaction.user_id == user_id,
        Reaction.type == reaction_data.type
    ).first()
    
    try:
        if existing_reaction:
            # Delete existing reaction (toggle off)
            action = "deleted"
            reaction_id = existing_reaction.id
            reaction_type = existing_reaction.type
            timestamp = datetime.utcnow()
            
            db.delete(existing_reaction)
            db.flush()
            
            # Create outbox event for deletion
            event_payload = {
                "reaction_id": str(reaction_id),
                "post_id": str(post_id),
                "user_id": str(user_id),
                "type": reaction_type,
                "action": "deleted",
                "ts": timestamp.isoformat()
            }
            
            create_outbox_event(
                db=db,
                stream_name="app.social.reaction.toggled",
                event_type="reaction.toggled",
                payload=event_payload
            )
            
            db.commit()
            
            return {
                "id": reaction_id,
                "post_id": post_id,
                "comment_id": None,
                "user_id": user_id,
                "type": reaction_type,
                "created_at": timestamp,
                "action": action
            }
        else:
            # Create new reaction (toggle on)
            action = "created"
            reaction = Reaction(
                post_id=post_id,
                user_id=user_id,
                type=reaction_data.type,
                created_at=datetime.utcnow()
            )
            
            db.add(reaction)
            db.flush()  # Flush to generate the reaction ID
            
            # Create outbox event for creation
            event_payload = {
                "reaction_id": str(reaction.id),
                "post_id": str(reaction.post_id),
                "user_id": str(reaction.user_id),
                "type": reaction.type,
                "action": "created",
                "ts": reaction.created_at.isoformat()
            }
            
            create_outbox_event(
                db=db,
                stream_name="app.social.reaction.toggled",
                event_type="reaction.toggled",
                payload=event_payload
            )
            
            db.commit()
            db.refresh(reaction)
            
            return {
                "id": reaction.id,
                "post_id": reaction.post_id,
                "comment_id": reaction.comment_id,
                "user_id": reaction.user_id,
                "type": reaction.type,
                "created_at": reaction.created_at,
                "action": action
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "REACTION_TOGGLE_FAILED",
                    "message": "Failed to toggle reaction",
                    "details": str(e)
                }
            }
        )
