"""Unit tests for encrypted collection field schema validation."""

from snackbase.domain.services.collection_validator import CollectionValidator


def test_encrypted_text_field_valid():
    schema = [{"name": "api_token", "type": "text", "encrypted": True}]
    errors = CollectionValidator.validate_schema(schema)
    assert errors == []


def test_encrypted_json_field_valid():
    schema = [{"name": "credentials", "type": "json", "encrypted": True}]
    errors = CollectionValidator.validate_schema(schema)
    assert errors == []


def test_encrypted_number_rejected():
    schema = [{"name": "secret_num", "type": "number", "encrypted": True}]
    errors = CollectionValidator.validate_schema(schema)
    assert any(e.code == "encrypted_type_invalid" for e in errors)


def test_encrypted_boolean_rejected():
    schema = [{"name": "flag", "type": "boolean", "encrypted": True}]
    errors = CollectionValidator.validate_schema(schema)
    assert any(e.code == "encrypted_type_invalid" for e in errors)


def test_encrypted_email_rejected():
    schema = [{"name": "secret_email", "type": "email", "encrypted": True}]
    errors = CollectionValidator.validate_schema(schema)
    assert any(e.code == "encrypted_type_invalid" for e in errors)


def test_encrypted_unique_rejected():
    schema = [{"name": "token", "type": "text", "encrypted": True, "unique": True}]
    errors = CollectionValidator.validate_schema(schema)
    assert any(e.code == "encrypted_no_unique" for e in errors)


def test_encrypted_searchable_option_rejected():
    schema = [
        {
            "name": "token",
            "type": "text",
            "encrypted": True,
            "options": {"searchable": True},
        }
    ]
    errors = CollectionValidator.validate_schema(schema)
    assert any(e.code == "encrypted_query_option_forbidden" for e in errors)


def test_unencrypted_fields_still_valid():
    schema = [
        {"name": "title", "type": "text"},
        {"name": "count", "type": "number", "unique": True},
    ]
    errors = CollectionValidator.validate_schema(schema)
    assert errors == []
