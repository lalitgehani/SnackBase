"""Collection validation service for schema and field validation.

Provides validation for collection names, schema definitions, and field configurations.
Supports field types: text, number, boolean, datetime, email, url, json, reference, file, date.
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
    FILE = "file"
    DATE = "date"
    COMPUTED = "computed"


class OnDeleteAction(str, Enum):
    """Valid on_delete actions for reference fields."""

    CASCADE = "cascade"
    SET_NULL = "set_null"
    RESTRICT = "restrict"


class MaskType(str, Enum):
    """Valid mask types for PII fields."""

    EMAIL = "email"
    SSN = "ssn"
    PHONE = "phone"
    NAME = "name"
    FULL = "full"
    CUSTOM = "custom"


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

# Valid return_type values for computed fields
VALID_RETURN_TYPES = frozenset({"text", "number", "boolean", "datetime"})

# Maximum computed fields allowed per collection
MAX_COMPUTED_FIELDS = 10


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
    def get_default_mask_type(cls, field_name: str) -> str | None:
        """Infer default mask type from field name.

        Args:
            field_name: The field name to analyze.

        Returns:
            Suggested mask type or None if no match.
        """
        field_lower = field_name.lower()

        # Email patterns
        if "email" in field_lower or field_lower in {"e_mail", "mail"}:
            return MaskType.EMAIL.value

        # SSN patterns
        if "ssn" in field_lower or "social_security" in field_lower:
            return MaskType.SSN.value

        # Phone patterns
        if "phone" in field_lower or "mobile" in field_lower or "tel" in field_lower:
            return MaskType.PHONE.value

        # Name patterns
        if field_lower in {"name", "first_name", "last_name", "full_name", "firstname", "lastname"}:
            return MaskType.NAME.value

        return None

    @classmethod
    def validate_pii_field(cls, field: dict, field_index: int) -> list[CollectionValidationError]:
        """Validate PII field configuration.

        Args:
            field: The field definition dict.
            field_index: Index of the field in the schema (for error messages).

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        pii = field.get("pii", False)
        mask_type = field.get("mask_type")

        # If pii is False, mask_type should not be set
        if not pii and mask_type is not None:
            errors.append(
                CollectionValidationError(
                    field=f"schema[{field_index}].mask_type",
                    message="mask_type can only be set when pii=True",
                    code="mask_type_requires_pii",
                )
            )

        # If pii is True and mask_type is provided, validate it
        if pii and mask_type is not None:
            valid_mask_types = [t.value for t in MaskType]
            if mask_type.lower() not in valid_mask_types:
                errors.append(
                    CollectionValidationError(
                        field=f"schema[{field_index}].mask_type",
                        message=f"Invalid mask_type '{mask_type}'. Valid types: {', '.join(valid_mask_types)}",
                        code="mask_type_invalid",
                    )
                )

        return errors

    @classmethod
    def validate_computed_field(
        cls,
        field: dict,
        field_index: int,
        all_field_names: set[str] | None = None,
        computed_field_names: set[str] | None = None,
    ) -> list[CollectionValidationError]:
        """Validate a computed field definition.

        Args:
            field: The field definition dict.
            field_index: Index of the field in the schema (for error messages).
            all_field_names: All non-computed field names in the schema (for expression validation).
            computed_field_names: Names of other computed fields (to reject cross-references).

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        field_path = f"schema[{field_index}]"

        # Reject constraints that don't apply to computed fields
        if field.get("required", False):
            errors.append(CollectionValidationError(
                field=f"{field_path}.required",
                message="Computed fields cannot have 'required' — they are always derived",
                code="computed_field_no_required",
            ))

        if field.get("default") is not None:
            errors.append(CollectionValidationError(
                field=f"{field_path}.default",
                message="Computed fields cannot have a 'default' value",
                code="computed_field_no_default",
            ))

        if field.get("unique", False):
            errors.append(CollectionValidationError(
                field=f"{field_path}.unique",
                message="Computed fields cannot have 'unique' constraint",
                code="computed_field_no_unique",
            ))

        # expression is required
        expression = field.get("expression")
        if not expression or not str(expression).strip():
            errors.append(CollectionValidationError(
                field=f"{field_path}.expression",
                message="Computed field requires an 'expression'",
                code="computed_field_expression_required",
            ))
            return errors  # Can't validate further without expression

        # return_type is required
        return_type = field.get("return_type")
        if not return_type:
            errors.append(CollectionValidationError(
                field=f"{field_path}.return_type",
                message=(
                    f"Computed field requires 'return_type'. "
                    f"Valid values: {', '.join(sorted(VALID_RETURN_TYPES))}"
                ),
                code="computed_field_return_type_required",
            ))
        elif return_type.lower() not in VALID_RETURN_TYPES:
            errors.append(CollectionValidationError(
                field=f"{field_path}.return_type",
                message=(
                    f"Invalid return_type '{return_type}'. "
                    f"Valid values: {', '.join(sorted(VALID_RETURN_TYPES))}"
                ),
                code="computed_field_return_type_invalid",
            ))

        # Validate expression syntax and field references
        if not errors:
            try:
                from snackbase.core.rules.expression_compiler import compile_expression_to_sql
                from snackbase.core.rules.exceptions import RuleSyntaxError

                # Build schema_fields: all non-computed fields + system fields
                system_fields = {
                    "id", "account_id", "created_at", "created_by", "updated_at", "updated_by"
                }
                schema_fields: set[str] | None = None
                if all_field_names is not None:
                    schema_fields = all_field_names | system_fields

                compile_expression_to_sql(expression, dialect="sqlite", schema_fields=schema_fields)

            except RuleSyntaxError as e:
                errors.append(CollectionValidationError(
                    field=f"{field_path}.expression",
                    message=f"Invalid expression syntax: {e}",
                    code="computed_field_expression_invalid",
                ))
            except Exception as e:
                errors.append(CollectionValidationError(
                    field=f"{field_path}.expression",
                    message=f"Expression error: {e}",
                    code="computed_field_expression_error",
                ))

        return errors

    @classmethod
    def validate_field(
        cls,
        field: dict,
        field_index: int,
        all_field_names: set[str] | None = None,
        computed_field_names: set[str] | None = None,
    ) -> list[CollectionValidationError]:
        """Validate a single field definition.

        Args:
            field: The field definition dict with at least 'name' and 'type'.
            field_index: Index of the field in the schema (for error messages).
            all_field_names: Non-computed field names (passed to computed field validation).
            computed_field_names: Computed field names (passed to computed field validation).

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

        # Computed fields have their own validation path
        if field_type.lower() == FieldType.COMPUTED.value:
            errors.extend(cls.validate_computed_field(
                field, field_index, all_field_names, computed_field_names
            ))
            return errors

        # If this is a reference field, validate reference-specific config
        if field_type.lower() == FieldType.REFERENCE.value:
            errors.extend(cls.validate_reference_field(field, field_index))

        # Validate PII configuration
        errors.extend(cls.validate_pii_field(field, field_index))

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

        # Collect non-computed and computed field names for cross-validation
        non_computed_names: set[str] = set()
        computed_names: set[str] = set()
        for field in schema:
            name = field.get("name", "")
            if field.get("type", "").lower() == FieldType.COMPUTED.value:
                computed_names.add(name)
            else:
                non_computed_names.add(name)

        # Enforce max computed fields limit
        if len(computed_names) > MAX_COMPUTED_FIELDS:
            errors.append(CollectionValidationError(
                field="schema",
                message=(
                    f"Collection cannot have more than {MAX_COMPUTED_FIELDS} computed fields "
                    f"(found {len(computed_names)})"
                ),
                code="too_many_computed_fields",
            ))

        # Validate each field
        seen_names: set[str] = set()
        for i, field in enumerate(schema):
            # Validate the field (pass context for computed field validation)
            errors.extend(cls.validate_field(
                field, i,
                all_field_names=non_computed_names,
                computed_field_names=computed_names,
            ))

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
