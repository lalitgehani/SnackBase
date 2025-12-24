"""Group entity for user organization within accounts.

Groups allow organizing users within an account for permission management.
Users can belong to multiple groups (many-to-many relationship).
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Group:
    """Group entity for organizing users within an account.

    Groups are account-scoped and can be used in permission rules
    to grant access based on group membership.

    Attributes:
        id: Unique identifier (UUID string).
        account_id: Foreign key to the account this group belongs to.
        name: Group name (unique within account).
        description: Optional description of the group's purpose.
        created_at: Timestamp when the group was created.
        updated_at: Timestamp when the group was last updated.
    """

    id: str
    account_id: str
    name: str
    description: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate group data after initialization."""
        if not self.id:
            raise ValueError("Group ID is required")
        if not self.account_id:
            raise ValueError("Account ID is required")
        if not self.name:
            raise ValueError("Group name is required")
