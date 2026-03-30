"""Repositories for webhook database operations."""

from datetime import UTC, datetime
from typing import Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.webhook import (
    WebhookDeliveryModel,
    WebhookModel,
)


class WebhookRepository:
    """Repository for webhook configuration database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, webhook: WebhookModel) -> WebhookModel:
        """Create a new webhook."""
        self.session.add(webhook)
        await self.session.flush()
        return webhook

    async def get_by_id(self, webhook_id: str) -> WebhookModel | None:
        """Get a webhook by ID."""
        result = await self.session.execute(
            select(WebhookModel).where(WebhookModel.id == webhook_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_account(
        self, webhook_id: str, account_id: str
    ) -> WebhookModel | None:
        """Get a webhook by ID scoped to an account."""
        result = await self.session.execute(
            select(WebhookModel).where(
                and_(
                    WebhookModel.id == webhook_id,
                    WebhookModel.account_id == account_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_account(self, account_id: str) -> Sequence[WebhookModel]:
        """List all webhooks for an account."""
        result = await self.session.execute(
            select(WebhookModel)
            .where(WebhookModel.account_id == account_id)
            .order_by(WebhookModel.created_at.desc())
        )
        return result.scalars().all()

    async def list_enabled_by_collection(
        self, account_id: str, collection: str
    ) -> Sequence[WebhookModel]:
        """List enabled webhooks for a specific account+collection."""
        result = await self.session.execute(
            select(WebhookModel).where(
                and_(
                    WebhookModel.account_id == account_id,
                    WebhookModel.collection == collection,
                    WebhookModel.enabled == True,  # noqa: E712
                )
            )
        )
        return result.scalars().all()

    async def update(self, webhook_id: str, values: dict) -> bool:
        """Update a webhook by ID."""
        values["updated_at"] = datetime.now(UTC)
        result = await self.session.execute(
            update(WebhookModel)
            .where(WebhookModel.id == webhook_id)
            .values(**values)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def delete(self, webhook_id: str) -> bool:
        """Hard-delete a webhook by ID."""
        webhook = await self.get_by_id(webhook_id)
        if webhook is None:
            return False
        await self.session.delete(webhook)
        await self.session.flush()
        return True

    async def count_by_account(self, account_id: str) -> int:
        """Count webhooks for an account."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(WebhookModel.id)).where(
                WebhookModel.account_id == account_id
            )
        )
        return result.scalar_one() or 0


class WebhookDeliveryRepository:
    """Repository for webhook delivery tracking database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, delivery: WebhookDeliveryModel) -> WebhookDeliveryModel:
        """Create a new delivery record."""
        self.session.add(delivery)
        await self.session.flush()
        return delivery

    async def get_by_id(self, delivery_id: str) -> WebhookDeliveryModel | None:
        """Get a delivery record by ID."""
        result = await self.session.execute(
            select(WebhookDeliveryModel).where(WebhookDeliveryModel.id == delivery_id)
        )
        return result.scalar_one_or_none()

    async def list_by_webhook(
        self,
        webhook_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[WebhookDeliveryModel], int]:
        """List delivery records for a webhook with pagination.

        Returns:
            Tuple of (deliveries, total_count).
        """
        from sqlalchemy import func

        count_result = await self.session.execute(
            select(func.count(WebhookDeliveryModel.id)).where(
                WebhookDeliveryModel.webhook_id == webhook_id
            )
        )
        total = count_result.scalar_one() or 0

        result = await self.session.execute(
            select(WebhookDeliveryModel)
            .where(WebhookDeliveryModel.webhook_id == webhook_id)
            .order_by(WebhookDeliveryModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all(), total

    async def update_status(
        self,
        delivery_id: str,
        status: str,
        response_status: int | None = None,
        response_body: str | None = None,
        delivered_at: datetime | None = None,
        next_retry_at: datetime | None = None,
        attempt_number: int | None = None,
    ) -> bool:
        """Update the status of a delivery record."""
        values: dict = {"status": status}
        if response_status is not None:
            values["response_status"] = response_status
        if response_body is not None:
            values["response_body"] = response_body[:5000]
        if delivered_at is not None:
            values["delivered_at"] = delivered_at
        if next_retry_at is not None:
            values["next_retry_at"] = next_retry_at
        if attempt_number is not None:
            values["attempt_number"] = attempt_number

        result = await self.session.execute(
            update(WebhookDeliveryModel)
            .where(WebhookDeliveryModel.id == delivery_id)
            .values(**values)
        )
        await self.session.flush()
        return result.rowcount > 0
