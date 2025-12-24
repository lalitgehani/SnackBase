"""Role entity for authorization.

Roles are global (not account-scoped) and define permissions for users.
Default roles are 'admin' and 'user'.
"""

from dataclasses import dataclass


@dataclass
class Role:
    """Role entity for user authorization.

    Roles are global and shared across all accounts. They define the base
    permission level for users.

    Attributes:
        id: Unique identifier (auto-incrementing integer).
        name: Role name (e.g., 'admin', 'user').
        description: Optional description of the role's purpose.
    """

    id: int
    name: str
    description: str | None = None

    def __post_init__(self) -> None:
        """Validate role data after initialization."""
        if not self.name:
            raise ValueError("Role name is required")
