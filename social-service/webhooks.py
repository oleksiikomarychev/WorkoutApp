"""Webhook subscription management endpoints."""
import hashlib
import hmac
import json
import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from models import WebhookSubscription
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session
from utils import utcnow

router = APIRouter(prefix="/social/webhooks", tags=["webhooks"])


# Pydantic models for request/response
class WebhookSubscriptionCreate(BaseModel):
    """Request model for creating a webhook subscription."""

    target_url: str
    events: list[str]
    filters: dict[str, Any] = Field(default_factory=dict)
    lease_expires_at: datetime | None = None

    @field_validator("target_url")
    @classmethod
    def validate_https(cls, v: str) -> str:
        """Validate that target_url uses HTTPS."""
        if not v.startswith("https://"):
            raise ValueError("target_url must use HTTPS protocol")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        """Validate that events list is not empty."""
        if not v:
            raise ValueError("events list cannot be empty")
        return v


class WebhookSubscriptionResponse(BaseModel):
    """Response model for webhook subscription."""

    id: UUID
    service: str
    target_url: str
    secret: str
    events: list[str]
    filters: dict[str, Any]
    active: str
    lease_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookSubscriptionList(BaseModel):
    """Response model for listing webhook subscriptions."""

    subscriptions: list[WebhookSubscriptionResponse]
    total: int


class TestDeliveryRequest(BaseModel):
    """Request model for test webhook delivery."""

    subscription_id: UUID


class TestDeliveryResponse(BaseModel):
    """Response model for test webhook delivery."""

    delivery_id: str
    status: str
    message: str


def generate_secret() -> str:
    """Generate a secure random secret for HMAC signing."""
    return secrets.token_urlsafe(32)


def generate_hmac_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


@router.post("/subscriptions", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_subscription(
    subscription: WebhookSubscriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> WebhookSubscription:
    """Create a new webhook subscription.

    - **target_url**: HTTPS URL to receive webhook events
    - **events**: List of event types to subscribe to (e.g., ["post.created", "comment.created"])
    - **filters**: Optional filters (e.g., {"scope": ["public"], "authors": ["user_id"]})
    - **lease_expires_at**: Optional expiration time for auto-cleanup
    """
    secret = generate_secret()

    webhook_sub = WebhookSubscription(
        service="social",
        target_url=subscription.target_url,
        secret=secret,
        events=subscription.events,
        filters=subscription.filters or {},
        active="true",
        lease_expires_at=subscription.lease_expires_at,
    )

    db.add(webhook_sub)
    db.commit()
    db.refresh(webhook_sub)

    return webhook_sub


@router.get("/subscriptions", response_model=WebhookSubscriptionList)
async def list_webhook_subscriptions(
    active: str | None = None,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> dict[str, Any]:
    """List all webhook subscriptions.

    - **active**: Optional filter by active status ("true" or "false")
    """
    query = db.query(WebhookSubscription).filter(
        WebhookSubscription.service == "social"
    )

    if active is not None:
        query = query.filter(WebhookSubscription.active == active)

    subscriptions = query.order_by(WebhookSubscription.created_at.desc()).all()

    return {
        "subscriptions": subscriptions,
        "total": len(subscriptions),
    }


@router.get("/subscriptions/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> WebhookSubscription:
    """Get a specific webhook subscription by ID."""
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.service == "social",
    ).first()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    return subscription


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> Response:
    """Delete a webhook subscription."""
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.service == "social",
    ).first()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    db.delete(subscription)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test-delivery", response_model=TestDeliveryResponse)
async def test_webhook_delivery(
    test_request: TestDeliveryRequest,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> dict[str, str]:
    """Send a test webhook event to verify the subscription is working.

    - **subscription_id**: ID of the webhook subscription to test
    """
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == test_request.subscription_id,
        WebhookSubscription.service == "social",
    ).first()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    delivery_id = secrets.token_urlsafe(16)
    test_event = {
        "event_type": "test.webhook",
        "delivery_id": delivery_id,
        "timestamp": utcnow().isoformat(),
        "data": {
            "message": "This is a test webhook delivery",
            "subscription_id": str(subscription.id),
        },
    }

    payload = json.dumps(test_event).encode("utf-8")
    signature = generate_hmac_signature(payload, subscription.secret)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                subscription.target_url,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Delivery-Id": delivery_id,
                    "X-Event-Type": "test.webhook",
                    "X-Signature": f"sha256={signature}",
                    "X-Retry": "0",
                    "User-Agent": "SocialMessagingPlatform/1.0",
                },
            )

            if 200 <= response.status_code < 300:
                return {
                    "delivery_id": delivery_id,
                    "status": "success",
                    "message": f"Test webhook delivered successfully (HTTP {response.status_code})",
                }
            return {
                "delivery_id": delivery_id,
                "status": "failed",
                "message": f"Test webhook delivery failed with HTTP {response.status_code}",
            }

    except httpx.TimeoutException:
        return {
            "delivery_id": delivery_id,
            "status": "failed",
            "message": "Test webhook delivery timed out after 10 seconds",
        }
    except Exception as e:
        return {
            "delivery_id": delivery_id,
            "status": "failed",
            "message": f"Test webhook delivery failed: {e}",
        }
