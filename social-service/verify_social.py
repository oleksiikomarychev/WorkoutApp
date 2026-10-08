import os
import sys
from datetime import datetime
from uuid import uuid4

from models import Post
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.getcwd())

# DB URL
DATABASE_URL = "postgresql://user:pass@localhost:5433/social"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def verify():
    print("Verifying Social Service Refactor...")
    
    # 1. Create Post with app_id and context_resource
    author_id = uuid4()
    app_id = "workout-app"
    context = {"type": "plan", "id": "123", "owner_id": str(uuid4())}
    
    post = Post(
        author_id=author_id,
        content="Test post with context",
        scope="public",
        app_id=app_id,
        context_resource=context,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    try:
        db.add(post)
        db.commit()
        print(f"SUCCESS: Created post with app_id={app_id} and context={context}")
    except Exception as e:
        print(f"FAILURE: Could not create post: {e}")
        return

    # 2. Verify persistence
    saved_post = db.query(Post).filter(Post.id == post.id).first()
    if saved_post.app_id == app_id and saved_post.context_resource == context:
        print("SUCCESS: Verified persistence of new fields")
    else:
        print(f"FAILURE: Fields mismatch. Got app_id={saved_post.app_id}, context={saved_post.context_resource}")

    # 3. Verify coach_only scope is rejected (by DB constraint)
    # Note: Pydantic validation is in API layer, here we test DB constraint
    bad_post = Post(
        author_id=uuid4(),
        content="Bad scope post",
        scope="coach_only",  # Should fail
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    try:
        db.add(bad_post)
        db.commit()
        print("FAILURE: DB accepted 'coach_only' scope (Constraint missing?)")
    except Exception as e:
        print(f"SUCCESS: DB rejected 'coach_only' scope as expected. Error: {e}")
        db.rollback()

if __name__ == "__main__":
    verify()
