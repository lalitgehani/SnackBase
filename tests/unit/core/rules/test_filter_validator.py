"""Unit tests for the FilterValidator."""

import pytest

from snackbase.core.rules.exceptions import RuleSyntaxError
from snackbase.core.rules.filter_validator import validate_filter_expression

SCHEMA = [
    {"name": "title", "type": "text"},
    {"name": "price", "type": "number"},
    {"name": "is_active", "type": "boolean"},
    {"name": "published_at", "type": "datetime"},
    {"name": "category_id", "type": "reference"},
    {"name": "metadata", "type": "json"},
    {"name": "status", "type": "text"},
    {"name": "rating", "type": "number"},
]


class TestFilterValidatorValidFields:
    """Tests for valid field name validation."""

    def test_valid_schema_field(self):
        validate_filter_expression('title = "hello"', SCHEMA)  # should not raise

    def test_valid_number_field(self):
        validate_filter_expression("price > 100", SCHEMA)

    def test_valid_boolean_field(self):
        validate_filter_expression("is_active = true", SCHEMA)

    def test_valid_datetime_field(self):
        validate_filter_expression('published_at > "2024-01-01"', SCHEMA)

    def test_valid_in_operator(self):
        validate_filter_expression('status IN ("active", "pending")', SCHEMA)

    def test_valid_is_null(self):
        validate_filter_expression("published_at IS NULL", SCHEMA)

    def test_valid_is_not_null(self):
        validate_filter_expression("published_at IS NOT NULL", SCHEMA)

    def test_valid_and_expression(self):
        validate_filter_expression('status = "active" && price > 100', SCHEMA)

    def test_valid_or_expression(self):
        validate_filter_expression('status = "active" || status = "pending"', SCHEMA)


class TestFilterValidatorSystemFields:
    """Tests that system fields are always valid."""

    def test_filter_on_id(self):
        validate_filter_expression('id = "abc123"', SCHEMA)

    def test_filter_on_created_at(self):
        validate_filter_expression('created_at > "2024-01-01"', SCHEMA)

    def test_filter_on_updated_at(self):
        validate_filter_expression("updated_at IS NOT NULL", SCHEMA)

    def test_filter_on_created_by(self):
        validate_filter_expression('created_by = "user_abc"', SCHEMA)

    def test_filter_on_updated_by(self):
        validate_filter_expression('updated_by != "user_xyz"', SCHEMA)

    def test_filter_on_account_id(self):
        # account_id is a system field — allowed (tenant isolation enforced elsewhere)
        validate_filter_expression('account_id = "AB1234"', SCHEMA)


class TestFilterValidatorInvalidFields:
    """Tests for invalid/unknown field names."""

    def test_unknown_field_raises(self):
        with pytest.raises(RuleSyntaxError, match="does not exist"):
            validate_filter_expression('nonexistent = "value"', SCHEMA)

    def test_typo_field_raises(self):
        with pytest.raises(RuleSyntaxError, match="does not exist"):
            validate_filter_expression('pric = 100', SCHEMA)

    def test_unknown_field_in_and_raises(self):
        with pytest.raises(RuleSyntaxError):
            validate_filter_expression('title = "x" && badfield = "y"', SCHEMA)

    def test_unknown_field_in_in_raises(self):
        with pytest.raises(RuleSyntaxError):
            validate_filter_expression('badfield IN ("a", "b")', SCHEMA)

    def test_error_message_lists_available_fields(self):
        with pytest.raises(RuleSyntaxError, match="Available fields"):
            validate_filter_expression('nofield = "x"', SCHEMA)


class TestFilterValidatorContextVariables:
    """Tests that context variables are rejected."""

    def test_rejects_auth_id(self):
        with pytest.raises(RuleSyntaxError, match="Context variables"):
            validate_filter_expression('@request.auth.id = "user123"', SCHEMA)

    def test_rejects_auth_email(self):
        with pytest.raises(RuleSyntaxError, match="Context variables"):
            validate_filter_expression('@request.auth.email = "test@example.com"', SCHEMA)

    def test_rejects_request_data(self):
        with pytest.raises(RuleSyntaxError, match="Context variables"):
            validate_filter_expression('@request.data.title = "test"', SCHEMA)

    def test_rejects_any_at_prefix(self):
        with pytest.raises(RuleSyntaxError):
            validate_filter_expression('@something = "x"', SCHEMA)


class TestFilterValidatorOperatorTypeCompatibility:
    """Tests for operator/type compatibility rules."""

    def test_greater_than_on_boolean_raises(self):
        with pytest.raises(RuleSyntaxError, match="not supported"):
            validate_filter_expression("is_active > true", SCHEMA)

    def test_less_than_on_boolean_raises(self):
        with pytest.raises(RuleSyntaxError, match="not supported"):
            validate_filter_expression("is_active < false", SCHEMA)

    def test_like_on_number_raises(self):
        with pytest.raises(RuleSyntaxError, match="not supported"):
            validate_filter_expression('price ~ "%100%"', SCHEMA)

    def test_like_on_boolean_raises(self):
        with pytest.raises(RuleSyntaxError, match="not supported"):
            validate_filter_expression('is_active ~ "%true%"', SCHEMA)

    def test_json_only_supports_is_null(self):
        validate_filter_expression("metadata IS NULL", SCHEMA)
        validate_filter_expression("metadata IS NOT NULL", SCHEMA)

    def test_json_equality_raises(self):
        with pytest.raises(RuleSyntaxError, match="not supported"):
            validate_filter_expression('metadata = "x"', SCHEMA)

    def test_reference_equality_valid(self):
        validate_filter_expression('category_id = "abc"', SCHEMA)

    def test_reference_in_valid(self):
        validate_filter_expression('category_id IN ("a", "b")', SCHEMA)

    def test_reference_greater_than_raises(self):
        with pytest.raises(RuleSyntaxError, match="not supported"):
            validate_filter_expression("category_id > 100", SCHEMA)

    def test_boolean_equality_valid(self):
        validate_filter_expression("is_active = true", SCHEMA)

    def test_boolean_not_equal_valid(self):
        validate_filter_expression("is_active != false", SCHEMA)

    def test_boolean_is_null_valid(self):
        validate_filter_expression("is_active IS NULL", SCHEMA)


class TestFilterValidatorEmptyExpression:
    """Tests for empty filter expressions."""

    def test_empty_string_is_valid(self):
        validate_filter_expression("", SCHEMA)  # should not raise

    def test_whitespace_is_valid(self):
        validate_filter_expression("   ", SCHEMA)  # should not raise


class TestFilterValidatorMalformedExpressions:
    """Tests for malformed filter syntax."""

    def test_unclosed_paren_raises(self):
        with pytest.raises(RuleSyntaxError):
            validate_filter_expression('(status = "active"', SCHEMA)

    def test_missing_value_raises(self):
        with pytest.raises(RuleSyntaxError):
            validate_filter_expression("status =", SCHEMA)

    def test_invalid_character_raises(self):
        with pytest.raises(RuleSyntaxError):
            validate_filter_expression("status $ active", SCHEMA)
