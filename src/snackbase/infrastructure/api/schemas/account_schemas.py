"""Pydantic schemas for account management endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class AccountListItem(BaseModel):
    """Account item in list view with statistics."""

    id: str = Field(..., description="Account ID in XX#### format")
    slug: str = Field(..., description="URL-friendly account identifier")
    name: str = Field(..., description="Display name for the account")
    created_at: datetime = Field(..., description="When the account was created")
    user_count: int = Field(..., description="Number of users in this account")
    status: str = Field(default="active", description="Account status")

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    """Paginated response for account list."""

    items: list[AccountListItem] = Field(..., description="List of accounts")
    total: int = Field(..., description="Total number of accounts")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class AccountDetailResponse(BaseModel):
    """Detailed account information."""

    id: str = Field(..., description="Account ID in XX#### format")
    slug: str = Field(..., description="URL-friendly account identifier")
    name: str = Field(..., description="Display name for the account")
    created_at: datetime = Field(..., description="When the account was created")
    updated_at: datetime = Field(..., description="When the account was last updated")
    user_count: int = Field(..., description="Number of users in this account")
    collections_used: list[str] = Field(
        default_factory=list, description="Collections used by this account"
    )

    model_config = {"from_attributes": True}


class CreateAccountRequest(BaseModel):
    """Request body for creating a new account."""

    name: str = Field(..., min_length=1, max_length=255, description="Account name")
    slug: str | None = Field(
        None,
        min_length=3,
        max_length=32,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly identifier (auto-generated if not provided)",
    )


class UpdateAccountRequest(BaseModel):
    """Request body for updating an account."""

    name: str = Field(..., min_length=1, max_length=255, description="Account name")


class AccountUserResponse(BaseModel):
    """User information in account users list."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    role: str = Field(..., description="User role name")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="When the user was created")

    model_config = {"from_attributes": True}


class AccountUsersResponse(BaseModel):
    """Paginated response for account users list."""

    items: list[AccountUserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
