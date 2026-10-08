"""Test script to verify idempotency implementation."""
import sys
from datetime import datetime, timedelta
from uuid import uuid4

from idempotency import cleanup_expired_idempotency_keys, get_idempotency_record
from models import Base, IdempotencyKey
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_idempotency_model():
    """Test IdempotencyKey model creation and retrieval."""
    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Test 1: Create idempotency record
        print("Test 1: Creating idempotency record...")
        key = "test-key-123"
        user_id = uuid4()
        record = IdempotencyKey(
            key=key,
            service="social-service",
            endpoint="/social/posts",
            user_id=user_id,
            response_status=201,
            response_body={"id": str(uuid4()), "content": "Test post"},
            created_at=datetime.utcnow()
        )
        db.add(record)
        db.commit()
        print("✓ Idempotency record created successfully")
        
        # Test 2: Retrieve idempotency record
        print("\nTest 2: Retrieving idempotency record...")
        retrieved = get_idempotency_record(db, key)
        assert retrieved is not None, "Record should exist"
        assert retrieved.key == key, "Key should match"
        assert retrieved.user_id == user_id, "User ID should match"
        assert retrieved.response_status == 201, "Status should match"
        print(f"✓ Retrieved record: {retrieved}")
        
        # Test 3: Test cleanup of expired keys
        print("\nTest 3: Testing cleanup of expired keys...")
        # Create an old record
        old_key = "old-key-456"
        old_record = IdempotencyKey(
            key=old_key,
            service="social-service",
            endpoint="/social/posts",
            user_id=uuid4(),
            response_status=201,
            response_body={"id": str(uuid4())},
            created_at=datetime.utcnow() - timedelta(hours=25)  # Older than 24 hours
        )
        db.add(old_record)
        db.commit()
        
        # Verify both records exist
        count_before = db.query(IdempotencyKey).count()
        print(f"  Records before cleanup: {count_before}")
        assert count_before == 2, "Should have 2 records"
        
        # Run cleanup
        deleted = cleanup_expired_idempotency_keys(db)
        print(f"  Deleted {deleted} expired record(s)")
        
        # Verify old record was deleted
        count_after = db.query(IdempotencyKey).count()
        print(f"  Records after cleanup: {count_after}")
        assert count_after == 1, "Should have 1 record left"
        assert get_idempotency_record(db, key) is not None, "Recent record should still exist"
        assert get_idempotency_record(db, old_key) is None, "Old record should be deleted"
        print("✓ Cleanup works correctly")
        
        # Test 4: Verify model constraints
        print("\nTest 4: Verifying model structure...")
        assert hasattr(IdempotencyKey, 'key'), "Should have key field"
        assert hasattr(IdempotencyKey, 'service'), "Should have service field"
        assert hasattr(IdempotencyKey, 'endpoint'), "Should have endpoint field"
        assert hasattr(IdempotencyKey, 'user_id'), "Should have user_id field"
        assert hasattr(IdempotencyKey, 'response_status'), "Should have response_status field"
        assert hasattr(IdempotencyKey, 'response_body'), "Should have response_body field"
        assert hasattr(IdempotencyKey, 'created_at'), "Should have created_at field"
        print("✓ All required fields present")
        
        print("\n" + "="*50)
        print("All tests passed! ✓")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_idempotency_model()
    sys.exit(0 if success else 1)
