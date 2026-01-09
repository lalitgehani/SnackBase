"""Pydantic schemas for User CRUD operations.

These schemas are used by the users_router for creating, updating, and
displaying user information in the admin UI.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator


class UserCreateRequest(BaseModel):
    """Request schema for creating a new user.

    This is used by superadmins to create users in any account.
    For OAuth/SAML users, password is optional and will be auto-generated.
    """

    email: EmailStr = Field(..., description="User's email address")
    password: SecretStr | None = Field(None, min_length=1, description="User's password (optional for OAuth/SAML users)")
    account_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Account ID (UUID)",
    )
    role_id: int = Field(..., ge=1, description="Role ID (must exist)")
    is_active: bool = Field(True, description="Whether the user can log in")
    auth_provider: str = Field("password", description="Authentication provider type ('password', 'oauth', 'saml')")
    auth_provider_name: str | None = Field(None, description="Specific provider name (e.g., 'google', 'github')")
    external_id: str | None = Field(None, description="External provider's user ID")
    external_email: str | None = Field(None, description="Email from external provider")
    profile_data: dict | None = Field(None, description="Additional profile data from external provider")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: SecretStr | None) -> SecretStr | None:
        """Validate password strength.

        This is a placeholder - actual validation happens in the router
        using the PasswordValidator service to provide detailed error messages.
        Password can be None for OAuth/SAML users (will be auto-generated).
        """
        if v is None:
            return v
        password = v.get_secret_value()
        if not password:
            raise ValueError("Password cannot be empty")
        return v


class UserUpdateRequest(BaseModel):
    """Request schema for updating a user.

    All fields are optional. Only provided fields will be updated.
    Note: account_id and password cannot be changed via this endpoint.
    """

    email: EmailStr | None = Field(None, description="User's email address")
    role_id: int | None = Field(None, ge=1, description="Role ID (must exist)")
    is_active: bool | None = Field(None, description="Whether the user can log in")
    auth_provider: str | None = Field(None, description="Authentication provider type ('password', 'oauth', 'saml')")
    auth_provider_name: str | None = Field(None, description="Specific provider name (e.g., 'google', 'github')")
    external_id: str | None = Field(None, description="External provider's user ID")
    external_email: str | None = Field(None, description="Email from external provider")
    profile_data: dict | None = Field(None, description="Additional profile data from external provider")


class PasswordResetRequest(BaseModel):
    """Request schema for resetting a user's password.

    Used by superadmins to reset user passwords.
    """

    new_password: SecretStr = Field(..., min_length=1, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: SecretStr) -> SecretStr:
        """Validate password strength.

        This is a placeholder - actual validation happens in the router
        using the PasswordValidator service to provide detailed error messages.
        """
        password = v.get_secret_value()
        if not password:
            raise ValueError("Password cannot be empty")
        return v


class UserResponse(BaseModel):
    """Response schema for a single user.

    Includes user details along with related account and role information.
    """

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User's email address")
    account_id: str = Field(..., description="Account ID (UUID)")
    account_code: str = Field(..., description="Human-readable account code in XX#### format (e.g., AB1234)")
    account_name: str = Field(..., description="Account display name")
    role_id: int = Field(..., description="Role ID")
    role_name: str = Field(..., description="Role name")
    is_active: bool = Field(..., description="Whether the user can log in")
    auth_provider: str = Field(..., description="Authentication provider type ('password', 'oauth', 'saml')")
    auth_provider_name: str | None = Field(None, description="Specific provider name (e.g., 'google', 'github')")
    external_id: str | None = Field(None, description="External provider's user ID")
    external_email: str | None = Field(None, description="Email from external provider")
    profile_data: dict | None = Field(None, description="Additional profile data from external provider")
    email_verified: bool = Field(..., description="Whether the user's email is verified")
    email_verified_at: datetime | None = Field(None, description="When the email was verified")
    created_at: datetime = Field(..., description="When the user was created")
    last_login: datetime | None = Field(None, description="Last successful login")

    model_config = {"from_attributes": True}


class UserListItem(BaseModel):
    """List item schema for a user.

    Used in paginated list responses.
    """

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User's email address")
    account_id: str = Field(..., description="Account ID (UUID)")
    account_code: str = Field(..., description="Human-readable account code in XX#### format (e.g., AB1234)")
    account_name: str = Field(..., description="Account display name")
    role_id: int = Field(..., description="Role ID")
    role_name: str = Field(..., description="Role name")
    is_active: bool = Field(..., description="Whether the user can log in")
    auth_provider: str = Field(..., description="Authentication provider type ('password', 'oauth', 'saml')")
    auth_provider_name: str | None = Field(None, description="Specific provider name (e.g., 'google', 'github')")
    external_id: str | None = Field(None, description="External provider's user ID")
    external_email: str | None = Field(None, description="Email from external provider")
    profile_data: dict | None = Field(None, description="Additional profile data from external provider")
    email_verified: bool = Field(..., description="Whether the user's email is verified")
    email_verified_at: datetime | None = Field(None, description="When the email was verified")
    created_at: datetime = Field(..., description="When the user was created")
    last_login: datetime | None = Field(None, description="Last successful login")

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Response schema for listing users with pagination.

    Attributes:
        total: Total number of users matching the filter.
        items: List of users for the current page.
    """

    total: int = Field(..., ge=0, description="Total number of users")
    items: list[UserListItem] = Field(..., description="List of users")
