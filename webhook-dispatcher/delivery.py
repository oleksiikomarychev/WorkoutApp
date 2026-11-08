"""HTTP delivery for webhooks with HMAC signing."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any, NamedTuple
from uuid import uuid4

import httpx
from config import settings
from models import WebhookSubscription

logger = logging.getLogger(__name__)


class DeliveryResult(NamedTuple):
    """Result of a webhook delivery attempt (tuple-compatible)."""

    success: bool
    status_code: int | None
    error_message: str | None
    delivery_id: str


class WebhookDelivery:
    """Handles HTTP delivery of webhooks with HMAC signing."""

    def __init__(self) -> None:
        """Initialize HTTP client for webhook delivery."""
        self.http_client = httpx.AsyncClient(
            timeout=settings.delivery_timeout,
            follow_redirects=False,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    def generate_signature(self, payload: bytes, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

    async def deliver(
        self,
        subscription: WebhookSubscription,
        payload: dict[str, Any],
        retry_count: int = 0,
        delivery_id: str | None = None,
    ) -> DeliveryResult:
        """Deliver webhook to target URL with HMAC signature."""
        if delivery_id is None:
            delivery_id = str(uuid4())

        # Serialize payload safely
        payload_bytes = json.dumps(payload, default=str).encode("utf-8")

        # Generate HMAC signature
        signature = self.generate_signature(payload_bytes, subscription.secret)

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "X-Delivery-Id": delivery_id,
            "X-Event-Type": str(payload.get("event_type", "unknown")),
            "X-Signature": f"sha256={signature}",
            "X-Retry": str(retry_count),
            "User-Agent": "SocialMessagingPlatform/1.0",
        }

        try:
            logger.info(
                "Delivering webhook to %s (delivery_id=%s, retry=%d)",
                subscription.target_url,
                delivery_id,
                retry_count,
            )

            response = await self.http_client.post(
                subscription.target_url,
                content=payload_bytes,
                headers=headers,
            )

            status_code = response.status_code

            if 200 <= status_code < 300:
                logger.info(
                    "Webhook delivered successfully to %s (status=%d)",
                    subscription.target_url,
                    status_code,
                )
                return DeliveryResult(True, status_code, None, delivery_id)

            if 400 <= status_code < 500:
                if status_code == 429:
                    logger.warning("Rate limited by %s (status=429)", subscription.target_url)
                    return DeliveryResult(False, status_code, "Rate limited", delivery_id)
                logger.warning(
                    "Client error from %s (status=%d)",
                    subscription.target_url,
                    status_code,
                )
                return DeliveryResult(False, status_code, f"Client error: {status_code}", delivery_id)

            logger.warning(
                "Server error from %s (status=%d)",
                subscription.target_url,
                status_code,
            )
            return DeliveryResult(False, status_code, f"Server error: {status_code}", delivery_id)

        except httpx.TimeoutException as e:
            logger.warning("Timeout delivering webhook to %s: %s", subscription.target_url, e)
            return DeliveryResult(False, None, "Timeout", delivery_id)
        except httpx.RequestError as e:
            logger.warning("Request error delivering webhook to %s: %s", subscription.target_url, e)
            return DeliveryResult(False, None, f"Request error: {e}", delivery_id)
        except Exception as e:
            logger.error(
                "Unexpected error delivering webhook to %s: %s",
                subscription.target_url,
                e,
                exc_info=True,
            )
            return DeliveryResult(False, None, f"Unexpected error: {e}", delivery_id)

    def should_retry(self, status_code: int | None, error_message: str | None) -> bool:
        """Determine if a failed delivery attempt should be retried."""
        # Retry on network errors and timeouts
        if status_code is None:
            logger.debug("Will retry due to network error: %s", error_message)
            return True

        # Retry on server errors (5xx)
        if status_code >= 500:
            logger.debug("Will retry due to server error: %d", status_code)
            return True

        # Retry on rate limiting (429)
        if status_code == 429:
            logger.debug("Will retry due to rate limiting: 429")
            return True

        # Don't retry on client errors (4xx except 429)
        if 400 <= status_code < 500:
            logger.debug("Will NOT retry due to client error: %d", status_code)
            return False

        # Default for any unexpected status code
        logger.debug("Will NOT retry for unexpected status code: %d", status_code)
        return False

    def get_retry_delay(self, retry_count: int) -> int:
        """Get delay in seconds before next retry attempt using exponential backoff."""
        if not settings.retry_delays:
            return 60
        if retry_count < 0:
            return settings.retry_delays[0]
        if retry_count >= len(settings.retry_delays):
            return settings.retry_delays[-1]
        return settings.retry_delays[retry_count]


# Global delivery instance
webhook_delivery = WebhookDelivery()
