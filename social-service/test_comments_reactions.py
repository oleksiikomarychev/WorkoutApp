"""
Manual test script for comments and reactions API.
This script verifies the implementation of task 5.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uuid import uuid4

from database import Base, get_db
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_comments_reactions.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_create_comment():
    """Test creating a comment on a post."""
    print("\n=== Test 1: Create Comment ===")
    
    # Create a test post first
    user_id = str(uuid4())
    post_data = {
        "content": "Test post for comments",
        "scope": "public",
        "attachments": []
    }
    
    response = client.post(
        "/social/posts",
        json=post_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 201, f"Failed to create post: {response.json()}"
    post_id = response.json()["id"]
    print(f"✓ Created test post: {post_id}")
    
    # Create a comment
    comment_data = {
        "content": "This is a test comment"
    }
    
    response = client.post(
        f"/social/posts/{post_id}/comments",
        json=comment_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 201, f"Failed to create comment: {response.json()}"
    comment = response.json()
    assert comment["content"] == "This is a test comment"
    assert comment["post_id"] == post_id
    assert comment["author_id"] == user_id
    print(f"✓ Created comment: {comment['id']}")
    
    return post_id, comment["id"], user_id


def test_create_nested_comment():
    """Test creating a nested comment (reply)."""
    print("\n=== Test 2: Create Nested Comment ===")
    
    # Create post and parent comment
    user_id = str(uuid4())
    post_data = {
        "content": "Test post for nested comments",
        "scope": "public",
        "attachments": []
    }
    
    response = client.post(
        "/social/posts",
        json=post_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    post_id = response.json()["id"]
    
    # Create parent comment
    parent_comment_data = {
        "content": "Parent comment"
    }
    
    response = client.post(
        f"/social/posts/{post_id}/comments",
        json=parent_comment_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    parent_comment_id = response.json()["id"]
    print(f"✓ Created parent comment: {parent_comment_id}")
    
    # Create nested comment
    nested_comment_data = {
        "content": "This is a reply",
        "reply_to": parent_comment_id
    }
    
    response = client.post(
        f"/social/posts/{post_id}/comments",
        json=nested_comment_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 201, f"Failed to create nested comment: {response.json()}"
    nested_comment = response.json()
    assert nested_comment["reply_to"] == parent_comment_id
    print(f"✓ Created nested comment: {nested_comment['id']}")


def test_get_comments():
    """Test getting comments for a post."""
    print("\n=== Test 3: Get Comments ===")
    
    # Create post with multiple comments
    user_id = str(uuid4())
    post_data = {
        "content": "Test post for getting comments",
        "scope": "public",
        "attachments": []
    }
    
    response = client.post(
        "/social/posts",
        json=post_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    post_id = response.json()["id"]
    
    # Create 3 comments
    for i in range(3):
        comment_data = {
            "content": f"Comment {i+1}"
        }
        client.post(
            f"/social/posts/{post_id}/comments",
            json=comment_data,
            headers={
                "X-User-Id": user_id,
                "Idempotency-Key": str(uuid4())
            }
        )
    
    print(f"✓ Created 3 comments on post {post_id}")
    
    # Get comments
    response = client.get(
        f"/social/posts/{post_id}/comments",
        headers={"X-User-Id": user_id}
    )
    
    assert response.status_code == 200, f"Failed to get comments: {response.json()}"
    result = response.json()
    assert len(result["comments"]) == 3
    print(f"✓ Retrieved {len(result['comments'])} comments")


def test_toggle_reaction():
    """Test toggling reactions on a post."""
    print("\n=== Test 4: Toggle Reaction ===")
    
    # Create a test post
    user_id = str(uuid4())
    post_data = {
        "content": "Test post for reactions",
        "scope": "public",
        "attachments": []
    }
    
    response = client.post(
        "/social/posts",
        json=post_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    post_id = response.json()["id"]
    print(f"✓ Created test post: {post_id}")
    
    # Add a reaction
    reaction_data = {
        "type": "like"
    }
    
    response = client.post(
        f"/social/posts/{post_id}/reactions",
        json=reaction_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 200, f"Failed to add reaction: {response.json()}"
    result = response.json()
    assert result["action"] == "created"
    assert result["type"] == "like"
    reaction_id = result["id"]
    print(f"✓ Added 'like' reaction: {reaction_id}")
    
    # Toggle off the reaction
    response = client.post(
        f"/social/posts/{post_id}/reactions",
        json=reaction_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 200, f"Failed to remove reaction: {response.json()}"
    result = response.json()
    assert result["action"] == "deleted"
    print("✓ Removed 'like' reaction")
    
    # Toggle on again
    response = client.post(
        f"/social/posts/{post_id}/reactions",
        json=reaction_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 200, f"Failed to re-add reaction: {response.json()}"
    result = response.json()
    assert result["action"] == "created"
    print("✓ Re-added 'like' reaction")


def test_comment_access_control():
    """Test that comments respect post access control."""
    print("\n=== Test 5: Comment Access Control ===")
    
    # Create a private post
    user1_id = str(uuid4())
    user2_id = str(uuid4())
    
    post_data = {
        "content": "Private post",
        "scope": "private",
        "attachments": []
    }
    
    response = client.post(
        "/social/posts",
        json=post_data,
        headers={
            "X-User-Id": user1_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    post_id = response.json()["id"]
    print(f"✓ Created private post: {post_id}")
    
    # Try to comment as different user (should fail)
    comment_data = {
        "content": "Trying to comment on private post"
    }
    
    response = client.post(
        f"/social/posts/{post_id}/comments",
        json=comment_data,
        headers={
            "X-User-Id": user2_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 403, f"Should not allow comment on private post: {response.json()}"
    print("✓ Correctly denied access to comment on private post")
    
    # Try to get comments as different user (should fail)
    response = client.get(
        f"/social/posts/{post_id}/comments",
        headers={"X-User-Id": user2_id}
    )
    
    assert response.status_code == 403, f"Should not allow viewing comments on private post: {response.json()}"
    print("✓ Correctly denied access to view comments on private post")


def test_content_validation():
    """Test content length validation."""
    print("\n=== Test 6: Content Validation ===")
    
    # Create a test post
    user_id = str(uuid4())
    post_data = {
        "content": "Test post",
        "scope": "public",
        "attachments": []
    }
    
    response = client.post(
        "/social/posts",
        json=post_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    post_id = response.json()["id"]
    
    # Try to create comment with content > 2000 characters
    long_content = "x" * 2001
    comment_data = {
        "content": long_content
    }
    
    response = client.post(
        f"/social/posts/{post_id}/comments",
        json=comment_data,
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 422, f"Should reject comment with content > 2000 chars: {response.json()}"
    print("✓ Correctly rejected comment with content > 2000 characters")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Comments and Reactions API Implementation")
    print("=" * 60)
    
    try:
        test_create_comment()
        test_create_nested_comment()
        test_get_comments()
        test_toggle_reaction()
        test_comment_access_control()
        test_content_validation()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        import os
        if os.path.exists("test_comments_reactions.db"):
            os.remove("test_comments_reactions.db")
