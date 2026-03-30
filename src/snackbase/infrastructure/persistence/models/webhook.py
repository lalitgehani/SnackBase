"""SQLAlchemy models for webhooks.

Outbound webhooks allow developers to configure HTTP callbacks that fire
when record events occur (create, update, delete).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class WebhookModel(Base):
    """SQLAlchemy model for the webhooks table.

    Attributes:
        id: Primary key (UUID string).
        account_id: Foreign key to accounts table.
        url: Destination URL for the webhook HTTP POST.
        collection: Collection name to watch (e.g., "posts").
        events: JSON list of events to fire on (["create","update","delete"]).
        secret: HMAC-SHA256 signing secret (stored plaintext, only returned once).
        filter: Optional rule expression to conditionally fire the webhook.
        enabled: Whether the webhook is active.
        headers: Optional custom HTTP headers to include in delivery.
        created_at: Timestamp when the webhook was created.
        updated_at: Timestamp when the webhook was last updated.
        created_by: User ID of who created the webhook.
    """

    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Webhook ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        comment="Destination URL for webhook HTTP POST",
    )
    collection: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Collection name to watch",
    )
    events: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        comment="JSON list of events: create, update, delete",
    )
    secret: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="HMAC-SHA256 signing secret (plaintext, only returned at creation)",
    )
    filter: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional rule expression to conditionally fire webhook",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        comment="Whether the webhook is active",
    )
    headers: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Optional custom HTTP headers to include in delivery",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="User ID of who created the webhook",
    )

    # Relationships
    deliveries: Mapped[list["WebhookDeliveryModel"]] = relationship(
        "WebhookDeliveryModel",
        back_populates="webhook",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, url={self.url}, collection={self.collection})>"


class WebhookDeliveryModel(Base):
    """SQLAlchemy model for the webhook_deliveries table.

    Tracks each delivery attempt for a webhook, including retries.

    Attributes:
        id: Primary key (UUID string).
        webhook_id: Foreign key to webhooks table.
        event: Event type that triggered this delivery (e.g., "records.create").
        payload: Full JSON payload that was/will be sent.
        response_status: HTTP response status code (null if not yet delivered).
        response_body: Truncated response body (max 5000 chars).
        attempt_number: Which attempt this is (1 = first try).
        delivered_at: When the delivery succeeded (null if not delivered).
        next_retry_at: When the next retry is scheduled (null if done).
        status: Delivery status (pending, delivered, failed, retrying).
        created_at: When this delivery record was created.
    """

    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Delivery ID (UUID)",
    )
    webhook_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to webhooks table",
    )
    event: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Event type that triggered this delivery",
    )
    payload: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        comment="Full JSON payload sent to the webhook URL",
    )
    response_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="HTTP response status code from the webhook endpoint",
    )
    response_body: Mapped[str | None] = mapped_column(
        String(5000),
        nullable=True,
        comment="Truncated response body (max 5000 chars)",
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Attempt number (1 = first try)",
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the delivery succeeded",
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When the next retry is scheduled",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
        comment="Delivery status: pending, delivered, failed, retrying",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this delivery record was created",
    )

    # Relationships
    webhook: Mapped["WebhookModel"] = relationship("WebhookModel", back_populates="deliveries")

    def __repr__(self) -> str:
        return f"<WebhookDelivery(id={self.id}, webhook_id={self.webhook_id}, status={self.status})>"
