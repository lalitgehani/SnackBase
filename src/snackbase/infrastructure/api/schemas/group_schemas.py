"""Pydantic schemas for Group operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GroupBase(BaseModel):
    """Base schema for Group data."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Group name")
    description: str | None = Field(None, max_length=500, description="Group description")


class GroupCreate(GroupBase):
    """Schema for creating a group."""
    
    account_id: str | None = Field(None, description="Account ID (UUID, optional for superadmins)")


class GroupUpdate(BaseModel):
    """Schema for updating a group."""
    
    name: str | None = Field(None, min_length=1, max_length=100, description="Group name")
    description: str | None = Field(None, max_length=500, description="Group description")


class GroupResponse(GroupBase):
    """Schema for group response."""
    
    id: str = Field(..., description="Group ID")
    account_id: str = Field(..., description="Account ID (UUID)")
    account_code: str = Field(..., description="Human-readable account code in XX#### format (e.g., AB1234)")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserGroupUpdate(BaseModel):
    """Schema for adding/removing users from a group."""
    
    user_id: str = Field(..., description="User ID to add/remove")
