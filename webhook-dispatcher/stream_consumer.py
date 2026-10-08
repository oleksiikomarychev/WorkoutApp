"""Redis Streams consumer for webhook dispatcher."""
import json
import logging
from datetime import datetime

from config import settings
from redis_client import redis_client

logger = logging.getLogger(__name__)


class StreamConsumer:
    """Consumes events from Redis Streams."""
    
    # Define all streams to consume from
    SOCIAL_STREAMS = [
        "app.social.post.created",
        "app.social.comment.created",
        "app.social.reaction.toggled",
        "app.social.follow.changed",
    ]
    
    MESSAGING_STREAMS = [
        "app.messaging.message.created",
        "app.messaging.message.acknowledged",
        "app.messaging.channel.created",
        "app.messaging.channel.member_added",
        "app.messaging.presence.updated",
    ]
    
    def __init__(self):
        """Initialize stream consumer."""
        self.all_streams = self.SOCIAL_STREAMS + self.MESSAGING_STREAMS
        logger.info(f"Stream consumer initialized for {len(self.all_streams)} streams")
    
    def consume_batch(self) -> list[dict]:
        """
        Consume a batch of events from all streams.
        
        Returns:
            List of event dictionaries with metadata
        """
        # Build streams dict for XREADGROUP (all streams read from '>' for new messages)
        streams_dict = {stream: '>' for stream in self.all_streams}
        
        # Read events from all streams
        raw_events = redis_client.read_events(
            streams=streams_dict,
            group_name=settings.consumer_group_name,
            consumer_name=settings.consumer_name,
            count=settings.batch_size,
            block=settings.block_time_ms
        )
        
        if not raw_events:
            return []
        
        # Parse and enrich events
        events = []
        for stream_name, message_id, message_data in raw_events:
            try:
                event = self._parse_event(stream_name, message_id, message_data)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error parsing event {message_id} from {stream_name}: {e}", exc_info=True)
                # Acknowledge malformed events to prevent blocking
                redis_client.acknowledge_event(stream_name, settings.consumer_group_name, message_id)
        
        logger.info(f"Consumed {len(events)} events from streams")
        return events
    
    def _parse_event(self, stream_name: str, message_id: str, message_data: dict) -> dict | None:
        """
        Parse raw event data into structured format.
        
        Args:
            stream_name: Name of the stream
            message_id: Redis message ID
            message_data: Raw message data from Redis
            
        Returns:
            Parsed event dictionary or None if parsing fails
        """
        try:
            # Determine service from stream name
            service = "social" if stream_name.startswith("app.social.") else "messaging"
            
            # Extract event type from stream name (e.g., "app.social.post.created" -> "post.created")
            event_type = stream_name.replace(f"app.{service}.", "")
            
            # Parse payload if it's a JSON string
            payload = message_data.get("payload", "{}")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse payload as JSON for event {message_id}")
                    payload = {}
            
            # Build event object
            event = {
                "stream_name": stream_name,
                "message_id": message_id,
                "service": service,
                "event_type": event_type,
                "payload": payload,
                "retry_count": 0,
                "raw_data": message_data
            }
            
            return event
            
        except Exception as e:
            logger.error(f"Error parsing event: {e}", exc_info=True)
            return None
    
    def acknowledge_event(self, event: dict):
        """Acknowledge that an event has been successfully processed."""
        redis_client.acknowledge_event(
            stream_name=event["stream_name"],
            group_name=settings.consumer_group_name,
            message_id=event["message_id"]
        )
        logger.debug(f"Acknowledged event {event['message_id']} from {event['stream_name']}")
    
    def move_to_dlq(self, event: dict, reason: str):
        """
        Move a failed event to the dead-letter queue after max retries exceeded.
        
        DLQ stream naming: app.dlq.{service} (e.g., app.dlq.social, app.dlq.messaging)
        
        After moving to DLQ, the original event is acknowledged to prevent blocking
        the consumer group.
        
        Args:
            event: Event dictionary
            reason: Reason for failure (e.g., "Max retries exceeded after 5 attempts")
        """
        dlq_stream = f"app.dlq.{event['service']}"
        
        # Prepare DLQ event data with all context
        dlq_data = {
            "original_stream": event["stream_name"],
            "original_message_id": event["message_id"],
            "event_type": event["event_type"],
            "payload": json.dumps(event["payload"]),
            "retry_count": str(event.get("retry_count", 0)),
            "failure_reason": reason,
            "failed_at": datetime.utcnow().isoformat(),
            "raw_data": json.dumps(event.get("raw_data", {}))
        }
        
        # Add to DLQ stream
        dlq_message_id = redis_client.add_to_dlq(dlq_stream, dlq_data)
        
        if dlq_message_id:
            logger.warning(
                f"Moved event {event['message_id']} from {event['stream_name']} "
                f"to DLQ {dlq_stream} (dlq_id={dlq_message_id}). Reason: {reason}"
            )
        else:
            logger.error(
                f"Failed to move event {event['message_id']} to DLQ {dlq_stream}. "
                f"Will still acknowledge to prevent blocking."
            )
        
        # Acknowledge the original event so it doesn't block the stream
        self.acknowledge_event(event)


# Global stream consumer instance
stream_consumer = StreamConsumer()
