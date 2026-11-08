"""Redis client for consuming events from Redis Streams."""

from __future__ import annotations

import logging
from typing import Any

import redis
from config import settings
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisStreamClient:
    """Client for consuming events from Redis Streams."""

    def __init__(self) -> None:
        """Initialize Redis connection state."""
        self.redis_client: redis.Redis | None = None
        self.connected: bool = False

    def _get_client(self) -> redis.Redis:
        """Return active redis client or raise RuntimeError."""
        if self.redis_client is None:
            raise RuntimeError("Redis client is not connected. Call connect() first.")
        return self.redis_client

    def connect(self) -> None:
        """Connect to Redis and test connection."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # Test connection
            self.redis_client.ping()
            self.connected = True
            logger.info("Connected to Redis at %s", settings.redis_url)
        except RedisError as e:
            logger.error("Failed to connect to Redis: %s", e)
            self.connected = False
            raise

    def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            self.redis_client.close()
            self.redis_client = None
            self.connected = False
            logger.info("Disconnected from Redis")

    def create_consumer_group(self, stream_name: str, group_name: str) -> None:
        """Create a consumer group for a stream if it doesn't already exist."""
        client = self._get_client()
        try:
            # Try to create group starting from the beginning of the stream
            client.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id="0",
                mkstream=True,
            )
            logger.info("Created consumer group '%s' for stream '%s'", group_name, stream_name)
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group '%s' already exists for stream '%s'", group_name, stream_name)
            else:
                logger.error("Error creating consumer group: %s", e)
                raise

    def read_events(
        self,
        streams: dict[str, str],
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block: int = 5000,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Read events from multiple streams using consumer group."""
        client = self._get_client()
        try:
            result = client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams=streams,
                count=count,
                block=block,
            )

            events: list[tuple[str, str, dict[str, Any]]] = []
            if result:
                for stream_name, messages in result:
                    for message_id, message_data in messages:
                        events.append((stream_name, message_id, message_data))

            return events
        except RedisError as e:
            logger.error("Error reading from streams: %s", e)
            return []

    def acknowledge_event(self, stream_name: str, group_name: str, message_id: str) -> None:
        """Acknowledge that an event has been processed."""
        client = self._get_client()
        try:
            client.xack(stream_name, group_name, message_id)
            logger.debug("Acknowledged message %s from stream %s", message_id, stream_name)
        except RedisError as e:
            logger.error("Error acknowledging message %s: %s", message_id, e)

    def add_to_dlq(self, dlq_stream: str, event_data: dict[str, Any]) -> str | None:
        """Add a failed event to the dead-letter queue."""
        client = self._get_client()
        try:
            message_id = client.xadd(dlq_stream, event_data)
            logger.info("Added event to DLQ stream %s: %s", dlq_stream, message_id)
            return str(message_id)
        except RedisError as e:
            logger.error("Error adding to DLQ stream %s: %s", dlq_stream, e)
            return None


# Global Redis client instance
redis_client = RedisStreamClient()
