"""Simple test script for Posts API endpoints."""
import sys
from uuid import uuid4

# Add current directory to path
sys.path.insert(0, '.')

from config import settings
from database import get_db
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create test database session
engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_create_post():
    """Test creating a post."""
    print("\n=== Test: Create Post ===")
    
    user_id = str(uuid4())
    idempotency_key = str(uuid4())
    
    response = client.post(
        "/social/posts",
        json={
            "content": "This is a test post!",
            "scope": "public",
            "attachments": []
        },
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": idempotency_key
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    data = response.json()
    assert "id" in data
    assert data["content"] == "This is a test post!"
    assert data["scope"] == "public"
    
    post_id = data["id"]
    print(f"✓ Post created successfully: {post_id}")
    
    # Test idempotency - same request should return same result
    print("\n=== Test: Idempotency ===")
    response2 = client.post(
        "/social/posts",
        json={
            "content": "This is a test post!",
            "scope": "public",
            "attachments": []
        },
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": idempotency_key
        }
    )
    
    print(f"Status: {response2.status_code}")
    print(f"Response: {response2.json()}")
    
    assert response2.status_code == 201
    assert response2.json()["id"] == post_id
    print("✓ Idempotency works correctly")
    
    return post_id, user_id


def test_get_post(post_id: str, user_id: str):
    """Test getting a post."""
    print("\n=== Test: Get Post ===")
    
    response = client.get(
        f"/social/posts/{post_id}",
        headers={"X-User-Id": user_id}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == post_id
    assert data["content"] == "This is a test post!"
    print("✓ Post retrieved successfully")
    
    # Test with fields parameter
    print("\n=== Test: Get Post with Fields ===")
    response = client.get(
        f"/social/posts/{post_id}?fields=id,content,scope",
        headers={"X-User-Id": user_id}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "content" in data
    assert "scope" in data
    assert "created_at" not in data  # Should be filtered out
    print("✓ Fields filtering works correctly")


def test_get_feed(user_id: str):
    """Test getting feed."""
    print("\n=== Test: Get Feed ===")
    
    response = client.get(
        "/social/posts?scope=home&limit=10",
        headers={"X-User-Id": user_id}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert "posts" in data
    assert "cursor" in data
    assert "has_more" in data
    assert isinstance(data["posts"], list)
    print(f"✓ Feed retrieved successfully ({len(data['posts'])} posts)")


def test_scope_validation():
    """Test scope validation."""
    print("\n=== Test: Scope Validation ===")
    
    user_id = str(uuid4())
    
    # Test invalid scope
    response = client.post(
        "/social/posts",
        json={
            "content": "Test post",
            "scope": "invalid_scope",
            "attachments": []
        },
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 422  # Validation error
    print("✓ Invalid scope rejected correctly")


def test_content_length_validation():
    """Test content length validation."""
    print("\n=== Test: Content Length Validation ===")
    
    user_id = str(uuid4())
    
    # Test content too long
    long_content = "x" * 10001
    response = client.post(
        "/social/posts",
        json={
            "content": long_content,
            "scope": "public",
            "attachments": []
        },
        headers={
            "X-User-Id": user_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    print(f"Status: {response.status_code}")
    
    assert response.status_code == 422  # Validation error
    print("✓ Content length validation works correctly")


def test_access_control():
    """Test access control for private posts."""
    print("\n=== Test: Access Control ===")
    
    # Create a private post
    author_id = str(uuid4())
    response = client.post(
        "/social/posts",
        json={
            "content": "Private post",
            "scope": "private",
            "attachments": []
        },
        headers={
            "X-User-Id": author_id,
            "Idempotency-Key": str(uuid4())
        }
    )
    
    assert response.status_code == 201
    post_id = response.json()["id"]
    print(f"Private post created: {post_id}")
    
    # Try to access as different user
    other_user_id = str(uuid4())
    response = client.get(
        f"/social/posts/{post_id}",
        headers={"X-User-Id": other_user_id}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 403  # Access denied
    print("✓ Access control works correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Posts API Implementation")
    print("=" * 60)
    
    try:
        # Test basic CRUD
        post_id, user_id = test_create_post()
        test_get_post(post_id, user_id)
        test_get_feed(user_id)
        
        # Test validations
        test_scope_validation()
        test_content_length_validation()
        test_access_control()
        
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


if __name__ == "__main__":
    main()
