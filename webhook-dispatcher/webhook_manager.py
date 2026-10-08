"""Webhook subscription manager for filtering and routing events."""
import logging
from datetime import datetime

from database import db_manager
from models import WebhookSubscription
from sqlalchemy import select

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages webhook subscriptions and event routing."""
    
    def __init__(self):
        """Initialize webhook manager."""
        self._subscription_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 60  # Cache for 60 seconds
    
    def get_active_subscriptions(self, service: str) -> list[WebhookSubscription]:
        """
        Get all active webhook subscriptions for a service.
        
        Args:
            service: Service name ("social" or "messaging")
            
        Returns:
            List of active webhook subscriptions
        """
        # Check cache
        cache_key = f"subscriptions_{service}"
        now = datetime.utcnow()
        
        if (self._cache_timestamp and 
            cache_key in self._subscription_cache and
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl):
            logger.debug(f"Using cached subscriptions for {service}")
            return self._subscription_cache[cache_key]
        
        # Fetch from database
        try:
            if service == "social":
                session = db_manager.get_social_session()
            elif service == "messaging":
                session = db_manager.get_messaging_session()
            else:
                logger.error(f"Unknown service: {service}")
                return []
            
            try:
                # Query active subscriptions
                stmt = select(WebhookSubscription).where(
                    WebhookSubscription.service == service,
                    WebhookSubscription.active == "true"
                )
                
                # Filter out expired leases
                now_dt = datetime.utcnow()
                stmt = stmt.where(
                    (WebhookSubscription.lease_expires_at.is_(None)) |
                    (WebhookSubscription.lease_expires_at > now_dt)
                )
                
                result = session.execute(stmt)
                subscriptions = result.scalars().all()
                
                # Update cache
                self._subscription_cache[cache_key] = subscriptions
                self._cache_timestamp = now
                
                logger.info(f"Loaded {len(subscriptions)} active subscriptions for {service}")
                return subscriptions
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error fetching subscriptions for {service}: {e}", exc_info=True)
            return []
    
    def find_matching_webhooks(self, event: dict) -> list[tuple[WebhookSubscription, dict]]:
        """
        Find all webhook subscriptions that match an event.
        
        Args:
            event: Event dictionary with service, event_type, and payload
            
        Returns:
            List of tuples (subscription, delivery_payload)
        """
        service = event["service"]
        event_type = event["event_type"]
        payload = event["payload"]
        
        # Get active subscriptions for this service
        subscriptions = self.get_active_subscriptions(service)
        
        if not subscriptions:
            logger.debug(f"No active subscriptions for service {service}")
            return []
        
        # Find matching subscriptions
        matches = []
        for subscription in subscriptions:
            if self._matches_subscription(subscription, event_type, payload):
                # Build delivery payload
                delivery_payload = self._build_delivery_payload(event, subscription)
                matches.append((subscription, delivery_payload))
        
        logger.info(f"Found {len(matches)} matching webhooks for event {event_type}")
        return matches
    
    def _matches_subscription(self, subscription: WebhookSubscription, 
                             event_type: str, payload: dict) -> bool:
        """
        Check if an event matches a webhook subscription.
        
        Args:
            subscription: Webhook subscription
            event_type: Event type (e.g., "post.created")
            payload: Event payload
            
        Returns:
            True if event matches subscription filters
        """
        # Check if event type is in subscription's events list
        if event_type not in subscription.events:
            return False
        
        # Apply additional filters
        filters = subscription.filters or {}
        
        # Filter by scope (for social posts)
        if "scope" in filters and "scope" in payload:
            allowed_scopes = filters["scope"]
            if isinstance(allowed_scopes, list) and payload["scope"] not in allowed_scopes:
                return False
        
        # Filter by authors
        if "authors" in filters:
            allowed_authors = filters["authors"]
            author_id = payload.get("author_id") or payload.get("sender_id")
            if isinstance(allowed_authors, list) and author_id and str(author_id) not in allowed_authors:
                return False
        
        # Filter by channel_id (for messaging)
        if "channels" in filters and "channel_id" in payload:
            allowed_channels = filters["channels"]
            if isinstance(allowed_channels, list) and str(payload["channel_id"]) not in allowed_channels:
                return False
        
        return True
    
    def _build_delivery_payload(self, event: dict, subscription: WebhookSubscription) -> dict:
        """
        Build the payload to be delivered to the webhook.
        
        Args:
            event: Event dictionary
            subscription: Webhook subscription
            
        Returns:
            Delivery payload dictionary
        """
        return {
            "event_type": f"{event['service']}.{event['event_type']}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": event["payload"]
        }
    
    def invalidate_cache(self):
        """Invalidate the subscription cache."""
        self._subscription_cache.clear()
        self._cache_timestamp = None
        logger.info("Subscription cache invalidated")


# Global webhook manager instance
webhook_manager = WebhookManager()
