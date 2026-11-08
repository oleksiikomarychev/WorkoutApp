"""Event processor with retry logic for webhook delivery."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from config import settings
from delivery import webhook_delivery
from models import WebhookSubscription
from stream_consumer import stream_consumer
from webhook_manager import webhook_manager

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes events and manages webhook delivery with retry logic and exact-once stream acknowledgment."""

    def __init__(self) -> None:
        """Initialize event processor state."""
        # retry_key (message_id_subscription_id) -> retry_info
        self.pending_retries: dict[str, dict[str, Any]] = {}
        # message_id -> {"event": event, "pending_sub_ids": set of subscription IDs}
        self.active_event_deliveries: dict[str, dict[str, Any]] = {}
        self.processing: bool = False

    async def process_events(self) -> None:
        """Main processing loop for consuming and delivering events."""
        self.processing = True

        while self.processing:
            try:
                # Consume batch of events from subscribed streams
                events = stream_consumer.consume_batch()

                if events:
                    for event in events:
                        await self._process_event(event)

                # Process any retries that are now due
                await self._process_pending_retries()

                # Avoid hot loop when no events and no retries are pending
                if not events and not self._has_due_retries():
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error("Error in event processing loop: %s", e, exc_info=True)
                await asyncio.sleep(1.0)

    def _has_due_retries(self) -> bool:
        """Check if any retries are currently due for execution."""
        now = datetime.now(UTC)
        return any(info["retry_time"] <= now for info in self.pending_retries.values())

    async def _process_event(self, event: dict[str, Any]) -> None:
        """Process a single event by delivering to matching webhook subscriptions."""
        message_id = str(event["message_id"])

        try:
            matches = webhook_manager.find_matching_webhooks(event)

            if not matches:
                logger.debug("No matching webhooks for event %s", event["event_type"])
                stream_consumer.acknowledge_event(event)
                return

            pending_sub_ids: set[str] = set()

            for subscription, payload in matches:
                sub_id_str = str(subscription.id)
                retry_count = event.get("retry_count", 0)

                # Consistent delivery ID per subscription for idempotency
                delivery_key = f"delivery_id_{subscription.id}"
                delivery_id = event.get(delivery_key)

                result = await webhook_delivery.deliver(
                    subscription,
                    payload,
                    retry_count=retry_count,
                    delivery_id=delivery_id,
                )

                if delivery_key not in event:
                    event[delivery_key] = result.delivery_id

                if result.success:
                    logger.debug("Delivery succeeded for sub %s", sub_id_str)
                    continue

                should_retry = webhook_delivery.should_retry(result.status_code, result.error_message)

                if should_retry:
                    if retry_count >= settings.max_retries:
                        logger.warning(
                            "Max retries (%d) exceeded for event %s to subscription %s",
                            settings.max_retries,
                            message_id,
                            subscription.id,
                        )
                        stream_consumer.move_to_dlq(
                            event,
                            f"Max retries exceeded after {retry_count} attempts. "
                            f"Last error: {result.error_message} (status={result.status_code})",
                        )
                    else:
                        pending_sub_ids.add(sub_id_str)
                        self._schedule_retry(event, subscription, payload, retry_count)
                else:
                    logger.info(
                        "Not retrying delivery to %s due to non-retryable error: %s (status=%s)",
                        subscription.target_url,
                        result.error_message,
                        result.status_code,
                    )

            if not pending_sub_ids:
                # All matching subscriptions delivered or handled
                stream_consumer.acknowledge_event(event)
                logger.info("Event %s fully processed and acknowledged", message_id)
            else:
                # Retries are pending for some subscriptions; track before acknowledging stream
                self.active_event_deliveries[message_id] = {
                    "event": event,
                    "pending_sub_ids": pending_sub_ids,
                }
                logger.info(
                    "Event %s has %d pending retry subscriptions",
                    message_id,
                    len(pending_sub_ids),
                )

        except Exception as e:
            logger.error("Error processing event %s: %s", message_id, e, exc_info=True)

    def _schedule_retry(
        self,
        event: dict[str, Any],
        subscription: WebhookSubscription,
        payload: dict[str, Any],
        retry_count: int,
    ) -> None:
        """Schedule a retry attempt for a failed delivery with exponential backoff."""
        next_retry_count = retry_count + 1
        delay = webhook_delivery.get_retry_delay(retry_count)
        retry_time = datetime.now(UTC) + timedelta(seconds=delay)

        retry_key = f"{event['message_id']}_{subscription.id}"
        self.pending_retries[retry_key] = {
            "event": event,
            "subscription": subscription,
            "payload": payload,
            "retry_count": next_retry_count,
            "retry_time": retry_time,
        }

        logger.info(
            "Scheduled retry %d for event %s to %s in %d seconds",
            next_retry_count,
            event["message_id"],
            subscription.target_url,
            delay,
        )

    async def _process_pending_retries(self) -> None:
        """Process retries that have reached their scheduled retry time."""
        now = datetime.now(UTC)
        due_retries: list[tuple[str, dict[str, Any]]] = []

        for retry_key, retry_info in list(self.pending_retries.items()):
            if retry_info["retry_time"] <= now:
                due_retries.append((retry_key, retry_info))
                del self.pending_retries[retry_key]

        for retry_key, retry_info in due_retries:
            await self._execute_retry(retry_key, retry_info)

    async def _execute_retry(self, retry_key: str, retry_info: dict[str, Any]) -> None:
        """Execute a retry attempt for a webhook delivery."""
        event: dict[str, Any] = retry_info["event"]
        subscription: WebhookSubscription = retry_info["subscription"]
        payload: dict[str, Any] = retry_info["payload"]
        retry_count: int = retry_info["retry_count"]
        message_id: str = str(event["message_id"])
        sub_id_str: str = str(subscription.id)

        logger.info(
            "Executing retry %d/%d for event %s to %s",
            retry_count,
            settings.max_retries,
            message_id,
            subscription.target_url,
        )

        event["retry_count"] = retry_count
        delivery_key = f"delivery_id_{subscription.id}"
        delivery_id = event.get(delivery_key)

        result = await webhook_delivery.deliver(
            subscription,
            payload,
            retry_count=retry_count,
            delivery_id=delivery_id,
        )

        delivery_concluded = False

        if result.success:
            logger.info("Retry %d succeeded for event %s to %s", retry_count, message_id, subscription.target_url)
            delivery_concluded = True
        else:
            should_retry = webhook_delivery.should_retry(result.status_code, result.error_message)

            if should_retry:
                if retry_count >= settings.max_retries:
                    logger.warning(
                        "Max retries (%d) exceeded for event %s to %s. Moving to DLQ.",
                        settings.max_retries,
                        message_id,
                        subscription.target_url,
                    )
                    stream_consumer.move_to_dlq(
                        event,
                        f"Max retries exceeded after {retry_count} attempts. "
                        f"Last error: {result.error_message} (status={result.status_code})",
                    )
                    delivery_concluded = True
                else:
                    self._schedule_retry(event, subscription, payload, retry_count)
            else:
                logger.info(
                    "Non-retryable error on retry for event %s to %s: %s (status=%s)",
                    message_id,
                    subscription.target_url,
                    result.error_message,
                    result.status_code,
                )
                delivery_concluded = True

        if delivery_concluded:
            # Check if this concludes all retries for the message_id
            active_info = self.active_event_deliveries.get(message_id)
            if active_info:
                active_info["pending_sub_ids"].discard(sub_id_str)
                if not active_info["pending_sub_ids"]:
                    stream_consumer.acknowledge_event(event)
                    del self.active_event_deliveries[message_id]
                    logger.info("Event %s all retries finished; acknowledged in stream", message_id)

    def stop(self) -> None:
        """Stop event processing loop."""
        self.processing = False
        logger.info("Event processor stopped")


# Global event processor instance
event_processor = EventProcessor()
