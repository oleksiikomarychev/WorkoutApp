"""Redis Streams consumer for webhook dispatcher."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from config import settings
from redis_client import redis_client

logger = logging.getLogger(__name__)


class StreamConsumer:
    """Consumes events from Redis Streams."""

    # Social service streams
    SOCIAL_STREAMS: list[str] = [
        "app.social.post.created",
        "app.social.comment.created",
        "app.social.reaction.toggled",
        "app.social.follow.changed",
    ]

    # Messaging service streams
    MESSAGING_STREAMS: list[str] = [
        "app.messaging.message.created",
        "app.messaging.message.acknowledged",
        "app.messaging.channel.created",
        "app.messaging.channel.member_added",
        "app.messaging.presence.updated",
    ]

    def __init__(self) -> None:
        """Initialize stream consumer."""
        self.all_streams: list[str] = self.SOCIAL_STREAMS + self.MESSAGING_STREAMS
        logger.info("Stream consumer initialized for %d streams", len(self.all_streams))

    def consume_batch(self) -> list[dict[str, Any]]:
        """Consume a batch of events from all subscribed streams."""
        # Build streams dict for XREADGROUP ('>' denotes new unread messages)
        streams_dict = {stream: ">" for stream in self.all_streams}

        raw_events = redis_client.read_events(
            streams=streams_dict,
            group_name=settings.consumer_group_name,
            consumer_name=settings.consumer_name,
            count=settings.batch_size,
            block=settings.block_time_ms,
        )

        if not raw_events:
            return []

        events: list[dict[str, Any]] = []
        for stream_name, message_id, message_data in raw_events:
            try:
                event = self._parse_event(stream_name, message_id, message_data)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error("Error parsing event %s from %s: %s", message_id, stream_name, e, exc_info=True)
                # Acknowledge malformed events to prevent stream stalling
                redis_client.acknowledge_event(stream_name, settings.consumer_group_name, message_id)

        logger.info("Consumed %d events from streams", len(events))
        return events

    def _parse_event(
        self,
        stream_name: str,
        message_id: str,
        message_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Parse raw event data into structured format supporting both unpacked and nested formats."""
        try:
            # Determine service from stream name
            service = "social" if stream_name.startswith("app.social.") else "messaging"

            # Extract event type from stream name (e.g. app.social.post.created -> post.created)
            event_type = stream_name.replace(f"app.{service}.", "")

            # Handle payload: support explicit 'payload' key and unpacked field format
            if "payload" in message_data:
                raw_payload = message_data["payload"]
                if isinstance(raw_payload, str):
                    try:
                        payload = json.loads(raw_payload)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse string payload as JSON for event %s", message_id)
                        payload = {"raw_payload": raw_payload}
                elif isinstance(raw_payload, dict):
                    payload = raw_payload
                else:
                    payload = {"value": raw_payload}
            else:
                # Reconstruct payload from unpacked fields produced by redis_publisher
                payload = {}
                metadata_keys = {"stream_name", "message_id", "event_type", "event_id", "timestamp"}
                for k, v in message_data.items():
                    if k in metadata_keys:
                        continue
                    if isinstance(v, str) and (v.startswith("{") or v.startswith("[")):
                        try:
                            payload[k] = json.loads(v)
                            continue
                        except json.JSONDecodeError:
                            pass
                    payload[k] = v

            return {
                "stream_name": stream_name,
                "message_id": message_id,
                "service": service,
                "event_type": event_type,
                "payload": payload,
                "retry_count": 0,
                "raw_data": message_data,
            }

        except Exception as e:
            logger.error("Error parsing event %s: %s", message_id, e, exc_info=True)
            return None

    def acknowledge_event(self, event: dict[str, Any]) -> None:
        """Acknowledge that an event has been successfully processed."""
        redis_client.acknowledge_event(
            stream_name=event["stream_name"],
            group_name=settings.consumer_group_name,
            message_id=event["message_id"],
        )
        logger.debug("Acknowledged event %s from %s", event["message_id"], event["stream_name"])

    def move_to_dlq(self, event: dict[str, Any], reason: str) -> None:
        """Move a failed event to the dead-letter queue and acknowledge the original stream event."""
        dlq_stream = f"app.dlq.{event['service']}"

        dlq_data = {
            "original_stream": event["stream_name"],
            "original_message_id": event["message_id"],
            "event_type": event["event_type"],
            "payload": json.dumps(event.get("payload", {})),
            "retry_count": str(event.get("retry_count", 0)),
            "failure_reason": reason,
            "failed_at": datetime.now(UTC).isoformat(),
            "raw_data": json.dumps(event.get("raw_data", {})),
        }

        dlq_message_id = redis_client.add_to_dlq(dlq_stream, dlq_data)

        if dlq_message_id:
            logger.warning(
                "Moved event %s from %s to DLQ %s (dlq_id=%s). Reason: %s",
                event["message_id"],
                event["stream_name"],
                dlq_stream,
                dlq_message_id,
                reason,
            )
        else:
            logger.error(
                "Failed to move event %s to DLQ %s. Acknowledging to avoid blocking stream.",
                event["message_id"],
                dlq_stream,
            )

        # Acknowledge original event so consumer group does not block
        self.acknowledge_event(event)


# Global stream consumer instance
stream_consumer = StreamConsumer()
