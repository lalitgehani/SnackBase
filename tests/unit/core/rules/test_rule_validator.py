"""Tests for rule expression validator."""

import pytest

from snackbase.core.rules.exceptions import RuleSyntaxError
from snackbase.core.rules.rule_validator import validate_rule_expression


class TestValidatorBasics:
    """Test basic validation."""

    def test_empty_string_valid(self):
        """Test that empty string (public) is valid."""
        validate_rule_expression("", "list", ["id", "created_by"])
        # Should not raise

    def test_none_valid(self):
        """Test that None (locked) is valid."""
        validate_rule_expression(None, "list", ["id", "created_by"])
        # Should not raise


class TestValidatorFieldNames:
    """Test field name validation."""

    def test_valid_field_name(self):
        """Test validation with valid field name."""
        validate_rule_expression("created_by = @request.auth.id", "list", ["created_by"])
        # Should not raise

    def test_invalid_field_name(self):
        """Test error on invalid field name."""
        with pytest.raises(RuleSyntaxError, match="Field 'invalid_field' does not exist"):
            validate_rule_expression("invalid_field = 'test'", "list", ["created_by"])

    def test_multiple_valid_fields(self):
        """Test validation with multiple valid fields."""
        validate_rule_expression(
            "created_by = @request.auth.id && status = 'published'",
            "list",
            ["created_by", "status"]
        )
        # Should not raise

    def test_one_invalid_field_in_expression(self):
        """Test error when one field in expression is invalid."""
        with pytest.raises(RuleSyntaxError, match="Field 'invalid' does not exist"):
            validate_rule_expression(
                "created_by = @request.auth.id && invalid = 'test'",
                "list",
                ["created_by"]
            )


class TestValidatorAuthVariables:
    """Test @request.auth.* validation."""

    def test_valid_auth_id(self):
        """Test validation with @request.auth.id."""
        validate_rule_expression("created_by = @request.auth.id", "list", ["created_by"])
        # Should not raise

    def test_valid_auth_email(self):
        """Test validation with @request.auth.email."""
        validate_rule_expression("email = @request.auth.email", "list", ["email"])
        # Should not raise

    def test_valid_auth_role(self):
        """Test validation with @request.auth.role."""
        validate_rule_expression("@request.auth.role = 'admin'", "list", [])
        # Should not raise

    def test_valid_auth_account_id(self):
        """Test validation with @request.auth.account_id."""
        validate_rule_expression(
            "account_id = @request.auth.account_id",
            "list",
            ["account_id"]
        )
        # Should not raise

    def test_invalid_auth_variable(self):
        """Test error on invalid @request.auth.* variable."""
        with pytest.raises(RuleSyntaxError, match="Invalid context variable"):
            validate_rule_expression("@request.auth.invalid = 'test'", "list", [])


class TestValidatorDataVariables:
    """Test @request.data.* validation."""

    def test_data_in_create_rule(self):
        """Test that @request.data.* is valid in create rules."""
        validate_rule_expression("@request.data.title != ''", "create", ["title"])
        # Should not raise

    def test_data_in_update_rule(self):
        """Test that @request.data.* is valid in update rules."""
        validate_rule_expression("@request.data.title != ''", "update", ["title"])
        # Should not raise

    def test_data_in_list_rule(self):
        """Test error when @request.data.* used in list rule."""
        with pytest.raises(
            RuleSyntaxError,
            match="'@request.data.\\*' can only be used in create/update rules"
        ):
            validate_rule_expression("@request.data.title = 'test'", "list", ["title"])

    def test_data_in_view_rule(self):
        """Test error when @request.data.* used in view rule."""
        with pytest.raises(
            RuleSyntaxError,
            match="'@request.data.\\*' can only be used in create/update rules"
        ):
            validate_rule_expression("@request.data.title = 'test'", "view", ["title"])

    def test_data_in_delete_rule(self):
        """Test error when @request.data.* used in delete rule."""
        with pytest.raises(
            RuleSyntaxError,
            match="'@request.data.\\*' can only be used in create/update rules"
        ):
            validate_rule_expression("@request.data.title = 'test'", "delete", ["title"])


class TestValidatorComplexExpressions:
    """Test validation of complex expressions."""

    def test_ownership_rule(self):
        """Test validation of ownership rule."""
        validate_rule_expression(
            "created_by = @request.auth.id",
            "list",
            ["created_by"]
        )
        # Should not raise

    def test_ownership_or_public(self):
        """Test validation of ownership or public rule."""
        validate_rule_expression(
            "created_by = @request.auth.id || public = true",
            "list",
            ["created_by", "public"]
        )
        # Should not raise

    def test_account_isolation(self):
        """Test validation of account isolation rule."""
        validate_rule_expression(
            "account_id = @request.auth.account_id",
            "list",
            ["account_id"]
        )
        # Should not raise

    def test_multi_condition(self):
        """Test validation of multi-condition rule."""
        validate_rule_expression(
            "created_by = @request.auth.id && status = 'published' && public = true",
            "list",
            ["created_by", "status", "public"]
        )
        # Should not raise

    def test_create_rule_with_data(self):
        """Test validation of create rule with @request.data.*."""
        validate_rule_expression(
            "@request.auth.id != '' && @request.data.title != ''",
            "create",
            ["title"]
        )
        # Should not raise


class TestValidatorSyntaxErrors:
    """Test validation of syntax errors."""

    def test_invalid_syntax(self):
        """Test error on invalid syntax."""
        with pytest.raises(RuleSyntaxError):
            validate_rule_expression("created_by = = @request.auth.id", "list", ["created_by"])

    def test_unterminated_string(self):
        """Test error on unterminated string."""
        with pytest.raises(RuleSyntaxError, match="Unterminated string"):
            validate_rule_expression("status = 'draft", "list", ["status"])

    def test_missing_operand(self):
        """Test error on missing operand."""
        with pytest.raises(RuleSyntaxError):
            validate_rule_expression("created_by =", "list", ["created_by"])


class TestValidatorErrorMessages:
    """Test validation error messages."""

    def test_field_error_shows_available_fields(self):
        """Test that field error shows available fields."""
        with pytest.raises(RuleSyntaxError, match="Available fields:"):
            validate_rule_expression("invalid = 'test'", "list", ["id", "name", "status"])

    def test_auth_error_shows_valid_variables(self):
        """Test that auth error shows valid variables."""
        with pytest.raises(RuleSyntaxError, match="Valid:"):
            validate_rule_expression("@request.auth.invalid = 'test'", "list", [])

    def test_data_error_shows_operation(self):
        """Test that data error shows current operation."""
        with pytest.raises(RuleSyntaxError, match="not in 'list' rules"):
            validate_rule_expression("@request.data.title = 'test'", "list", ["title"])


class TestValidatorOperations:
    """Test validation for different operations."""

    def test_list_operation(self):
        """Test validation for list operation."""
        validate_rule_expression("created_by = @request.auth.id", "list", ["created_by"])
        # Should not raise

    def test_view_operation(self):
        """Test validation for view operation."""
        validate_rule_expression("created_by = @request.auth.id", "view", ["created_by"])
        # Should not raise

    def test_create_operation(self):
        """Test validation for create operation."""
        validate_rule_expression(
            "@request.auth.id != '' && @request.data.title != ''",
            "create",
            ["title"]
        )
        # Should not raise

    def test_update_operation(self):
        """Test validation for update operation."""
        validate_rule_expression(
            "created_by = @request.auth.id && @request.data.title != ''",
            "update",
            ["created_by", "title"]
        )
        # Should not raise

    def test_delete_operation(self):
        """Test validation for delete operation."""
        validate_rule_expression("created_by = @request.auth.id", "delete", ["created_by"])
        # Should not raise
