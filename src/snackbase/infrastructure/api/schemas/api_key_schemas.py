"""Pydantic schemas for API key operations."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class APIKeyBase(BaseModel):
    """Base schema for API keys."""
    name: Annotated[str, Field(min_length=3, max_length=100)]


class APIKeyCreateRequest(APIKeyBase):
    """Request schema for creating an API key."""
    expires_at: datetime | None = None


class APIKeyCreateResponse(APIKeyBase):
    """Response schema for a newly created API key."""
    id: str
    key: str  # Plaintext key, only returned once
    expires_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyListItem(APIKeyBase):
    """Schema for an item in the API key list."""
    id: str
    key: str  # Masked key
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyListResponse(BaseModel):
    """Response schema for listing API keys."""
    items: list[APIKeyListItem]
    total: int


class APIKeyDetailResponse(APIKeyListItem):
    """Schema for detailed API key information."""
    updated_at: datetime
