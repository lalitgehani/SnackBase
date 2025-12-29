"""Account entity for multi-tenant isolation.

Accounts represent isolated tenants within the system. Each account has a unique
UUID as the primary key and a human-readable account code in XX#### format.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Account:
    """Account entity representing a tenant in the multi-tenant system.

    Attributes:
        id: Unique identifier (UUID string, 36 characters).
        account_code: Human-readable account code in XX#### format (e.g., AB1234).
        slug: URL-friendly identifier (3-32 chars, alphanumeric + hyphens).
        name: Display name for the account.
        created_at: Timestamp when the account was created.
        updated_at: Timestamp when the account was last updated.
    """

    id: str
    account_code: str
    slug: str
    name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate account data after initialization."""
        # Validate UUID format (36 characters with hyphens)
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        if not self.id or not uuid_pattern.match(self.id):
            raise ValueError("Account ID must be a valid UUID (36 characters)")

        # Validate account code format (XX####)
        code_pattern = re.compile(r"^[A-Z]{2}\d{4}$")
        if not self.account_code or not code_pattern.match(self.account_code):
            raise ValueError("Account code must be in XX#### format (e.g., AB1234)")

        # Validate slug
        if not self.slug or len(self.slug) < 3 or len(self.slug) > 32:
            raise ValueError("Slug must be 3-32 characters")

        # Validate name
        if not self.name:
            raise ValueError("Name is required")
