
import pytest
from snackbase.domain.services.collection_validator import (
    CollectionValidator,
    CollectionValidationError,
    FieldType,
    OnDeleteAction,
    RESERVED_FIELD_NAMES
)

class TestCollectionValidator:
    
    # --- Name Validation ---
    
    def test_validate_name_valid(self):
        valid_names = ["posts", "user_profiles", "data_2024", "MyCollection"]
        for name in valid_names:
            errors = CollectionValidator.validate_name(name)
            assert len(errors) == 0, f"Expected no errors for '{name}'"

    def test_validate_name_empty(self):
        errors = CollectionValidator.validate_name("")
        assert len(errors) == 1
        assert errors[0].code == "name_required"

    def test_validate_name_too_short(self):
        errors = CollectionValidator.validate_name("ab")
        assert len(errors) == 1
        assert errors[0].code == "name_too_short"

    def test_validate_name_too_long(self):
        errors = CollectionValidator.validate_name("a" * 65)
        assert len(errors) == 1
        assert errors[0].code == "name_too_long"

    def test_validate_name_invalid_format(self):
        invalid_names = ["123start", "has-dash", "has space", "special$char"]
        for name in invalid_names:
            errors = CollectionValidator.validate_name(name)
            assert len(errors) == 1
            assert errors[0].code == "name_invalid_format"

    # --- Field Name Validation ---

    def test_validate_field_name_valid(self):
        errors = CollectionValidator.validate_field_name("title", 0)
        assert len(errors) == 0

    def test_validate_field_name_reserved(self):
        for name in RESERVED_FIELD_NAMES:
            errors = CollectionValidator.validate_field_name(name, 0)
            assert len(errors) == 1
            assert errors[0].code == "field_name_reserved"

    def test_validate_field_name_empty(self):
        errors = CollectionValidator.validate_field_name("", 0)
        assert len(errors) == 1
        assert errors[0].code == "field_name_required"

    def test_validate_field_name_invalid(self):
        errors = CollectionValidator.validate_field_name("invalid-name", 0)
        assert len(errors) == 1
        assert errors[0].code == "field_name_invalid_format"

    # --- Field Type Validation ---

    def test_validate_field_type_valid(self):
        for type_enum in FieldType:
            errors = CollectionValidator.validate_field_type(type_enum.value, 0)
            assert len(errors) == 0

    def test_validate_field_type_invalid(self):
        errors = CollectionValidator.validate_field_type("unknown_type", 0)
        assert len(errors) == 1
        assert errors[0].code == "field_type_invalid"

    def test_validate_field_type_empty(self):
        errors = CollectionValidator.validate_field_type("", 0)
        assert len(errors) == 1
        assert errors[0].code == "field_type_required"

    # --- Reference Field Validation ---

    def test_validate_reference_field_valid(self):
        field = {
            "name": "author",
            "type": "reference",
            "collection": "users",
            "on_delete": "set_null"
        }
        errors = CollectionValidator.validate_field(field, 0)
        assert len(errors) == 0

    def test_validate_reference_field_missing_collection(self):
        field = {
            "name": "author",
            "type": "reference",
            "on_delete": "set_null"
        }
        errors = CollectionValidator.validate_field(field, 0)
        assert len(errors) == 1
        assert errors[0].code == "reference_collection_required"

    def test_validate_reference_field_missing_on_delete(self):
        field = {
            "name": "author",
            "type": "reference",
            "collection": "users"
        }
        errors = CollectionValidator.validate_field(field, 0)
        assert len(errors) == 1
        assert errors[0].code == "reference_on_delete_required"

    def test_validate_reference_field_invalid_on_delete(self):
        field = {
            "name": "author",
            "type": "reference",
            "collection": "users",
            "on_delete": "explode"
        }
        errors = CollectionValidator.validate_field(field, 0)
        assert len(errors) == 1
        assert errors[0].code == "reference_on_delete_invalid"

    # --- Schema Validation ---

    def test_validate_schema_valid(self):
        schema = [
            {"name": "title", "type": "text"},
            {"name": "count", "type": "number"}
        ]
        errors = CollectionValidator.validate_schema(schema)
        assert len(errors) == 0

    def test_validate_schema_empty(self):
        errors = CollectionValidator.validate_schema([])
        assert len(errors) == 1
        assert errors[0].code == "schema_empty"

    def test_validate_schema_duplicate_field_names(self):
        schema = [
            {"name": "title", "type": "text"},
            {"name": "Title", "type": "number"}  # Case-insensitive duplicate check not implemented?
            # Wait, implementation uses `name.lower()` for check
        ]
        errors = CollectionValidator.validate_schema(schema)
        assert len(errors) == 1
        assert errors[0].code == "field_name_duplicate"

    def test_validate_full_collection(self):
        name = "valid_collection"
        schema = [{"name": "title", "type": "text"}]
        errors = CollectionValidator.validate(name, schema)
        assert len(errors) == 0
