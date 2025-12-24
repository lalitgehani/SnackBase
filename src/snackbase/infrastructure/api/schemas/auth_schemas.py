"""Pydantic schemas for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for account registration."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")
    account_name: str = Field(
        ..., min_length=1, max_length=255, description="Display name for the account"
    )
    account_slug: str | None = Field(
        None,
        min_length=3,
        max_length=32,
        description="URL-friendly account identifier (auto-generated if not provided)",
    )


class AccountResponse(BaseModel):
    """Account information in auth responses."""

    id: str = Field(..., description="Account ID in XX#### format")
    slug: str = Field(..., description="URL-friendly account identifier")
    name: str = Field(..., description="Display name for the account")
    created_at: datetime = Field(..., description="When the account was created")

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    """User information in auth responses."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User's email address")
    role: str = Field(..., description="User's role name")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="When the user was created")

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Response for successful authentication (login/register)."""

    token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    account: AccountResponse = Field(..., description="Account information")
    user: UserResponse = Field(..., description="User information")


class ValidationErrorDetail(BaseModel):
    """Detail for a single validation error."""

    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Human-readable error message")
    code: str | None = Field(None, description="Machine-readable error code")


class ValidationErrorResponse(BaseModel):
    """Response for validation errors."""

    error: str = Field(..., description="Error type")
    details: list[ValidationErrorDetail] = Field(..., description="List of validation errors")


class ConflictErrorResponse(BaseModel):
    """Response for conflict errors (duplicate resources)."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    field: str = Field(..., description="Field that caused the conflict")
