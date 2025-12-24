"""Permission entity for role-based access control.

Permissions define access rules for collections, linking roles to CRUD operations.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class OperationRule:
    """Rule for a single CRUD operation.

    Attributes:
        rule: Expression string (e.g., "true", "user.id == record.owner_id").
        fields: List of allowed fields or "*" for all fields.
    """

    rule: str
    fields: list[str] | str = "*"

    def __post_init__(self) -> None:
        """Validate operation rule after initialization."""
        if not self.rule:
            raise ValueError("Rule expression is required")
        if self.fields != "*" and not isinstance(self.fields, list):
            raise ValueError("Fields must be '*' or a list of field names")


@dataclass
class PermissionRules:
    """Rules for all CRUD operations.

    Each operation is optional - if None, that operation is not permitted.

    Attributes:
        create: Rule for create operations.
        read: Rule for read operations.
        update: Rule for update operations.
        delete: Rule for delete operations.
    """

    create: OperationRule | None = None
    read: OperationRule | None = None
    update: OperationRule | None = None
    delete: OperationRule | None = None

    def to_dict(self) -> dict:
        """Convert rules to dictionary format for JSON serialization."""
        result = {}
        if self.create:
            result["create"] = {"rule": self.create.rule, "fields": self.create.fields}
        if self.read:
            result["read"] = {"rule": self.read.rule, "fields": self.read.fields}
        if self.update:
            result["update"] = {"rule": self.update.rule, "fields": self.update.fields}
        if self.delete:
            result["delete"] = {"rule": self.delete.rule, "fields": self.delete.fields}
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "PermissionRules":
        """Create PermissionRules from dictionary."""
        return cls(
            create=OperationRule(**data["create"]) if data.get("create") else None,
            read=OperationRule(**data["read"]) if data.get("read") else None,
            update=OperationRule(**data["update"]) if data.get("update") else None,
            delete=OperationRule(**data["delete"]) if data.get("delete") else None,
        )


@dataclass
class Permission:
    """Permission entity for access control.

    Links a role to a collection with specific CRUD operation rules.
    Multiple permissions can exist for the same collection (evaluated with OR logic).

    Attributes:
        role_id: Role this permission applies to.
        collection: Collection name (* for all collections).
        rules: CRUD operation rules.
        id: Unique identifier (auto-generated).
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    role_id: int
    collection: str
    rules: PermissionRules
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate permission after initialization."""
        if not self.collection:
            raise ValueError("Collection name is required")
        if self.role_id <= 0:
            raise ValueError("Role ID must be a positive integer")
