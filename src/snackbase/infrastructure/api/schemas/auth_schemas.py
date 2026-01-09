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


class LoginRequest(BaseModel):
    """Request body for user login."""

    account: str = Field(
        ...,
        min_length=1,
        description="Account identifier (slug or ID in XX#### format)",
    )
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")


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


class RefreshRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str = Field(..., min_length=1, description="JWT refresh token")


class TokenRefreshResponse(BaseModel):
    """Response for successful token refresh."""

    token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class OAuthAuthorizeRequest(BaseModel):
    """Request body for starting an OAuth flow."""

    account: str | None = Field(None, description="Account identifier (slug or ID)")
    account_name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Display name for the new account (used when creating a new account)",
    )
    redirect_uri: str = Field(..., description="URI to redirect to after OAuth completion")
    state: str | None = Field(
        None, description="Optional state for CSRF (auto-generated if missing)"
    )


class OAuthAuthorizeResponse(BaseModel):
    """Response for OAuth authorization initiation."""

    authorization_url: str = Field(..., description="URL to redirect the user to")
    state: str = Field(..., description="The state token used for this flow")
    provider: str = Field(..., description="The provider name")


class OAuthCallbackRequest(BaseModel):
    """Request body for OAuth callback completion."""

    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="State token for CSRF protection")
    redirect_uri: str = Field(..., description="Original redirect URI used in authorize request")



class OAuthCallbackResponse(AuthResponse):
    """Response for successful OAuth callback authentication."""

    is_new_user: bool = Field(..., description="Whether a new user was created")
    is_new_account: bool = Field(..., description="Whether a new account was created")


class SendVerificationRequest(BaseModel):
    """Request body for sending verification email."""

    email: EmailStr | None = Field(
        None,
        description="User's email address. If not provided, the authenticated user's email is used.",
    )


class VerifyEmailRequest(BaseModel):
    """Request body for verifying email with token."""

    token: str = Field(..., description="Verification token")

