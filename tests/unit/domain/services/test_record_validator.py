
import pytest
from datetime import datetime, timezone
from snackbase.domain.services.record_validator import (
    RecordValidator,
    RecordValidationError
)

class TestRecordValidator:

    # --- Type Validation ---

    def test_validate_text(self):
        assert RecordValidator.validate_text("hello", "f") is None
        assert RecordValidator.validate_text(123, "f").code == "invalid_type"

    def test_validate_number(self):
        assert RecordValidator.validate_number(123, "f") is None
        assert RecordValidator.validate_number(12.34, "f") is None
        assert RecordValidator.validate_number("123", "f").code == "invalid_type"
        assert RecordValidator.validate_number(True, "f").code == "invalid_type"  # bool is instance of int in Python

    def test_validate_boolean(self):
        assert RecordValidator.validate_boolean(True, "f") is None
        assert RecordValidator.validate_boolean(False, "f") is None
        assert RecordValidator.validate_boolean("true", "f").code == "invalid_type"

    def test_validate_datetime(self):
        now = datetime.now(timezone.utc)
        assert RecordValidator.validate_datetime(now, "f") is None
        assert RecordValidator.validate_datetime("2024-01-01T12:00:00Z", "f") is None
        assert RecordValidator.validate_datetime("not-a-date", "f").code == "invalid_datetime_format"
        assert RecordValidator.validate_datetime(123, "f").code == "invalid_type"

    def test_validate_date(self):
        from datetime import date
        assert RecordValidator.validate_date("2024-01-01", "f") is None
        assert RecordValidator.validate_date(date(2024, 1, 1), "f") is None
        assert RecordValidator.validate_date("not-a-date", "f").code == "invalid_date_format"
        assert RecordValidator.validate_date(123, "f").code == "invalid_type"

    def test_validate_email(self):
        assert RecordValidator.validate_email("test@example.com", "f") is None
        assert RecordValidator.validate_email("invalid-email", "f").code == "invalid_email_format"
        assert RecordValidator.validate_email(123, "f").code == "invalid_type"

    def test_validate_url(self):
        assert RecordValidator.validate_url("https://example.com", "f") is None
        assert RecordValidator.validate_url("http://example.com/path", "f") is None
        assert RecordValidator.validate_url("not-url", "f").code == "invalid_url_format"
        assert RecordValidator.validate_url(123, "f").code == "invalid_type"

    def test_validate_json(self):
        assert RecordValidator.validate_json({"key": "value"}, "f") is None
        assert RecordValidator.validate_json([1, 2, 3], "f") is None
        assert RecordValidator.validate_json(None, "f") is None


    def test_validate_reference(self):
        assert RecordValidator.validate_reference("some-id", "f") is None
        assert RecordValidator.validate_reference("", "f").code == "empty_reference"
        assert RecordValidator.validate_reference(123, "f").code == "invalid_type"

    # --- Full Record Validation ---

    def test_validate_defaults_success(self):
        schema = [
            {"name": "title", "type": "text", "required": True},
            {"name": "status", "type": "text", "default": "draft"},
            {"name": "count", "type": "number"},
            {"name": "birth_date", "type": "date"}
        ]
        data = {"title": "Hello", "birth_date": "1990-01-01"}
        
        processed, errors = RecordValidator.validate_and_apply_defaults(data, schema)
        assert len(errors) == 0
        assert processed["title"] == "Hello"
        assert processed["status"] == "draft"  # Default applied
        assert processed["birth_date"] == "1990-01-01"
        assert "count" not in processed  # Optional missing

    def test_validate_required_missing(self):
        schema = [{"name": "title", "type": "text", "required": True}]
        data = {}
        processed, errors = RecordValidator.validate_and_apply_defaults(data, schema)
        assert len(errors) == 1
        assert errors[0].code == "required_missing"

    def test_validate_unknown_field(self):
        schema = [{"name": "title", "type": "text"}]
        data = {"title": "Hello", "extra": "field"}
        processed, errors = RecordValidator.validate_and_apply_defaults(data, schema)
        assert len(errors) == 1
        assert errors[0].code == "unknown_field"

    def test_validate_type_mismatch(self):
        schema = [{"name": "count", "type": "number"}]
        data = {"count": "not-a-number"}
        processed, errors = RecordValidator.validate_and_apply_defaults(data, schema)
        assert len(errors) == 1
        assert errors[0].code == "invalid_type"

    def test_validate_null_required(self):
        schema = [{"name": "title", "type": "text", "required": True}]
        data = {"title": None}
        processed, errors = RecordValidator.validate_and_apply_defaults(data, schema)
        assert len(errors) == 1
        assert errors[0].code == "required_null"

    def test_validate_null_optional(self):
        schema = [{"name": "title", "type": "text", "required": False}]
        data = {"title": None}
        processed, errors = RecordValidator.validate_and_apply_defaults(data, schema)
        assert len(errors) == 0
        assert processed["title"] is None

    def test_partial_update(self):
        schema = [
            {"name": "title", "type": "text", "required": True},
            {"name": "status", "type": "text", "required": True}
        ]
        data = {"title": "New Title"}
        # Partial=True should not complain about missing 'status'
        processed, errors = RecordValidator.validate_and_apply_defaults(data, schema, partial=True)
        assert len(errors) == 0
        assert processed["title"] == "New Title"
        assert "status" not in processed

    def test_unknown_field_type_in_schema(self):
        schema = [{"name": "weird", "type": "alien"}]
        data = {"weird": "value"}
        processed, errors = RecordValidator.validate_and_apply_defaults(data, schema)
        assert len(errors) == 1
        assert errors[0].code == "unknown_type"
