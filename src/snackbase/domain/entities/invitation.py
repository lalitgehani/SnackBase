"""Invitation entity for user onboarding.

Invitations allow account admins to invite new users via email.
The invitation includes a secure token that expires after a set period.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Invitation:
    """Invitation entity for inviting users to an account.

    Invitations contain a secure token that the invitee uses to accept
    the invitation and create their account password.

    Attributes:
        id: Unique identifier (UUID string).
        account_id: Foreign key to the account the user is invited to.
        email: Email address of the invited user.
        token: Secure random token for accepting the invitation.
        invited_by: Foreign key to the user who sent the invitation.
        expires_at: Timestamp when the invitation expires.
        accepted_at: Timestamp when the invitation was accepted (nullable).
        email_sent: Whether the invitation email has been sent.
        email_sent_at: Timestamp when the email was sent (nullable).
        created_at: Timestamp when the invitation was created.
    """

    id: str
    account_id: str
    email: str
    token: str
    invited_by: str
    expires_at: datetime
    accepted_at: datetime | None = None
    email_sent: bool = False
    email_sent_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate invitation data after initialization."""
        if not self.id:
            raise ValueError("Invitation ID is required")
        if not self.account_id:
            raise ValueError("Account ID is required")
        if not self.email:
            raise ValueError("Email is required")
        if not self.token:
            raise ValueError("Token is required")
        if not self.invited_by:
            raise ValueError("Invited by user ID is required")

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_accepted(self) -> bool:
        """Check if the invitation has been accepted."""
        return self.accepted_at is not None
