"""SQLAlchemy model for the invitations table.

Invitations allow account admins to invite new users via email.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class InvitationModel(Base):
    """SQLAlchemy model for the invitations table.

    Invitations contain a secure token that the invitee uses to accept
    the invitation and create their account password.

    Attributes:
        id: Primary key (UUID string).
        account_id: Foreign key to accounts table.
        email: Email address of the invited user.
        token: Secure random token for accepting the invitation.
        invited_by: Foreign key to users table.
        expires_at: Timestamp when the invitation expires.
        accepted_at: Timestamp when the invitation was accepted.
        created_at: Timestamp when the invitation was created.
    """

    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Invitation ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Email address of the invited user",
    )
    token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Secure random token for accepting invitation",
    )
    invited_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        comment="Foreign key to users table (inviter)",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Timestamp when the invitation expires",
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when the invitation was accepted",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    account: Mapped["AccountModel"] = relationship(  # noqa: F821
        "AccountModel",
        back_populates="invitations",
    )
    inviter: Mapped["UserModel"] = relationship(  # noqa: F821
        "UserModel",
        back_populates="invitations_sent",
    )

    __table_args__ = (
        Index("ix_invitations_account_email", "account_id", "email"),
    )


    def __repr__(self) -> str:
        return f"<Invitation(id={self.id}, email={self.email}, account_id={self.account_id})>"
