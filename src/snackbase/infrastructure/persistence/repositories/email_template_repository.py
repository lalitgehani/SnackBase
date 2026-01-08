"""Repository for email template persistence operations.

Provides CRUD operations for email templates with account-level fallback to system defaults.
"""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.email_template import EmailTemplateModel


class EmailTemplateRepository:
    """Repository for email template database operations.

    Handles template CRUD with hierarchical resolution (account -> system fallback).
    """

    SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"

    async def get_template(
        self,
        session: AsyncSession,
        account_id: str,
        template_type: str,
        locale: str = "en",
    ) -> EmailTemplateModel | None:
        """Get email template with fallback to system default.

        First tries to find account-specific template, then falls back to system template.

        Args:
            session: Database session.
            account_id: Account ID to search for.
            template_type: Template type (e.g., 'email_verification').
            locale: Language/locale code (default: 'en').

        Returns:
            EmailTemplateModel if found, None otherwise.
        """
        # Try account-specific template first
        result = await session.execute(
            select(EmailTemplateModel).where(
                EmailTemplateModel.account_id == account_id,
                EmailTemplateModel.template_type == template_type,
                EmailTemplateModel.locale == locale,
                EmailTemplateModel.enabled == True,  # noqa: E712
            )
        )
        template = result.scalar_one_or_none()

        # Fall back to system template if not found
        if template is None:
            result = await session.execute(
                select(EmailTemplateModel).where(
                    EmailTemplateModel.account_id == self.SYSTEM_ACCOUNT_ID,
                    EmailTemplateModel.template_type == template_type,
                    EmailTemplateModel.locale == locale,
                    EmailTemplateModel.enabled == True,  # noqa: E712
                )
            )
            template = result.scalar_one_or_none()

        return template

    async def list_templates(
        self,
        session: AsyncSession,
        account_id: str | None = None,
        template_type: str | None = None,
        locale: str | None = None,
        enabled: bool | None = None,
    ) -> Sequence[EmailTemplateModel]:
        """List email templates with optional filters.

        Args:
            session: Database session.
            account_id: Optional filter by account ID.
            template_type: Optional filter by template type.
            locale: Optional filter by locale.
            enabled: Optional filter by enabled status.

        Returns:
            List of email templates matching filters.
        """
        query = select(EmailTemplateModel)

        if account_id is not None:
            query = query.where(EmailTemplateModel.account_id == account_id)
        if template_type is not None:
            query = query.where(EmailTemplateModel.template_type == template_type)
        if locale is not None:
            query = query.where(EmailTemplateModel.locale == locale)
        if enabled is not None:
            query = query.where(EmailTemplateModel.enabled == enabled)

        query = query.order_by(
            EmailTemplateModel.account_id,
            EmailTemplateModel.template_type,
            EmailTemplateModel.locale,
        )

        result = await session.execute(query)
        return result.scalars().all()

    async def get_by_id(
        self,
        session: AsyncSession,
        template_id: str,
    ) -> EmailTemplateModel | None:
        """Get email template by ID.

        Args:
            session: Database session.
            template_id: Template ID.

        Returns:
            EmailTemplateModel if found, None otherwise.
        """
        result = await session.execute(
            select(EmailTemplateModel).where(EmailTemplateModel.id == template_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        template: EmailTemplateModel,
    ) -> EmailTemplateModel:
        """Create a new email template.

        Args:
            session: Database session.
            template: Email template to create.

        Returns:
            Created email template.
        """
        session.add(template)
        await session.flush()
        await session.refresh(template)
        return template

    async def update(
        self,
        session: AsyncSession,
        template: EmailTemplateModel,
    ) -> EmailTemplateModel:
        """Update an existing email template.

        Args:
            session: Database session.
            template: Email template to update.

        Returns:
            Updated email template.
        """
        await session.flush()
        await session.refresh(template)
        return template

    async def delete(
        self,
        session: AsyncSession,
        template_id: str,
    ) -> bool:
        """Delete an email template.

        Args:
            session: Database session.
            template_id: Template ID to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            ValueError: If attempting to delete a builtin template.
        """
        template = await self.get_by_id(session, template_id)
        if template is None:
            return False

        if template.is_builtin:
            raise ValueError("Cannot delete builtin email templates")

        await session.delete(template)
        await session.flush()
        return True
