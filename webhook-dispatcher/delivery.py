"""HTTP delivery for webhooks with HMAC signing."""
import hashlib
import hmac
import json
import logging
from uuid import uuid4

import httpx
from config import settings
from models import WebhookSubscription

logger = logging.getLogger(__name__)


class WebhookDelivery:
    """Handles HTTP delivery of webhooks with HMAC signing."""
    
    def __init__(self):
        """Initialize webhook delivery."""
        self.http_client = httpx.AsyncClient(
            timeout=settings.delivery_timeout,
            follow_redirects=False
        )
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
    
    def generate_signature(self, payload: bytes, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.
        
        Args:
            payload: Payload bytes to sign
            secret: Secret key for HMAC
            
        Returns:
            Hex digest of HMAC signature
        """
        signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def deliver(self, subscription: WebhookSubscription, payload: dict, 
                     retry_count: int = 0, delivery_id: str | None = None) -> tuple[bool, int | None, str | None, str]:
        """
        Deliver webhook to target URL with HMAC signature.
        
        Args:
            subscription: Webhook subscription
            payload: Payload to deliver
            retry_count: Current retry attempt number
            delivery_id: Optional delivery ID for deduplication (reused across retries)
            
        Returns:
            Tuple of (success, status_code, error_message, delivery_id)
        """
        # Generate or reuse delivery ID for deduplication
        # Same delivery_id is used across all retry attempts for the same event
        if delivery_id is None:
            delivery_id = str(uuid4())
        
        # Serialize payload
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        # Generate HMAC signature
        signature = self.generate_signature(payload_bytes, subscription.secret)
        
        # Build headers
        headers = {
            "Content-Type": "application/json",
            "X-Delivery-Id": delivery_id,
            "X-Event-Type": payload.get("event_type", "unknown"),
            "X-Signature": f"sha256={signature}",
            "X-Retry": str(retry_count),
            "User-Agent": "SocialMessagingPlatform/1.0"
        }
        
        try:
            logger.info(f"Delivering webhook to {subscription.target_url} (delivery_id={delivery_id}, retry={retry_count})")
            
            # Send POST request
            response = await self.http_client.post(
                subscription.target_url,
                content=payload_bytes,
                headers=headers
            )
            
            status_code = response.status_code
            
            # Check if delivery was successful
            if 200 <= status_code < 300:
                logger.info(f"Webhook delivered successfully to {subscription.target_url} (status={status_code})")
                return (True, status_code, None, delivery_id)
            elif 400 <= status_code < 500:
                # Client error - don't retry (except 429)
                if status_code == 429:
                    logger.warning(f"Rate limited by {subscription.target_url} (status=429)")
                    return (False, status_code, "Rate limited", delivery_id)
                else:
                    logger.warning(f"Client error from {subscription.target_url} (status={status_code})")
                    return (False, status_code, f"Client error: {status_code}", delivery_id)
            else:
                # Server error - retry
                logger.warning(f"Server error from {subscription.target_url} (status={status_code})")
                return (False, status_code, f"Server error: {status_code}", delivery_id)
                
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout delivering webhook to {subscription.target_url}: {e}")
            return (False, None, "Timeout", delivery_id)
        except httpx.RequestError as e:
            logger.warning(f"Request error delivering webhook to {subscription.target_url}: {e}")
            return (False, None, f"Request error: {str(e)}", delivery_id)
        except Exception as e:
            logger.error(f"Unexpected error delivering webhook to {subscription.target_url}: {e}", exc_info=True)
            return (False, None, f"Unexpected error: {str(e)}", delivery_id)
    
    def should_retry(self, status_code: int | None, error_message: str | None) -> bool:
        """
        Determine if a failed delivery should be retried.
        
        Retry conditions:
        - HTTP 5xx (server errors)
        - HTTP 429 (rate limiting)
        - Timeout errors (no status code)
        - Network errors (no status code)
        
        Don't retry:
        - HTTP 4xx (client errors, except 429)
        
        Args:
            status_code: HTTP status code (None if request failed)
            error_message: Error message
            
        Returns:
            True if delivery should be retried
        """
        # Retry on network errors (timeout, connection errors, etc.)
        if status_code is None:
            logger.debug(f"Will retry due to network error: {error_message}")
            return True
        
        # Retry on server errors (5xx)
        if status_code >= 500:
            logger.debug(f"Will retry due to server error: {status_code}")
            return True
        
        # Retry on rate limiting (429)
        if status_code == 429:
            logger.debug(f"Will retry due to rate limiting: {status_code}")
            return True
        
        # Don't retry on client errors (4xx except 429)
        if 400 <= status_code < 500:
            logger.debug(f"Will NOT retry due to client error: {status_code}")
            return False
        
        # Default: don't retry for unexpected status codes
        logger.debug(f"Will NOT retry for unexpected status code: {status_code}")
        return False
    
    def get_retry_delay(self, retry_count: int) -> int:
        """
        Get delay in seconds before next retry attempt using exponential backoff.
        
        Retry delays (configurable):
        - Attempt 1: 60s (1 minute)
        - Attempt 2: 300s (5 minutes)
        - Attempt 3: 900s (15 minutes)
        - Attempt 4: 3600s (1 hour)
        - Attempt 5: 10800s (3 hours)
        
        Args:
            retry_count: Current retry count (0-based, so 0 = first retry)
            
        Returns:
            Delay in seconds before next retry
        """
        if retry_count >= len(settings.retry_delays):
            # If we somehow exceed configured delays, use the last one
            return settings.retry_delays[-1]
        return settings.retry_delays[retry_count]


# Global delivery instance
webhook_delivery = WebhookDelivery()
