"""Token types and payload models for the unified authentication system.

Defines the fields and types used in SnackBase tokens (JWT, API Keys, etc.).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TokenType(str, Enum):
    """Supported token types in SnackBase."""

    JWT = "jwt"
    API_KEY = "api_key"
    PERSONAL_TOKEN = "personal_token"
    OAUTH = "oauth"


class TokenPayload(BaseModel):
    """Structure of the data contained within a SnackBase token."""

    model_config = ConfigDict(from_attributes=True)

    version: int = Field(default=1, description="Token format version")
    type: TokenType = Field(..., description="Type of token (jwt, api_key, etc.)")
    user_id: str = Field(..., description="Unique identifier of the user")
    email: str = Field(..., description="User's email address")
    account_id: str = Field(..., description="Account ID the user belongs to")
    role: str = Field(..., description="User's role name")
    permissions: List[str] = Field(default_factory=list, description="List of granted permissions")
    issued_at: int = Field(..., description="Unix timestamp when the token was issued")
    expires_at: Optional[int] = Field(None, description="Unix timestamp when the token expires")
    token_id: str = Field(..., description="Unique identifier for the token (for revocation)")


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user in the system context."""
    user_id: str
    account_id: str
    email: str
    role: str
    token_type: TokenType
    groups: List[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Alias for user_id to maintain compatibility with code expecting user.id."""
        return self.user_id
