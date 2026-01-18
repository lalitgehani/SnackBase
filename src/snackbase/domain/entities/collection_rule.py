"""Collection rule entity for row-level security.

Collection rules define access control for collections using database-centric
filtering. Each collection has one rule set with 5 operations: list, view,
create, update, delete.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json


@dataclass
class CollectionRule:
    """Collection rule entity for database-centric row-level security.

    Each collection has one rule set defining access control for 5 operations.
    Rules can be:
    - None (null): Locked - only superadmin can access
    - "" (empty string): Public - anyone can access
    - "expression": Custom SQL filter expression

    Attributes:
        id: Unique identifier (UUID string).
        collection_id: Foreign key to collections table.
        list_rule: Filter expression for listing records.
        view_rule: Filter expression for viewing single record.
        create_rule: Validation expression for creating records.
        update_rule: Filter/validation expression for updates.
        delete_rule: Filter expression for deletions.
        list_fields: Fields visible in list operations ('*' or JSON array).
        view_fields: Fields visible in view operations ('*' or JSON array).
        create_fields: Fields allowed in create requests ('*' or JSON array).
        update_fields: Fields allowed in update requests ('*' or JSON array).
        created_at: Timestamp when the rule was created.
        updated_at: Timestamp when the rule was last updated.
    """

    id: str
    collection_id: str
    list_rule: str | None = None
    view_rule: str | None = None
    create_rule: str | None = None
    update_rule: str | None = None
    delete_rule: str | None = None
    list_fields: str = "*"
    view_fields: str = "*"
    create_fields: str = "*"
    update_fields: str = "*"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate collection rule after initialization."""
        if not self.id:
            raise ValueError("Collection rule ID is required")
        if not self.collection_id:
            raise ValueError("Collection ID is required")

        # Validate rule values (must be None, "", or non-empty string)
        for operation in ["list", "view", "create", "update", "delete"]:
            rule_value = getattr(self, f"{operation}_rule")
            if rule_value is not None and not isinstance(rule_value, str):
                raise ValueError(f"{operation}_rule must be None or a string")

        # Validate field values (must be '*' or valid JSON array string)
        for operation in ["list", "view", "create", "update"]:
            field_value = getattr(self, f"{operation}_fields")
            if not isinstance(field_value, str):
                raise ValueError(f"{operation}_fields must be a string")
            if field_value != "*":
                try:
                    parsed = json.loads(field_value)
                    if not isinstance(parsed, list):
                        raise ValueError(
                            f"{operation}_fields must be '*' or a JSON array string"
                        )
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"{operation}_fields must be '*' or valid JSON: {e}"
                    ) from e

    def is_locked(self, operation: str) -> bool:
        """Check if an operation is locked (only superadmin can access).

        Args:
            operation: Operation name (list, view, create, update, delete).

        Returns:
            True if the operation is locked (rule is None).
        """
        rule_value = getattr(self, f"{operation}_rule", None)
        return rule_value is None

    def is_public(self, operation: str) -> bool:
        """Check if an operation is public (anyone can access).

        Args:
            operation: Operation name (list, view, create, update, delete).

        Returns:
            True if the operation is public (rule is empty string).
        """
        rule_value = getattr(self, f"{operation}_rule", None)
        return rule_value == ""

    def has_custom_rule(self, operation: str) -> bool:
        """Check if an operation has a custom expression.

        Args:
            operation: Operation name (list, view, create, update, delete).

        Returns:
            True if the operation has a custom expression (non-empty string).
        """
        rule_value = getattr(self, f"{operation}_rule", None)
        return isinstance(rule_value, str) and rule_value != ""

    def get_rule(self, operation: str) -> str | None:
        """Get the rule expression for an operation.

        Args:
            operation: Operation name (list, view, create, update, delete).

        Returns:
            Rule expression or None if locked.
        """
        return getattr(self, f"{operation}_rule", None)

    def get_fields(self, operation: str) -> str:
        """Get the field list for an operation.

        Args:
            operation: Operation name (list, view, create, update).

        Returns:
            Field list ('*' or JSON array string).
        """
        return getattr(self, f"{operation}_fields", "*")
