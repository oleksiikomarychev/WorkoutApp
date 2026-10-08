"""Redis Streams publisher for outbox events."""
import asyncio
import json
import logging
from datetime import datetime

import redis.asyncio as redis
from config import settings
from database import SessionLocal
from outbox import get_unpublished_events, increment_retry_count, mark_event_published
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RedisStreamsPublisher:
    """Background worker for publishing outbox events to Redis Streams."""
    
    def __init__(self, redis_url: str, batch_size: int = 100, poll_interval: int = 1):
        """Initialize the publisher.
        
        Args:
            redis_url: Redis connection URL
            batch_size: Number of events to process per batch
            poll_interval: Seconds to wait between polling cycles
        """
        self.redis_url = redis_url
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.redis_client: redis.Redis | None = None
        self.running = False
        
    async def connect(self):
        """Connect to Redis."""
        self.redis_client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Connected to Redis at {self.redis_url}")
        
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
            
    async def publish_event(self, event) -> bool:
        """Publish a single event to Redis Streams.
        
        Args:
            event: OutboxEvent instance
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.redis_client:
            logger.error("Redis client not connected")
            return False
            
        try:
            # Prepare event data for Redis Streams
            event_data = {
                "event_id": str(event.id),
                "event_type": event.event_type,
                "timestamp": event.created_at.isoformat(),
                **event.payload  # Unpack payload fields
            }
            
            # Convert all values to strings for Redis
            redis_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                         for k, v in event_data.items()}
            
            # Publish to Redis Stream using XADD
            message_id = await self.redis_client.xadd(
                event.stream_name,
                redis_data
            )
            
            logger.info(
                f"Published event {event.id} to stream {event.stream_name} "
                f"with message_id {message_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to publish event {event.id} to stream {event.stream_name}: {e}",
                exc_info=True
            )
            return False
            
    def calculate_retry_delay(self, retry_count: int) -> int:
        """Calculate exponential backoff delay.
        
        Args:
            retry_count: Number of previous retry attempts
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: 1m, 5m, 15m, 1h, 3h
        delays = [60, 300, 900, 3600, 10800]
        
        if retry_count >= len(delays):
            return delays[-1]  # Max delay
            
        return delays[retry_count]
        
    def should_retry_event(self, event) -> bool:
        """Check if event should be retried based on retry count and timing.
        
        Args:
            event: OutboxEvent instance
            
        Returns:
            True if event should be retried now
        """
        max_retries = 5
        
        # Don't retry if max retries reached
        if event.retry_count >= max_retries:
            logger.warning(
                f"Event {event.id} reached max retries ({max_retries}), skipping"
            )
            return False
            
        # For first attempt, always try
        if event.retry_count == 0:
            return True
            
        # Calculate when next retry should happen
        delay = self.calculate_retry_delay(event.retry_count - 1)
        next_retry_time = event.created_at.timestamp() + sum(
            self.calculate_retry_delay(i) for i in range(event.retry_count)
        )
        
        current_time = datetime.utcnow().timestamp()
        
        # Only retry if enough time has passed
        should_retry = current_time >= next_retry_time
        
        if not should_retry:
            logger.debug(
                f"Event {event.id} not ready for retry yet "
                f"(retry_count={event.retry_count}, next_retry in {int(next_retry_time - current_time)}s)"
            )
            
        return should_retry
        
    async def process_batch(self):
        """Process a batch of unpublished events."""
        db: Session = SessionLocal()
        
        try:
            # Get unpublished events
            events = get_unpublished_events(db, limit=self.batch_size)
            
            if not events:
                return
                
            logger.info(f"Processing batch of {len(events)} unpublished events")
            
            for event in events:
                # Check if event should be retried
                if not self.should_retry_event(event):
                    continue
                    
                # Try to publish
                success = await self.publish_event(event)
                
                if success:
                    # Mark as published
                    mark_event_published(db, str(event.id))
                    logger.info(f"Event {event.id} marked as published")
                else:
                    # Increment retry count
                    increment_retry_count(db, str(event.id))
                    logger.warning(
                        f"Event {event.id} failed to publish, "
                        f"retry_count now {event.retry_count + 1}"
                    )
                    
        except Exception as e:
            logger.error(f"Error processing batch: {e}", exc_info=True)
        finally:
            db.close()
            
    async def run(self):
        """Run the publisher worker loop."""
        self.running = True
        logger.info("Starting Redis Streams publisher worker")
        
        await self.connect()
        
        try:
            while self.running:
                await self.process_batch()
                await asyncio.sleep(self.poll_interval)
        except Exception as e:
            logger.error(f"Publisher worker error: {e}", exc_info=True)
        finally:
            await self.disconnect()
            
    async def stop(self):
        """Stop the publisher worker."""
        logger.info("Stopping Redis Streams publisher worker")
        self.running = False


# Global publisher instance
_publisher: RedisStreamsPublisher | None = None


def get_publisher() -> RedisStreamsPublisher:
    """Get or create the global publisher instance."""
    global _publisher
    
    if _publisher is None:
        _publisher = RedisStreamsPublisher(
            redis_url=settings.redis_url,
            batch_size=100,
            poll_interval=1
        )
        
    return _publisher


async def start_publisher():
    """Start the publisher background task."""
    publisher = get_publisher()
    await publisher.run()


async def stop_publisher():
    """Stop the publisher background task."""
    publisher = get_publisher()
    await publisher.stop()
