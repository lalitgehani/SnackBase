"""Collection validation service for schema and field validation.

Provides validation for collection names, schema definitions, and field configurations.
Supports field types: text, number, boolean, datetime, email, url, json, reference.
"""

import re
from dataclasses import dataclass
from enum import Enum


class FieldType(str, Enum):
    """Supported field types for collection schemas."""

    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    EMAIL = "email"
    URL = "url"
    JSON = "json"
    REFERENCE = "reference"


class OnDeleteAction(str, Enum):
    """Valid on_delete actions for reference fields."""

    CASCADE = "cascade"
    SET_NULL = "set_null"
    RESTRICT = "restrict"


# Reserved field names that are auto-added by the system
RESERVED_FIELD_NAMES = frozenset({
    "id",
    "account_id",
    "created_at",
    "created_by",
    "updated_at",
    "updated_by",
})

# Pattern for valid collection and field names
NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


@dataclass
class CollectionValidationError:
    """A single collection validation error."""

    field: str
    message: str
    code: str


class CollectionValidator:
    """Validator for collection creation requests.

    Validates collection names, schema definitions, and individual field configurations.
    """

    # Collection name constraints
    MIN_NAME_LENGTH = 3
    MAX_NAME_LENGTH = 64

    # Field name constraints
    MIN_FIELD_NAME_LENGTH = 1
    MAX_FIELD_NAME_LENGTH = 64

    @classmethod
    def validate_name(cls, name: str) -> list[CollectionValidationError]:
        """Validate a collection name.

        Args:
            name: The collection name to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        if not name:
            errors.append(
                CollectionValidationError(
                    field="name",
                    message="Collection name is required",
                    code="name_required",
                )
            )
            return errors

        if len(name) < cls.MIN_NAME_LENGTH:
            errors.append(
                CollectionValidationError(
                    field="name",
                    message=f"Collection name must be at least {cls.MIN_NAME_LENGTH} characters",
                    code="name_too_short",
                )
            )

        if len(name) > cls.MAX_NAME_LENGTH:
            errors.append(
                CollectionValidationError(
                    field="name",
                    message=f"Collection name must be at most {cls.MAX_NAME_LENGTH} characters",
                    code="name_too_long",
                )
            )

        if not NAME_PATTERN.match(name):
            errors.append(
                CollectionValidationError(
                    field="name",
                    message="Collection name must start with a letter and contain only alphanumeric characters and underscores",
                    code="name_invalid_format",
                )
            )

        return errors

    @classmethod
    def validate_field_name(cls, name: str, field_index: int) -> list[CollectionValidationError]:
        """Validate a field name.

        Args:
            name: The field name to validate.
            field_index: Index of the field in the schema (for error messages).

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        field_path = f"schema[{field_index}].name"

        if not name:
            errors.append(
                CollectionValidationError(
                    field=field_path,
                    message="Field name is required",
                    code="field_name_required",
                )
            )
            return errors

        if len(name) > cls.MAX_FIELD_NAME_LENGTH:
            errors.append(
                CollectionValidationError(
                    field=field_path,
                    message=f"Field name must be at most {cls.MAX_FIELD_NAME_LENGTH} characters",
                    code="field_name_too_long",
                )
            )

        if not NAME_PATTERN.match(name):
            errors.append(
                CollectionValidationError(
                    field=field_path,
                    message="Field name must start with a letter and contain only alphanumeric characters and underscores",
                    code="field_name_invalid_format",
                )
            )

        if name.lower() in RESERVED_FIELD_NAMES:
            errors.append(
                CollectionValidationError(
                    field=field_path,
                    message=f"Field name '{name}' is reserved and cannot be used",
                    code="field_name_reserved",
                )
            )

        return errors

    @classmethod
    def validate_field_type(cls, field_type: str, field_index: int) -> list[CollectionValidationError]:
        """Validate a field type.

        Args:
            field_type: The field type to validate.
            field_index: Index of the field in the schema (for error messages).

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        field_path = f"schema[{field_index}].type"

        if not field_type:
            errors.append(
                CollectionValidationError(
                    field=field_path,
                    message="Field type is required",
                    code="field_type_required",
                )
            )
            return errors

        valid_types = [t.value for t in FieldType]
        if field_type.lower() not in valid_types:
            errors.append(
                CollectionValidationError(
                    field=field_path,
                    message=f"Invalid field type '{field_type}'. Valid types: {', '.join(valid_types)}",
                    code="field_type_invalid",
                )
            )

        return errors

    @classmethod
    def validate_reference_field(
        cls, field: dict, field_index: int
    ) -> list[CollectionValidationError]:
        """Validate a reference field configuration.

        Args:
            field: The field definition dict.
            field_index: Index of the field in the schema (for error messages).

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Reference fields require 'collection' (target collection name)
        target_collection = field.get("collection")
        if not target_collection:
            errors.append(
                CollectionValidationError(
                    field=f"schema[{field_index}].collection",
                    message="Reference field requires 'collection' (target collection name)",
                    code="reference_collection_required",
                )
            )

        # on_delete is required for reference fields
        on_delete = field.get("on_delete")
        if not on_delete:
            errors.append(
                CollectionValidationError(
                    field=f"schema[{field_index}].on_delete",
                    message="Reference field requires 'on_delete' (cascade/set_null/restrict)",
                    code="reference_on_delete_required",
                )
            )
        else:
            valid_actions = [a.value for a in OnDeleteAction]
            if on_delete.lower() not in valid_actions:
                errors.append(
                    CollectionValidationError(
                        field=f"schema[{field_index}].on_delete",
                        message=f"Invalid on_delete action '{on_delete}'. Valid actions: {', '.join(valid_actions)}",
                        code="reference_on_delete_invalid",
                    )
                )

        return errors

    @classmethod
    def validate_field(cls, field: dict, field_index: int) -> list[CollectionValidationError]:
        """Validate a single field definition.

        Args:
            field: The field definition dict with at least 'name' and 'type'.
            field_index: Index of the field in the schema (for error messages).

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Validate field name
        name = field.get("name", "")
        errors.extend(cls.validate_field_name(name, field_index))

        # Validate field type
        field_type = field.get("type", "")
        errors.extend(cls.validate_field_type(field_type, field_index))

        # If this is a reference field, validate reference-specific config
        if field_type.lower() == FieldType.REFERENCE.value:
            errors.extend(cls.validate_reference_field(field, field_index))

        return errors

    @classmethod
    def validate_schema(cls, schema: list[dict]) -> list[CollectionValidationError]:
        """Validate a collection schema.

        Args:
            schema: List of field definitions.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Schema must have at least one field
        if not schema:
            errors.append(
                CollectionValidationError(
                    field="schema",
                    message="Schema must define at least one field",
                    code="schema_empty",
                )
            )
            return errors

        # Validate each field
        seen_names: set[str] = set()
        for i, field in enumerate(schema):
            # Validate the field
            errors.extend(cls.validate_field(field, i))

            # Check for duplicate field names
            name = field.get("name", "").lower()
            if name and name in seen_names:
                errors.append(
                    CollectionValidationError(
                        field=f"schema[{i}].name",
                        message=f"Duplicate field name '{field.get('name')}'",
                        code="field_name_duplicate",
                    )
                )
            seen_names.add(name)

        return errors

    @classmethod
    def validate(cls, name: str, schema: list[dict]) -> list[CollectionValidationError]:
        """Validate a complete collection definition.

        Args:
            name: The collection name.
            schema: The collection schema (list of field definitions).

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        errors.extend(cls.validate_name(name))
        errors.extend(cls.validate_schema(schema))
        return errors
