"""Record validation service for validating record data against collection schemas.

Provides validation for record data, ensuring it conforms to the collection schema.
Supports field types: text, number, boolean, datetime, email, url, json, reference, file.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from snackbase.domain.services.collection_validator import FieldType


# Email validation pattern (simplified but effective)
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# URL validation pattern (simplified)
URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


@dataclass
class RecordValidationError:
    """A single record validation error."""

    field: str
    message: str
    code: str


class RecordValidator:
    """Validator for record data against collection schemas.

    Validates field types, required fields, and applies default values.
    """

    @classmethod
    def validate_text(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate a text field value."""
        if not isinstance(value, str):
            return RecordValidationError(
                field=field_name,
                message=f"Expected text value, got {type(value).__name__}",
                code="invalid_type",
            )
        return None

    @classmethod
    def validate_number(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate a number field value."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return RecordValidationError(
                field=field_name,
                message=f"Expected number value, got {type(value).__name__}",
                code="invalid_type",
            )
        return None

    @classmethod
    def validate_boolean(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate a boolean field value."""
        if not isinstance(value, bool):
            return RecordValidationError(
                field=field_name,
                message=f"Expected boolean value, got {type(value).__name__}",
                code="invalid_type",
            )
        return None

    @classmethod
    def validate_datetime(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate a datetime field value.

        Accepts ISO 8601 formatted strings or datetime objects.
        """
        if isinstance(value, datetime):
            return None

        if isinstance(value, str):
            try:
                # Try parsing ISO 8601 format
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return None
            except ValueError:
                return RecordValidationError(
                    field=field_name,
                    message="Invalid datetime format. Use ISO 8601 format (e.g., 2024-01-01T12:00:00Z)",
                    code="invalid_datetime_format",
                )

        return RecordValidationError(
            field=field_name,
            message=f"Expected datetime string, got {type(value).__name__}",
            code="invalid_type",
        )

    @classmethod
    def validate_email(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate an email field value."""
        if not isinstance(value, str):
            return RecordValidationError(
                field=field_name,
                message=f"Expected email string, got {type(value).__name__}",
                code="invalid_type",
            )

        if not EMAIL_PATTERN.match(value):
            return RecordValidationError(
                field=field_name,
                message="Invalid email format",
                code="invalid_email_format",
            )

        return None

    @classmethod
    def validate_url(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate a URL field value."""
        if not isinstance(value, str):
            return RecordValidationError(
                field=field_name,
                message=f"Expected URL string, got {type(value).__name__}",
                code="invalid_type",
            )

        if not URL_PATTERN.match(value):
            return RecordValidationError(
                field=field_name,
                message="Invalid URL format. Must start with http:// or https://",
                code="invalid_url_format",
            )

        return None

    @classmethod
    def validate_json(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate a JSON field value.

        Accepts any value that can be serialized to JSON (dict, list, etc.).
        """
        if value is None:
            return None

        # Check if value is JSON-serializable
        try:
            json.dumps(value)
            return None
        except (TypeError, ValueError):
            return RecordValidationError(
                field=field_name,
                message="Value must be JSON-serializable (dict, list, string, number, boolean, or null)",
                code="invalid_json",
            )

    @classmethod
    def validate_reference(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate a reference field value.

        Reference values should be string IDs. Actual foreign key validation
        is done during database insert (constraint check).
        """
        if not isinstance(value, str):
            return RecordValidationError(
                field=field_name,
                message=f"Expected reference ID (string), got {type(value).__name__}",
                code="invalid_type",
            )

        if not value.strip():
            return RecordValidationError(
                field=field_name,
                message="Reference ID cannot be empty",
                code="empty_reference",
            )

        return None

    @classmethod
    def validate_file(cls, value: Any, field_name: str) -> RecordValidationError | None:
        """Validate a file field value.

        File fields should contain JSON metadata with: filename, size, mime_type, path.
        """
        if not isinstance(value, (dict, str)):
            return RecordValidationError(
                field=field_name,
                message=f"Expected file metadata (dict or JSON string), got {type(value).__name__}",
                code="invalid_type",
            )

        # If string, try to parse as JSON
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return RecordValidationError(
                    field=field_name,
                    message="Invalid file metadata: must be valid JSON",
                    code="invalid_json",
                )

        # Validate required fields in file metadata
        required_fields = {"filename", "size", "mime_type", "path"}
        missing_fields = required_fields - set(value.keys())
        if missing_fields:
            return RecordValidationError(
                field=field_name,
                message=f"File metadata missing required fields: {', '.join(missing_fields)}",
                code="missing_file_metadata",
            )

        # Validate field types
        if not isinstance(value.get("filename"), str):
            return RecordValidationError(
                field=field_name,
                message="File metadata 'filename' must be a string",
                code="invalid_file_metadata",
            )

        if not isinstance(value.get("size"), int):
            return RecordValidationError(
                field=field_name,
                message="File metadata 'size' must be an integer",
                code="invalid_file_metadata",
            )

        if not isinstance(value.get("mime_type"), str):
            return RecordValidationError(
                field=field_name,
                message="File metadata 'mime_type' must be a string",
                code="invalid_file_metadata",
            )

        if not isinstance(value.get("path"), str):
            return RecordValidationError(
                field=field_name,
                message="File metadata 'path' must be a string",
                code="invalid_file_metadata",
            )

        return None

    @classmethod
    def validate_field_value(
        cls, value: Any, field_type: str, field_name: str
    ) -> RecordValidationError | None:
        """Validate a single field value against its type.

        Args:
            value: The value to validate.
            field_type: The expected field type from schema.
            field_name: The field name for error messages.

        Returns:
            RecordValidationError if invalid, None if valid.
        """
        validators = {
            FieldType.TEXT.value: cls.validate_text,
            FieldType.NUMBER.value: cls.validate_number,
            FieldType.BOOLEAN.value: cls.validate_boolean,
            FieldType.DATETIME.value: cls.validate_datetime,
            FieldType.EMAIL.value: cls.validate_email,
            FieldType.URL.value: cls.validate_url,
            FieldType.JSON.value: cls.validate_json,
            FieldType.REFERENCE.value: cls.validate_reference,
            FieldType.FILE.value: cls.validate_file,
        }

        validator = validators.get(field_type.lower())
        if validator:
            return validator(value, field_name)

        # Unknown type - shouldn't happen if collection was validated
        return RecordValidationError(
            field=field_name,
            message=f"Unknown field type: {field_type}",
            code="unknown_type",
        )

    @classmethod
    def validate_and_apply_defaults(
        cls, data: dict[str, Any], schema: list[dict[str, Any]], partial: bool = False
    ) -> tuple[dict[str, Any], list[RecordValidationError]]:
        """Validate record data against schema and apply default values.

        Args:
            data: The record data to validate.
            schema: The collection schema (list of field definitions).
            partial: If True, only validate fields present in data (for PATCH).

        Returns:
            Tuple of (processed_data, errors).
            processed_data has defaults applied for missing optional fields (unless partial=True).
            errors is empty list if validation passed.
        """
        errors: list[RecordValidationError] = []
        processed_data: dict[str, Any] = {}

        # Build schema lookup
        schema_fields = {field["name"]: field for field in schema}

        # Check for unknown fields in data
        for field_name in data:
            if field_name not in schema_fields:
                errors.append(
                    RecordValidationError(
                        field=field_name,
                        message=f"Unknown field '{field_name}' not defined in collection schema",
                        code="unknown_field",
                    )
                )

        # Validate each schema field
        for field in schema:
            field_name = field["name"]
            field_type = field.get("type", "text").lower()
            is_required = field.get("required", False)
            default_value = field.get("default")

            if field_name in data:
                # Field provided - validate type
                value = data[field_name]

                # Allow null values for non-required fields
                if value is None and not is_required:
                    processed_data[field_name] = None
                elif value is None and is_required:
                    errors.append(
                        RecordValidationError(
                            field=field_name,
                            message=f"Required field '{field_name}' cannot be null",
                            code="required_null",
                        )
                    )
                else:
                    # Validate the value type
                    error = cls.validate_field_value(value, field_type, field_name)
                    if error:
                        errors.append(error)
                    else:
                        # For file fields, convert dict to JSON string for storage
                        if field_type == FieldType.FILE.value and isinstance(value, dict):
                            processed_data[field_name] = json.dumps(value)
                        else:
                            processed_data[field_name] = value
            elif not partial:
                # Field missing - apply defaults or check required ONLY if not partial update
                if is_required:
                    # Required field missing
                    errors.append(
                        RecordValidationError(
                            field=field_name,
                            message=f"Required field '{field_name}' is missing",
                            code="required_missing",
                        )
                    )
                elif default_value is not None:
                    # Optional field with default - apply default
                    processed_data[field_name] = default_value
                # else: optional field without default - don't include in processed_data

        return processed_data, errors
