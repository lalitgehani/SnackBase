"""Invitation repository for database operations."""

from datetime import datetime, timezone

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import InvitationModel


class InvitationRepository:
    """Repository for invitation database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create_invitation(self, invitation: InvitationModel) -> InvitationModel:
        """Create a new invitation.

        Args:
            invitation: Invitation model to create.

        Returns:
            Created invitation model.
        """
        self.session.add(invitation)
        await self.session.flush()
        return invitation

    async def get_by_token(self, token: str) -> InvitationModel | None:
        """Get an invitation by token.

        Args:
            token: Invitation token.

        Returns:
            Invitation model if found, None otherwise.
        """
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, invitation_id: str) -> InvitationModel | None:
        """Get an invitation by ID.

        Args:
            invitation_id: Invitation ID (UUID string).

        Returns:
            Invitation model if found, None otherwise.
        """
        result = await self.session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        return result.scalar_one_or_none()

    async def list_by_account(
        self,
        account_id: str,
        status: str | None = None,
    ) -> list[InvitationModel]:
        """List invitations for an account.

        Args:
            account_id: Account ID to filter by.
            status: Optional status filter (pending, accepted, expired, cancelled).

        Returns:
            List of invitation models.
        """
        query = select(InvitationModel).where(InvitationModel.account_id == account_id)

        now = datetime.now(timezone.utc)

        if status == "pending":
            # Pending: not accepted and not expired
            query = query.where(
                and_(
                    InvitationModel.accepted_at.is_(None),
                    InvitationModel.expires_at > now,
                )
            )
        elif status == "accepted":
            # Accepted: has accepted_at timestamp
            query = query.where(InvitationModel.accepted_at.isnot(None))
        elif status == "expired":
            # Expired: not accepted and past expiration
            query = query.where(
                and_(
                    InvitationModel.accepted_at.is_(None),
                    InvitationModel.expires_at <= now,
                )
            )
        # Note: "cancelled" status would require a separate field in the model
        # For now, cancelled invitations are deleted from the database

        # Order by created_at descending (newest first)
        query = query.order_by(InvitationModel.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_as_accepted(self, invitation_id: str) -> None:
        """Mark an invitation as accepted.

        Args:
            invitation_id: ID of the invitation to mark as accepted.
        """
        invitation = await self.get_by_id(invitation_id)
        if invitation:
            invitation.accepted_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def cancel_invitation(self, invitation_id: str) -> bool:
        """Cancel (delete) an invitation.

        Args:
            invitation_id: ID of the invitation to cancel.

        Returns:
            True if invitation was deleted, False if not found.
        """
        result = await self.session.execute(
            delete(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def check_pending_invitation_exists(
        self, email: str, account_id: str
    ) -> bool:
        """Check if a pending invitation exists for an email in an account.

        Args:
            email: Email address to check.
            account_id: Account ID to check within.

        Returns:
            True if a pending invitation exists, False otherwise.
        """
        now = datetime.now(timezone.utc)

        result = await self.session.execute(
            select(InvitationModel.id)
            .where(
                and_(
                    InvitationModel.email == email,
                    InvitationModel.account_id == account_id,
                    InvitationModel.accepted_at.is_(None),
                    InvitationModel.expires_at > now,
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
