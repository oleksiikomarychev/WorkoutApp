import os
import sys
from datetime import datetime
from uuid import uuid4

from models import Channel, Message
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.getcwd())

# DB URL
DATABASE_URL = "postgresql://user:pass@localhost:5434/messaging"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def verify():
    print("Verifying Messaging Service Refactor...")
    
    app_id = "workout-app"
    context = {"type": "workout", "id": "456", "owner_id": str(uuid4())}
    
    # 1. Create Channel
    channel_id = uuid4()
    channel = Channel(
        id=channel_id,
        type="group",
        name="Workout Chat",
        app_id=app_id,
        context_resource=context,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    try:
        db.add(channel)
        db.commit()
        print(f"SUCCESS: Created channel with app_id={app_id}")
    except Exception as e:
        print(f"FAILURE: Could not create channel: {e}")
        return

    # 2. Create Message
    message = Message(
        id=uuid4(),
        channel_id=channel_id,
        sender_id=uuid4(),
        content="Hello workout!",
        kind="text",
        app_id=app_id,
        context_resource=context,
        created_at=datetime.utcnow()
    )
    
    try:
        db.add(message)
        db.commit()
        print(f"SUCCESS: Created message with app_id={app_id}")
    except Exception as e:
        print(f"FAILURE: Could not create message: {e}")
        return

    # 3. Verify persistence
    saved_channel = db.query(Channel).filter(Channel.id == channel_id).first()
    saved_message = db.query(Message).filter(Message.id == message.id).first()
    
    if saved_channel.app_id == app_id and saved_channel.context_resource == context:
        print("SUCCESS: Verified Channel persistence")
    else:
        print(f"FAILURE: Channel mismatch. Got {saved_channel.app_id}, {saved_channel.context_resource}")
        
    if saved_message.app_id == app_id and saved_message.context_resource == context:
        print("SUCCESS: Verified Message persistence")
    else:
        print(f"FAILURE: Message mismatch. Got {saved_message.app_id}, {saved_message.context_resource}")

if __name__ == "__main__":
    verify()
