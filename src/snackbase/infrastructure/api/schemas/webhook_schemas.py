"""Pydantic schemas for webhook API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookCreateRequest(BaseModel):
    """Request body for creating a webhook."""

    url: str = Field(..., min_length=1, max_length=2048, description="Destination URL for webhook HTTP POST")
    collection: str = Field(..., min_length=1, max_length=100, description="Collection name to watch")
    events: list[str] = Field(
        ...,
        min_length=1,
        description="Events to fire on: create, update, delete",
    )
    secret: str | None = Field(
        default=None,
        max_length=100,
        description="HMAC-SHA256 signing secret (auto-generated if omitted)",
    )
    filter: str | None = Field(
        default=None,
        description="Optional rule expression to conditionally fire webhook",
    )
    enabled: bool = Field(default=True, description="Whether the webhook is active")
    headers: dict[str, str] | None = Field(
        default=None,
        description="Optional custom HTTP headers to include in delivery",
    )

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        """Validate event names."""
        valid = {"create", "update", "delete"}
        for event in v:
            if event not in valid:
                raise ValueError(f"Invalid event '{event}'. Must be one of: {', '.join(sorted(valid))}")
        return list(set(v))  # deduplicate


class WebhookUpdateRequest(BaseModel):
    """Request body for updating a webhook (all fields optional)."""

    url: str | None = Field(default=None, min_length=1, max_length=2048)
    collection: str | None = Field(default=None, min_length=1, max_length=100)
    events: list[str] | None = Field(default=None, min_length=1)
    filter: str | None = Field(default=None)
    enabled: bool | None = Field(default=None)
    headers: dict[str, str] | None = Field(default=None)

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str] | None) -> list[str] | None:
        """Validate event names."""
        if v is None:
            return v
        valid = {"create", "update", "delete"}
        for event in v:
            if event not in valid:
                raise ValueError(f"Invalid event '{event}'. Must be one of: {', '.join(sorted(valid))}")
        return list(set(v))


class WebhookResponse(BaseModel):
    """Webhook details response (secret NOT included)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    url: str
    collection: str
    events: list[str]
    filter: str | None
    enabled: bool
    headers: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None


class WebhookCreateResponse(WebhookResponse):
    """Webhook creation response — includes secret (shown ONCE only)."""

    secret: str = Field(..., description="Signing secret — save this, it will never be shown again")


class WebhookListResponse(BaseModel):
    """Paginated list of webhooks."""

    items: list[WebhookResponse]
    total: int


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery details."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    webhook_id: str
    event: str
    payload: dict[str, Any]
    response_status: int | None
    response_body: str | None
    attempt_number: int
    delivered_at: datetime | None
    next_retry_at: datetime | None
    status: str
    created_at: datetime


class WebhookDeliveryListResponse(BaseModel):
    """Paginated list of webhook deliveries."""

    items: list[WebhookDeliveryResponse]
    total: int


class WebhookTestResponse(BaseModel):
    """Response for the test webhook endpoint."""

    success: bool
    status_code: int | None
    response_body: str | None
    error: str | None = None
