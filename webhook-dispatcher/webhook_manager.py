"""Webhook subscription manager for filtering and routing events."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from database import db_manager
from models import WebhookSubscription
from sqlalchemy import select

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages webhook subscriptions and event routing."""

    def __init__(self) -> None:
        """Initialize webhook manager with cache."""
        self._subscription_cache: dict[str, list[WebhookSubscription]] = {}
        self._cache_timestamp: datetime | None = None
        self._cache_ttl: int = 60  # Cache for 60 seconds

    def get_active_subscriptions(self, service: str) -> list[WebhookSubscription]:
        """Get all active webhook subscriptions for a service."""
        cache_key = f"subscriptions_{service}"
        now = datetime.now(UTC)

        if (
            self._cache_timestamp
            and cache_key in self._subscription_cache
            and (now - self._cache_timestamp).total_seconds() < self._cache_ttl
        ):
            logger.debug("Using cached subscriptions for %s", service)
            return self._subscription_cache[cache_key]

        try:
            if service == "social":
                session_cm = db_manager.social_session()
            elif service == "messaging":
                session_cm = db_manager.messaging_session()
            else:
                logger.error("Unknown service: %s", service)
                return []

            with session_cm as session:
                # Query active subscriptions
                stmt = select(WebhookSubscription).where(
                    WebhookSubscription.service == service,
                    WebhookSubscription.active == "true",
                )

                # Filter out expired leases
                stmt = stmt.where(
                    (WebhookSubscription.lease_expires_at.is_(None)) | (WebhookSubscription.lease_expires_at > now)
                )

                result = session.execute(stmt)
                subscriptions = list(result.scalars().all())

                # Update cache
                self._subscription_cache[cache_key] = subscriptions
                self._cache_timestamp = now

                logger.info("Loaded %d active subscriptions for %s", len(subscriptions), service)
                return subscriptions

        except Exception as e:
            logger.error("Error fetching subscriptions for %s: %s", service, e, exc_info=True)
            return []

    def find_matching_webhooks(self, event: dict[str, Any]) -> list[tuple[WebhookSubscription, dict[str, Any]]]:
        """Find all webhook subscriptions that match an event."""
        service = str(event["service"])
        event_type = str(event["event_type"])
        payload = event.get("payload", {})

        subscriptions = self.get_active_subscriptions(service)
        if not subscriptions:
            logger.debug("No active subscriptions for service %s", service)
            return []

        matches: list[tuple[WebhookSubscription, dict[str, Any]]] = []
        for subscription in subscriptions:
            if self._matches_subscription(subscription, event_type, payload):
                delivery_payload = self._build_delivery_payload(event, subscription)
                matches.append((subscription, delivery_payload))

        logger.info("Found %d matching webhooks for event %s", len(matches), event_type)
        return matches

    def _matches_subscription(
        self,
        subscription: WebhookSubscription,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Check if an event matches a webhook subscription's events and filters."""
        if not subscription.events or event_type not in subscription.events:
            return False

        filters: dict[str, Any] = subscription.filters or {}

        # Filter by scope (for social posts)
        if "scope" in filters and "scope" in payload:
            allowed_scopes = filters["scope"]
            if isinstance(allowed_scopes, list) and payload["scope"] not in allowed_scopes:
                return False

        # Filter by authors (social posts, messages)
        if "authors" in filters:
            allowed_authors = filters["authors"]
            author_id = payload.get("author_id") or payload.get("sender_id")
            if isinstance(allowed_authors, list) and author_id is not None:
                allowed_set = {str(a) for a in allowed_authors}
                if str(author_id) not in allowed_set:
                    return False

        # Filter by channel_id (for messaging)
        if "channels" in filters and "channel_id" in payload:
            allowed_channels = filters["channels"]
            channel_id = payload.get("channel_id")
            if isinstance(allowed_channels, list) and channel_id is not None:
                allowed_set = {str(c) for c in allowed_channels}
                if str(channel_id) not in allowed_set:
                    return False

        return True

    def _build_delivery_payload(
        self,
        event: dict[str, Any],
        subscription: WebhookSubscription,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Build the payload dictionary to be delivered to the webhook."""
        return {
            "event_type": f"{event['service']}.{event['event_type']}",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": event.get("payload", {}),
        }

    def invalidate_cache(self) -> None:
        """Invalidate the subscription cache."""
        self._subscription_cache.clear()
        self._cache_timestamp = None
        logger.info("Subscription cache invalidated")


# Global webhook manager instance
webhook_manager = WebhookManager()
