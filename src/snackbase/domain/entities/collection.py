"""Collection entity for dynamic schema definitions.

Collections store metadata about user-created data tables. The schema
defines the fields, types, and constraints for records in the collection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Collection:
    """Collection entity representing a dynamic data table schema.

    Collections are global (not account-scoped) but all data within them
    is automatically scoped by account_id.

    Attributes:
        id: Unique identifier (UUID string).
        name: Collection name (used in API routes).
        schema: JSON schema defining fields, types, and constraints.
        created_at: Timestamp when the collection was created.
        updated_at: Timestamp when the collection was last updated.
    """

    id: str
    name: str
    schema: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate collection data after initialization."""
        if not self.id:
            raise ValueError("Collection ID is required")
        if not self.name:
            raise ValueError("Collection name is required")
        if not isinstance(self.schema, dict):
            raise ValueError("Schema must be a dictionary")
