"""Webhook Dispatcher Service - Main entry point."""
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
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True


async def initialize_services():
    """Initialize all required services."""
    logger.info("Initializing Webhook Dispatcher Service...")
    
    # Connect to Redis
    redis_client.connect()
    
    # Create consumer groups for social and messaging streams
    # Social service streams
    redis_client.create_consumer_group("app.social.post.created", settings.consumer_group_name)
    redis_client.create_consumer_group("app.social.comment.created", settings.consumer_group_name)
    redis_client.create_consumer_group("app.social.reaction.toggled", settings.consumer_group_name)
    redis_client.create_consumer_group("app.social.follow.changed", settings.consumer_group_name)
    
    # Messaging service streams
    redis_client.create_consumer_group("app.messaging.message.created", settings.consumer_group_name)
    redis_client.create_consumer_group("app.messaging.message.acknowledged", settings.consumer_group_name)
    redis_client.create_consumer_group("app.messaging.channel.created", settings.consumer_group_name)
    redis_client.create_consumer_group("app.messaging.channel.member_added", settings.consumer_group_name)
    redis_client.create_consumer_group("app.messaging.presence.updated", settings.consumer_group_name)
    
    logger.info("All services initialized successfully")


async def cleanup_services():
    """Cleanup all services."""
    logger.info("Cleaning up services...")
    event_processor.stop()
    await webhook_delivery.close()
    redis_client.disconnect()
    db_manager.close()
    logger.info("Cleanup complete")


async def main():
    """Main entry point for webhook dispatcher service."""
    global shutdown_flag
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize services
        await initialize_services()
        
        logger.info("Webhook Dispatcher Service started successfully")
        
        # Start event processing
        await event_processor.process_events()
        
        logger.info("Shutdown flag set, exiting main loop")
        
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await cleanup_services()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Webhook Dispatcher Service shutting down...")
    finally:
        sys.exit(0)
