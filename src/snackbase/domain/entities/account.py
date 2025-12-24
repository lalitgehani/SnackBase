"""Account entity for multi-tenant isolation.

Accounts represent isolated tenants within the system. Each account has a unique
ID in XX#### format (2 uppercase letters + 4 digits) and a URL-friendly slug.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Account:
    """Account entity representing a tenant in the multi-tenant system.

    Attributes:
        id: Unique identifier in XX#### format (e.g., AB1234).
        slug: URL-friendly identifier (3-32 chars, alphanumeric + hyphens).
        name: Display name for the account.
        created_at: Timestamp when the account was created.
        updated_at: Timestamp when the account was last updated.
    """

    id: str
    slug: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate account data after initialization."""
        if not self.id or len(self.id) != 6:
            raise ValueError("Account ID must be 6 characters (XX####)")
        if not self.slug or len(self.slug) < 3 or len(self.slug) > 32:
            raise ValueError("Slug must be 3-32 characters")
        if not self.name:
            raise ValueError("Name is required")
