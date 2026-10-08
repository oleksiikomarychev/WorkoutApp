"""Comprehensive test for feed generation functionality."""
import sys
from datetime import datetime, timedelta
from uuid import uuid4

sys.path.insert(0, '.')

from config import settings
from database import get_db
from fastapi.testclient import TestClient
from main import app
from models import Follow, Post
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


def setup_test_data():
    """Create test users, follows, and posts."""
    print("\n=== Setting up test data ===")
    
    db = TestingSessionLocal()
    
    # Create test users
    user1_id = uuid4()
    user2_id = uuid4()
    user3_id = uuid4()
    
    print(f"User 1: {user1_id}")
    print(f"User 2: {user2_id}")
    print(f"User 3: {user3_id}")
    
    # User 1 follows User 2
    follow = Follow(follower_id=user1_id, followee_id=user2_id)
    db.add(follow)
    
    # Create posts with different scopes and timestamps
    now = datetime.utcnow()
    
    # User 1's posts
    post1 = Post(
        author_id=user1_id,
        content="User 1 public post",
        scope="public",
        attachments=[],
        created_at=now - timedelta(minutes=10)
    )
    post2 = Post(
        author_id=user1_id,
        content="User 1 private post",
        scope="private",
        attachments=[],
        created_at=now - timedelta(minutes=9)
    )
    
    # User 2's posts (followed by User 1)
    post3 = Post(
        author_id=user2_id,
        content="User 2 public post with keyword search",
        scope="public",
        attachments=[],
        created_at=now - timedelta(minutes=8)
    )
    post4 = Post(
        author_id=user2_id,
        content="User 2 followers only post",
        scope="followers",
        attachments=[],
        created_at=now - timedelta(minutes=7)
    )
    
    # User 3's posts (not followed by User 1)
    post5 = Post(
        author_id=user3_id,
        content="User 3 public post",
        scope="public",
        attachments=[],
        created_at=now - timedelta(minutes=6)
    )
    post6 = Post(
        author_id=user3_id,
        content="User 3 followers only post",
        scope="followers",
        attachments=[],
        created_at=now - timedelta(minutes=5)
    )
    
    db.add_all([post1, post2, post3, post4, post5, post6])
    db.commit()
    
    print("✓ Created 6 posts and 1 follow relationship")
    
    db.close()
    
    return {
        "user1_id": str(user1_id),
        "user2_id": str(user2_id),
        "user3_id": str(user3_id),
        "posts": {
            "post1": str(post1.id),
            "post2": str(post2.id),
            "post3": str(post3.id),
            "post4": str(post4.id),
            "post5": str(post5.id),
            "post6": str(post6.id),
        }
    }


def test_home_feed(test_data):
    """Test home feed scope."""
    print("\n=== Test: Home Feed ===")
    
    user1_id = test_data["user1_id"]
    
    response = client.get(
        "/social/posts?scope=home&limit=20",
        headers={"X-User-Id": user1_id}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Posts returned: {len(data['posts'])}")
    
    assert response.status_code == 200
    assert "posts" in data
    assert "cursor" in data
    assert "has_more" in data
    
    # User 1 should see:
    # - Their own posts (post1, post2)
    # - User 2's public post (post3)
    # - User 2's followers post (post4) - because User 1 follows User 2
    # - User 3's public post (post5)
    # - NOT User 3's followers post (post6) - because User 1 doesn't follow User 3
    
    post_contents = [p["content"] for p in data["posts"]]
    print(f"Post contents: {post_contents}")
    
    assert "User 1 public post" in post_contents
    assert "User 1 private post" in post_contents
    assert "User 2 public post with keyword search" in post_contents
    assert "User 2 followers only post" in post_contents
    assert "User 3 public post" in post_contents
    assert "User 3 followers only post" not in post_contents
    
    print("✓ Home feed filtering works correctly")


def test_user_feed(test_data):
    """Test user feed scope."""
    print("\n=== Test: User Feed ===")
    
    user1_id = test_data["user1_id"]
    user2_id = test_data["user2_id"]
    
    # Get User 2's posts as User 1
    response = client.get(
        f"/social/posts?scope=user&authors={user2_id}&limit=20",
        headers={"X-User-Id": user1_id}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Posts returned: {len(data['posts'])}")
    
    assert response.status_code == 200
    
    # User 1 should see User 2's public and followers posts
    post_contents = [p["content"] for p in data["posts"]]
    print(f"Post contents: {post_contents}")
    
    assert "User 2 public post with keyword search" in post_contents
    assert "User 2 followers only post" in post_contents
    
    print("✓ User feed filtering works correctly")


def test_user_feed_without_authors():
    """Test user feed requires authors parameter."""
    print("\n=== Test: User Feed Without Authors ===")
    
    user_id = str(uuid4())
    
    response = client.get(
        "/social/posts?scope=user&limit=20",
        headers={"X-User-Id": user_id}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 400
    assert "AUTHORS_REQUIRED" in response.json()["error"]["code"]
    
    print("✓ User feed validation works correctly")


def test_feed_with_since_filter(test_data):
    """Test feed with since timestamp filter."""
    print("\n=== Test: Feed with Since Filter ===")
    
    user1_id = test_data["user1_id"]
    
    # Get posts from last 7 minutes
    since_time = (datetime.utcnow() - timedelta(minutes=7)).isoformat()
    
    response = client.get(
        f"/social/posts?scope=home&since={since_time}&limit=20",
        headers={"X-User-Id": user1_id}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Posts returned: {len(data['posts'])}")
    
    assert response.status_code == 200
    
    # Should only get posts newer than 7 minutes ago
    # That's post4, post5, post6 (but post6 is filtered by scope)
    assert len(data["posts"]) >= 2
    
    print("✓ Since filter works correctly")


def test_feed_with_query_filter(test_data):
    """Test feed with content search query."""
    print("\n=== Test: Feed with Query Filter ===")
    
    user1_id = test_data["user1_id"]
    
    response = client.get(
        "/social/posts?scope=home&query=keyword search&limit=20",
        headers={"X-User-Id": user1_id}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Posts returned: {len(data['posts'])}")
    
    assert response.status_code == 200
    assert len(data["posts"]) >= 1
    
    # Should find the post with "keyword search" in content
    post_contents = [p["content"] for p in data["posts"]]
    assert any("keyword search" in content for content in post_contents)
    
    print("✓ Query filter works correctly")


def test_feed_pagination(test_data):
    """Test cursor-based pagination."""
    print("\n=== Test: Feed Pagination ===")
    
    user1_id = test_data["user1_id"]
    
    # Get first page with limit 2
    response1 = client.get(
        "/social/posts?scope=home&limit=2&sort=created_at:desc",
        headers={"X-User-Id": user1_id}
    )
    
    print(f"Page 1 Status: {response1.status_code}")
    data1 = response1.json()
    print(f"Page 1 Posts: {len(data1['posts'])}")
    print(f"Has more: {data1['has_more']}")
    print(f"Cursor: {data1['cursor']}")
    
    assert response1.status_code == 200
    assert len(data1["posts"]) == 2
    assert data1["has_more"] is True
    assert data1["cursor"] is not None
    
    # Get second page using cursor
    response2 = client.get(
        f"/social/posts?scope=home&limit=2&cursor={data1['cursor']}&sort=created_at:desc",
        headers={"X-User-Id": user1_id}
    )
    
    print(f"Page 2 Status: {response2.status_code}")
    data2 = response2.json()
    print(f"Page 2 Posts: {len(data2['posts'])}")
    
    assert response2.status_code == 200
    assert len(data2["posts"]) >= 1
    
    # Ensure no overlap between pages
    page1_ids = {p["id"] for p in data1["posts"]}
    page2_ids = {p["id"] for p in data2["posts"]}
    assert len(page1_ids & page2_ids) == 0
    
    print("✓ Pagination works correctly")


def test_feed_with_fields_parameter(test_data):
    """Test fields parameter for partial responses."""
    print("\n=== Test: Feed with Fields Parameter ===")
    
    user1_id = test_data["user1_id"]
    
    response = client.get(
        "/social/posts?scope=home&fields=id,content,scope&limit=5",
        headers={"X-User-Id": user1_id}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    assert response.status_code == 200
    assert len(data["posts"]) > 0
    
    # Check that only requested fields are present
    first_post = data["posts"][0]
    print(f"First post keys: {first_post.keys()}")
    
    assert "id" in first_post
    assert "content" in first_post
    assert "scope" in first_post
    assert "created_at" not in first_post
    assert "updated_at" not in first_post
    
    print("✓ Fields parameter works correctly")


def test_feed_with_expand_parameter(test_data):
    """Test expand parameter for nested data."""
    print("\n=== Test: Feed with Expand Parameter ===")
    
    user1_id = test_data["user1_id"]
    
    response = client.get(
        "/social/posts?scope=home&expand=comments,reactions&limit=5",
        headers={"X-User-Id": user1_id}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    assert response.status_code == 200
    assert len(data["posts"]) > 0
    
    # Check that expanded fields are present
    first_post = data["posts"][0]
    print(f"First post keys: {first_post.keys()}")
    
    assert "comments" in first_post
    assert "reactions" in first_post
    assert isinstance(first_post["comments"], list)
    assert isinstance(first_post["reactions"], list)
    
    print("✓ Expand parameter works correctly")


def test_feed_sort_order(test_data):
    """Test sort parameter."""
    print("\n=== Test: Feed Sort Order ===")
    
    user1_id = test_data["user1_id"]
    
    # Test descending order (newest first)
    response_desc = client.get(
        "/social/posts?scope=home&sort=created_at:desc&limit=10",
        headers={"X-User-Id": user1_id}
    )
    
    data_desc = response_desc.json()
    print(f"Desc order posts: {len(data_desc['posts'])}")
    
    # Test ascending order (oldest first)
    response_asc = client.get(
        "/social/posts?scope=home&sort=created_at:asc&limit=10",
        headers={"X-User-Id": user1_id}
    )
    
    data_asc = response_asc.json()
    print(f"Asc order posts: {len(data_asc['posts'])}")
    
    assert response_desc.status_code == 200
    assert response_asc.status_code == 200
    
    # Verify order is different
    if len(data_desc["posts"]) > 1 and len(data_asc["posts"]) > 1:
        first_desc = data_desc["posts"][0]["id"]
        first_asc = data_asc["posts"][0]["id"]
        assert first_desc != first_asc
    
    print("✓ Sort order works correctly")


def test_invalid_scope():
    """Test invalid scope parameter."""
    print("\n=== Test: Invalid Scope ===")
    
    user_id = str(uuid4())
    
    response = client.get(
        "/social/posts?scope=invalid&limit=10",
        headers={"X-User-Id": user_id}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 400
    assert "INVALID_SCOPE" in response.json()["error"]["code"]
    
    print("✓ Invalid scope validation works correctly")


def test_invalid_sort():
    """Test invalid sort parameter."""
    print("\n=== Test: Invalid Sort ===")
    
    user_id = str(uuid4())
    
    response = client.get(
        "/social/posts?scope=home&sort=invalid&limit=10",
        headers={"X-User-Id": user_id}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 400
    assert "INVALID_SORT" in response.json()["error"]["code"]
    
    print("✓ Invalid sort validation works correctly")


def main():
    """Run all feed tests."""
    print("=" * 60)
    print("Testing Feed Generation Implementation")
    print("=" * 60)
    
    try:
        # Setup test data
        test_data = setup_test_data()
        
        # Run tests
        test_home_feed(test_data)
        test_user_feed(test_data)
        test_user_feed_without_authors()
        test_feed_with_since_filter(test_data)
        test_feed_with_query_filter(test_data)
        test_feed_pagination(test_data)
        test_feed_with_fields_parameter(test_data)
        test_feed_with_expand_parameter(test_data)
        test_feed_sort_order(test_data)
        test_invalid_scope()
        test_invalid_sort()
        
        print("\n" + "=" * 60)
        print("✓ All feed tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
