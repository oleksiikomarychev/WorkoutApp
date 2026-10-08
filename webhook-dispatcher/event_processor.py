"""Event processor with retry logic for webhook delivery."""
import asyncio
import logging
from datetime import datetime, timedelta

from config import settings
from delivery import webhook_delivery
from stream_consumer import stream_consumer
from webhook_manager import webhook_manager

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes events and manages webhook delivery with retry logic."""
    
    def __init__(self):
        """Initialize event processor."""
        self.pending_retries: dict[str, list[dict]] = {}  # retry_key -> retry_info
        self.processing = False
        self.events_pending_ack: set[str] = set()  # Track events waiting for all deliveries
    
    async def process_events(self):
        """Main processing loop for consuming and delivering events."""
        self.processing = True
        
        while self.processing:
            try:
                # Consume batch of events from streams
                events = stream_consumer.consume_batch()
                
                if not events:
                    # No events, check for pending retries
                    await self._process_pending_retries()
                    continue
                
                # Process each event
                for event in events:
                    await self._process_event(event)
                
                # Also check for pending retries
                await self._process_pending_retries()
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _process_event(self, event: dict):
        """
        Process a single event by delivering to matching webhooks.
        
        Retry Logic:
        - Retry on HTTP 5xx or timeout with exponential backoff (1m, 5m, 15m, 1h, 3h)
        - Don't retry on HTTP 4xx (except 429 which is retried)
        - XACK event after successful delivery or non-retryable HTTP 4xx
        - After 5 retry attempts, move to DLQ (app.dlq.*)
        
        Args:
            event: Event dictionary
        """
        try:
            # Find matching webhook subscriptions
            matches = webhook_manager.find_matching_webhooks(event)
            
            if not matches:
                logger.debug(f"No matching webhooks for event {event['event_type']}")
                # Acknowledge event since there are no subscribers
                stream_consumer.acknowledge_event(event)
                return
            
            # Track delivery results for each subscription
            delivery_results = []
            has_retryable_failures = False
            
            # Deliver to all matching webhooks
            for subscription, payload in matches:
                retry_count = event.get("retry_count", 0)
                
                # Get or generate delivery_id for deduplication
                # Same delivery_id is reused across all retry attempts
                delivery_key = f"delivery_id_{subscription.id}"
                delivery_id = event.get(delivery_key)
                
                success, status_code, error_msg, returned_delivery_id = await webhook_delivery.deliver(
                    subscription, 
                    payload,
                    retry_count=retry_count,
                    delivery_id=delivery_id
                )
                
                # Store delivery_id in event for retry deduplication
                # This ensures the same delivery_id is used across all retry attempts
                if delivery_key not in event:
                    event[delivery_key] = returned_delivery_id
                
                delivery_results.append({
                    "subscription_id": str(subscription.id),
                    "success": success,
                    "status_code": status_code,
                    "error_message": error_msg
                })
                
                if not success:
                    # Determine if this failure should be retried
                    should_retry = webhook_delivery.should_retry(status_code, error_msg)
                    
                    if should_retry:
                        # Check if we've exceeded max retries
                        if retry_count >= settings.max_retries:
                            # Max retries exceeded (5 attempts), move to DLQ
                            logger.warning(
                                f"Max retries ({settings.max_retries}) exceeded for event {event['message_id']} "
                                f"to subscription {subscription.id}"
                            )
                            stream_consumer.move_to_dlq(
                                event, 
                                f"Max retries exceeded after {retry_count} attempts. "
                                f"Last error: {error_msg} (status={status_code})"
                            )
                        else:
                            # Schedule retry with exponential backoff
                            await self._schedule_retry(event, subscription, payload, retry_count)
                            has_retryable_failures = True
                    else:
                        # Non-retryable error (4xx except 429)
                        logger.info(
                            f"Not retrying delivery to {subscription.target_url} "
                            f"due to non-retryable error: {error_msg} (status={status_code})"
                        )
            
            # Determine if we should acknowledge the event
            # XACK when:
            # 1. All deliveries succeeded
            # 2. All failures are non-retryable (4xx except 429)
            # 3. All retryable failures have exceeded max retries (moved to DLQ)
            all_succeeded = all(r["success"] for r in delivery_results)
            
            if all_succeeded:
                # All deliveries succeeded - acknowledge immediately
                stream_consumer.acknowledge_event(event)
                logger.info(f"Event {event['message_id']} delivered successfully to all subscriptions")
            elif not has_retryable_failures:
                # No pending retries - all failures are either non-retryable or moved to DLQ
                stream_consumer.acknowledge_event(event)
                logger.info(f"Event {event['message_id']} processed (no retryable failures)")
            else:
                # Has retryable failures - don't acknowledge yet, will retry later
                logger.info(
                    f"Event {event['message_id']} has pending retries, "
                    f"will not acknowledge until retries complete"
                )
            
        except Exception as e:
            logger.error(f"Error processing event {event.get('message_id')}: {e}", exc_info=True)
    
    async def _schedule_retry(self, event: dict, subscription, payload: dict, retry_count: int):
        """
        Schedule a retry for a failed delivery.
        
        Args:
            event: Original event
            subscription: Webhook subscription
            payload: Delivery payload
            retry_count: Current retry count
        """
        next_retry_count = retry_count + 1
        delay = webhook_delivery.get_retry_delay(retry_count)
        retry_time = datetime.utcnow() + timedelta(seconds=delay)
        
        retry_info = {
            "event": event,
            "subscription": subscription,
            "payload": payload,
            "retry_count": next_retry_count,
            "retry_time": retry_time
        }
        
        # Store in pending retries
        retry_key = f"{event['message_id']}_{subscription.id}"
        if retry_key not in self.pending_retries:
            self.pending_retries[retry_key] = []
        self.pending_retries[retry_key].append(retry_info)
        
        logger.info(f"Scheduled retry {next_retry_count} for event {event['message_id']} "
                   f"to {subscription.target_url} in {delay} seconds")
    
    async def _process_pending_retries(self):
        """Process pending retries that are due."""
        now = datetime.utcnow()
        retries_to_process = []
        retries_to_keep = {}
        
        # Find retries that are due
        for retry_key, retry_list in self.pending_retries.items():
            for retry_info in retry_list:
                if retry_info["retry_time"] <= now:
                    retries_to_process.append((retry_key, retry_info))
                else:
                    if retry_key not in retries_to_keep:
                        retries_to_keep[retry_key] = []
                    retries_to_keep[retry_key].append(retry_info)
        
        # Update pending retries
        self.pending_retries = retries_to_keep
        
        # Process due retries
        for retry_key, retry_info in retries_to_process:
            await self._execute_retry(retry_info)
    
    async def _execute_retry(self, retry_info: dict):
        """
        Execute a retry attempt with exponential backoff.
        
        Retry delays: 1m, 5m, 15m, 1h, 3h (configurable)
        Max retries: 5 attempts
        
        Args:
            retry_info: Retry information dictionary
        """
        event = retry_info["event"]
        subscription = retry_info["subscription"]
        payload = retry_info["payload"]
        retry_count = retry_info["retry_count"]
        
        logger.info(
            f"Executing retry attempt {retry_count}/{settings.max_retries} "
            f"for event {event['message_id']} to {subscription.target_url}"
        )
        
        # Update event retry count
        event["retry_count"] = retry_count
        
        # Get delivery_id for deduplication (should already be stored in event)
        delivery_key = f"delivery_id_{subscription.id}"
        delivery_id = event.get(delivery_key)
        
        # Attempt delivery
        success, status_code, error_msg, returned_delivery_id = await webhook_delivery.deliver(
            subscription,
            payload,
            retry_count=retry_count,
            delivery_id=delivery_id
        )
        
        if success:
            # Success! Acknowledge the event
            stream_consumer.acknowledge_event(event)
            logger.info(
                f"Retry {retry_count} succeeded for event {event['message_id']} "
                f"to {subscription.target_url}"
            )
        else:
            # Failed again - determine next action
            should_retry = webhook_delivery.should_retry(status_code, error_msg)
            
            if should_retry:
                # Check if we've reached max retries
                if retry_count >= settings.max_retries:
                    # Max retries exceeded (5 attempts) - move to DLQ
                    logger.warning(
                        f"Max retries ({settings.max_retries}) exceeded for event {event['message_id']} "
                        f"to {subscription.target_url}. Moving to DLQ."
                    )
                    stream_consumer.move_to_dlq(
                        event,
                        f"Max retries exceeded after {retry_count} attempts. "
                        f"Last error: {error_msg} (status={status_code})"
                    )
                else:
                    # Schedule another retry with exponential backoff
                    next_delay = webhook_delivery.get_retry_delay(retry_count)
                    logger.info(
                        f"Retry {retry_count} failed for event {event['message_id']}. "
                        f"Scheduling retry {retry_count + 1} in {next_delay}s"
                    )
                    await self._schedule_retry(event, subscription, payload, retry_count)
            else:
                # Non-retryable error (4xx except 429) - acknowledge and stop
                logger.info(
                    f"Non-retryable error for event {event['message_id']} "
                    f"to {subscription.target_url}: {error_msg} (status={status_code}). "
                    f"Acknowledging event."
                )
                stream_consumer.acknowledge_event(event)
    
    def stop(self):
        """Stop processing events."""
        self.processing = False
        logger.info("Event processor stopped")


# Global event processor instance
event_processor = EventProcessor()
