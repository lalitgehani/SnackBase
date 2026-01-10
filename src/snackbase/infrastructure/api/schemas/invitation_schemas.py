"""Pydantic schemas for invitation API endpoints."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InvitationStatus(str, Enum):
    """Invitation status enum."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InvitationCreateRequest(BaseModel):
    """Request schema for creating an invitation."""

    email: EmailStr = Field(..., description="Email address of the user to invite")
    role_id: str | None = Field(
        None, description="Optional role ID to assign to the user"
    )
    groups: list[str] | None = Field(
        None, description="Optional list of group IDs to add the user to"
    )


class InvitationResponse(BaseModel):
    """Response schema for invitation details."""

    id: str = Field(..., description="Invitation ID")
    account_id: str = Field(..., description="Account ID (UUID)")
    account_code: str = Field(..., description="Human-readable account code in XX#### format (e.g., AB1234)")
    email: str = Field(..., description="Email address of the invited user")
    invited_by: str = Field(..., description="User ID of the inviter")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    accepted_at: datetime | None = Field(
        None, description="Acceptance timestamp (if accepted)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    email_sent: bool = Field(False, description="Whether the invitation email has been sent")
    email_sent_at: datetime | None = Field(None, description="Timestamp when the email was sent")
    status: InvitationStatus = Field(..., description="Current invitation status")

    model_config = ConfigDict(from_attributes=True)


class InvitationAcceptRequest(BaseModel):
    """Request schema for accepting an invitation."""

    password: str = Field(
        ...,
        min_length=8,
        description="Password for the new user account",
    )


class InvitationListResponse(BaseModel):
    """Response schema for listing invitations."""

    invitations: list[InvitationResponse] = Field(
        ..., description="List of invitations"
    )
    total: int = Field(..., description="Total number of invitations")
