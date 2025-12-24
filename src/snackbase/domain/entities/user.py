"""User entity for authentication and account membership.

Users belong to accounts and are uniquely identified by (account_id, email).
Each user has a role that defines their permissions within the account.
"""

from dataclasses import dataclass, field
from datetime import datetime


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
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
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
