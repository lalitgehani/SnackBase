"""User entity for authentication and account membership.

Users belong to accounts and are uniquely identified by (account_id, email).
Each user has a role that defines their permissions within the account.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class User:
    """User entity representing an authenticated user within an account.

    Users are scoped to accounts - the same email can exist in multiple accounts
    with different passwords and roles.

    Attributes:
        id: Unique identifier (UUID string).
        account_id: Foreign key to the account this user belongs to.
        email: User's email address (unique within account).
        password_hash: Hashed password (never store plaintext).
        role_id: Foreign key to the user's role.
        is_active: Whether the user can log in.
        auth_provider: Authentication provider type ('password', 'oauth', 'saml').
        auth_provider_name: Specific provider name (e.g., 'google', 'github').
        external_id: External provider's user ID for identity linking.
        external_email: Email from external provider (may differ from local email).
        profile_data: Additional profile data from external provider.
        created_at: Timestamp when the user was created.
        updated_at: Timestamp when the user was last updated.
        last_login: Timestamp of last successful login (nullable).
    """

    id: str
    account_id: str
    email: str
    password_hash: str
    role_id: int
    is_active: bool = True
    auth_provider: str = "password"
    auth_provider_name: str | None = None
    external_id: str | None = None
    external_email: str | None = None
    profile_data: dict | None = None
    email_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: datetime | None = None

    def __post_init__(self) -> None:
        """Validate user data after initialization."""
        if not self.id:
            raise ValueError("User ID is required")
        if not self.account_id:
            raise ValueError("Account ID is required")
        if not self.email:
            raise ValueError("Email is required")
        if not self.password_hash:
            raise ValueError("Password hash is required")
        
        valid_providers = {"password", "oauth", "saml"}
        if self.auth_provider not in valid_providers:
            raise ValueError(f"Invalid auth_provider. Must be one of {valid_providers}")
