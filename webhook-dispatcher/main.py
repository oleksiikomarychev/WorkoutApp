"""Webhook Dispatcher Service - Main entry point."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from config import settings
from database import db_manager
from delivery import webhook_delivery
from event_processor import event_processor
from redis_client import redis_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def setup_signal_handlers() -> None:
    """Setup graceful shutdown signal handlers."""

    def signal_handler(signum: int, _frame: object) -> None:
        logger.info("Received signal %d, initiating graceful shutdown...", signum)
        event_processor.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def initialize_services() -> None:
    """Initialize Redis connections and stream consumer groups."""
    logger.info("Initializing Webhook Dispatcher Service...")

    redis_client.connect()

    # Create consumer groups for social streams
    social_streams = [
        "app.social.post.created",
        "app.social.comment.created",
        "app.social.reaction.toggled",
        "app.social.follow.changed",
    ]
    for stream in social_streams:
        redis_client.create_consumer_group(stream, settings.consumer_group_name)

    # Create consumer groups for messaging streams
    messaging_streams = [
        "app.messaging.message.created",
        "app.messaging.message.acknowledged",
        "app.messaging.channel.created",
        "app.messaging.channel.member_added",
        "app.messaging.presence.updated",
    ]
    for stream in messaging_streams:
        redis_client.create_consumer_group(stream, settings.consumer_group_name)

    logger.info("All services initialized successfully")


async def cleanup_services() -> None:
    """Clean up and close all connections gracefully."""
    logger.info("Cleaning up services...")
    event_processor.stop()
    await webhook_delivery.close()
    redis_client.disconnect()
    db_manager.close()
    logger.info("Cleanup complete")


async def main() -> None:
    """Main application loop."""
    setup_signal_handlers()

    try:
        await initialize_services()
        logger.info("Webhook Dispatcher Service started successfully")
        await event_processor.process_events()
        logger.info("Event processor finished, exiting main loop")
    except Exception as e:
        logger.error("Fatal error in main loop: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        await cleanup_services()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Webhook Dispatcher Service interrupted, exiting...")
    finally:
        sys.exit(0)
