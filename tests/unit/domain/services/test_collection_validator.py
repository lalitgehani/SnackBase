
import pytest
from snackbase.domain.services.collection_validator import (
    CollectionValidator,
    CollectionValidationError,
    FieldType,
    OnDeleteAction,
    MaskType,
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

    # --- PII Field Validation ---

    def test_validate_pii_field_valid(self):
        """Test valid PII field with mask_type."""
        field = {
            "name": "email",
            "type": "email",
            "pii": True,
            "mask_type": "email"
        }
        errors = CollectionValidator.validate_field(field, 0)
        assert len(errors) == 0

    def test_validate_pii_field_all_mask_types(self):
        """Test all valid mask types."""
        for mask_type in MaskType:
            field = {
                "name": "sensitive_data",
                "type": "text",
                "pii": True,
                "mask_type": mask_type.value
            }
            errors = CollectionValidator.validate_field(field, 0)
            assert len(errors) == 0, f"Expected no errors for mask_type '{mask_type.value}'"

    def test_validate_pii_field_without_mask_type(self):
        """Test PII field without mask_type is valid."""
        field = {
            "name": "sensitive",
            "type": "text",
            "pii": True
        }
        errors = CollectionValidator.validate_field(field, 0)
        assert len(errors) == 0

    def test_validate_pii_field_mask_type_requires_pii(self):
        """Test mask_type without pii=True returns error."""
        field = {
            "name": "email",
            "type": "email",
            "pii": False,
            "mask_type": "email"
        }
        errors = CollectionValidator.validate_field(field, 0)
        assert len(errors) == 1
        assert errors[0].code == "mask_type_requires_pii"

    def test_validate_pii_field_invalid_mask_type(self):
        """Test invalid mask_type returns error."""
        field = {
            "name": "data",
            "type": "text",
            "pii": True,
            "mask_type": "invalid_type"
        }
        errors = CollectionValidator.validate_field(field, 0)
        assert len(errors) == 1
        assert errors[0].code == "mask_type_invalid"

    def test_get_default_mask_type_email(self):
        """Test default mask type inference for email fields."""
        assert CollectionValidator.get_default_mask_type("email") == "email"
        assert CollectionValidator.get_default_mask_type("user_email") == "email"
        assert CollectionValidator.get_default_mask_type("e_mail") == "email"
        assert CollectionValidator.get_default_mask_type("mail") == "email"

    def test_get_default_mask_type_ssn(self):
        """Test default mask type inference for SSN fields."""
        assert CollectionValidator.get_default_mask_type("ssn") == "ssn"
        assert CollectionValidator.get_default_mask_type("social_security") == "ssn"
        assert CollectionValidator.get_default_mask_type("user_ssn") == "ssn"

    def test_get_default_mask_type_phone(self):
        """Test default mask type inference for phone fields."""
        assert CollectionValidator.get_default_mask_type("phone") == "phone"
        assert CollectionValidator.get_default_mask_type("mobile") == "phone"
        assert CollectionValidator.get_default_mask_type("telephone") == "phone"
        assert CollectionValidator.get_default_mask_type("tel") == "phone"

    def test_get_default_mask_type_name(self):
        """Test default mask type inference for name fields."""
        assert CollectionValidator.get_default_mask_type("name") == "name"
        assert CollectionValidator.get_default_mask_type("first_name") == "name"
        assert CollectionValidator.get_default_mask_type("last_name") == "name"
        assert CollectionValidator.get_default_mask_type("full_name") == "name"
        assert CollectionValidator.get_default_mask_type("firstname") == "name"
        assert CollectionValidator.get_default_mask_type("lastname") == "name"

    def test_get_default_mask_type_no_match(self):
        """Test default mask type returns None for non-matching fields."""
        assert CollectionValidator.get_default_mask_type("title") is None
        assert CollectionValidator.get_default_mask_type("description") is None
        assert CollectionValidator.get_default_mask_type("count") is None

    def test_validate_schema_with_pii_fields(self):
        """Test schema validation with multiple PII fields."""
        schema = [
            {"name": "email", "type": "email", "pii": True, "mask_type": "email"},
            {"name": "ssn", "type": "text", "pii": True, "mask_type": "ssn"},
            {"name": "title", "type": "text", "required": True}
        ]
        errors = CollectionValidator.validate_schema(schema)
        assert len(errors) == 0
