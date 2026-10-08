"""Redis client for consuming events from Redis Streams."""
import logging

import redis
from config import settings
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisStreamClient:
    """Client for consuming events from Redis Streams."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client: redis.Redis | None = None
        self.connected = False
    
    def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            # Test connection
            self.redis_client.ping()
            self.connected = True
            logger.info(f"Connected to Redis at {settings.redis_url}")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            self.redis_client.close()
            self.connected = False
            logger.info("Disconnected from Redis")
    
    def create_consumer_group(self, stream_name: str, group_name: str):
        """Create a consumer group for a stream if it doesn't exist."""
        try:
            # Try to create the group starting from the beginning of the stream
            self.redis_client.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id='0',
                mkstream=True
            )
            logger.info(f"Created consumer group '{group_name}' for stream '{stream_name}'")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group '{group_name}' already exists for stream '{stream_name}'")
            else:
                logger.error(f"Error creating consumer group: {e}")
                raise
    
    def read_events(self, streams: dict[str, str], group_name: str, consumer_name: str, 
                   count: int = 10, block: int = 5000) -> list[tuple[str, str, dict]]:
        """
        Read events from multiple streams using consumer group.
        
        Args:
            streams: Dict of stream_name -> last_id (use '>' for new messages)
            group_name: Consumer group name
            consumer_name: Consumer name
            count: Maximum number of messages to read
            block: Block time in milliseconds
            
        Returns:
            List of tuples (stream_name, message_id, message_data)
        """
        try:
            # XREADGROUP GROUP group_name consumer_name COUNT count BLOCK block STREAMS stream1 stream2 ... > >
            result = self.redis_client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams=streams,
                count=count,
                block=block
            )
            
            # Parse result: [['stream_name', [('msg_id', {'field': 'value'}), ...]], ...]
            events = []
            if result:
                for stream_name, messages in result:
                    for message_id, message_data in messages:
                        events.append((stream_name, message_id, message_data))
            
            return events
        except RedisError as e:
            logger.error(f"Error reading from streams: {e}")
            return []
    
    def acknowledge_event(self, stream_name: str, group_name: str, message_id: str):
        """Acknowledge that an event has been processed."""
        try:
            self.redis_client.xack(stream_name, group_name, message_id)
            logger.debug(f"Acknowledged message {message_id} from stream {stream_name}")
        except RedisError as e:
            logger.error(f"Error acknowledging message: {e}")
    
    def add_to_dlq(self, dlq_stream: str, event_data: dict):
        """Add a failed event to the dead-letter queue."""
        try:
            message_id = self.redis_client.xadd(dlq_stream, event_data)
            logger.info(f"Added event to DLQ stream {dlq_stream}: {message_id}")
            return message_id
        except RedisError as e:
            logger.error(f"Error adding to DLQ: {e}")
            return None


# Global Redis client instance
redis_client = RedisStreamClient()
