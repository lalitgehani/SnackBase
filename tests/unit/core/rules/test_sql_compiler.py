"""Tests for SQL compiler."""

import pytest

from snackbase.core.rules.exceptions import RuleEvaluationError
from snackbase.core.rules.sql_compiler import compile_to_sql


class TestSQLCompilerBasics:
    """Test basic SQL compilation."""

    def test_empty_string_public(self):
        """Test that empty string compiles to public access."""
        sql, params = compile_to_sql("")
        assert sql == "1=1"
        assert params == {}

    def test_none_locked(self):
        """Test that None compiles to locked/deny all."""
        sql, params = compile_to_sql(None)
        assert sql == "1=0"
        assert params == {}


class TestSQLCompilerLiterals:
    """Test compiling literal values."""

    def test_string_literal(self):
        """Test compiling string literal."""
        sql, params = compile_to_sql("status = 'published'")
        assert "status = :param_0" in sql
        assert params["param_0"] == "published"

    def test_integer_literal(self):
        """Test compiling integer literal."""
        sql, params = compile_to_sql("age = 18")
        assert "age = :param_0" in sql
        assert params["param_0"] == 18

    def test_boolean_literal(self):
        """Test compiling boolean literal."""
        sql, params = compile_to_sql("public = true")
        assert "public = :param_0" in sql
        assert params["param_0"] is True

    def test_null_literal(self):
        """Test compiling null literal."""
        sql, params = compile_to_sql("deleted_at = null")
        assert "deleted_at = :param_0" in sql
        assert params["param_0"] is None


class TestSQLCompilerContextVariables:
    """Test compiling context variables."""

    def test_auth_id(self):
        """Test compiling @request.auth.id."""
        sql, params = compile_to_sql(
            "created_by = @request.auth.id", {"id": "user123"}
        )
        assert "created_by = :auth_id" in sql
        assert params["auth_id"] == "user123"

    def test_auth_email(self):
        """Test compiling @request.auth.email."""
        sql, params = compile_to_sql(
            "email = @request.auth.email", {"email": "user@example.com"}
        )
        assert "email = :auth_email" in sql
        assert params["auth_email"] == "user@example.com"

    def test_auth_role(self):
        """Test compiling @request.auth.role."""
        sql, params = compile_to_sql(
            "@request.auth.role = 'admin'", {"role": "admin"}
        )
        assert ":auth_role = :param_0" in sql
        assert params["auth_role"] == "admin"
        assert params["param_0"] == "admin"

    def test_auth_account_id(self):
        """Test compiling @request.auth.account_id."""
        sql, params = compile_to_sql(
            "account_id = @request.auth.account_id", {"account_id": "acc123"}
        )
        assert "account_id = :auth_account_id" in sql
        assert params["auth_account_id"] == "acc123"

    def test_data_variable(self):
        """Test compiling @request.data.* variable."""
        sql, params = compile_to_sql("@request.data.title != ''")
        assert ":data_title != :param_0" in sql
        assert params["data_title"] is None  # Placeholder
        assert params["param_0"] == ""

    def test_invalid_auth_variable(self):
        """Test error on invalid @request.auth.* variable."""
        with pytest.raises(RuleEvaluationError, match="Invalid context variable"):
            compile_to_sql("@request.auth.invalid = 'test'")


class TestSQLCompilerOperators:
    """Test compiling operators."""

    def test_equals(self):
        """Test compiling = operator."""
        sql, params = compile_to_sql("status = 'draft'")
        assert "status = :param_0" in sql

    def test_not_equals(self):
        """Test compiling != operator."""
        sql, params = compile_to_sql("status != 'draft'")
        assert "status != :param_0" in sql

    def test_less_than(self):
        """Test compiling < operator."""
        sql, params = compile_to_sql("age < 18")
        assert "age < :param_0" in sql

    def test_greater_than(self):
        """Test compiling > operator."""
        sql, params = compile_to_sql("age > 18")
        assert "age > :param_0" in sql

    def test_less_than_or_equal(self):
        """Test compiling <= operator."""
        sql, params = compile_to_sql("age <= 18")
        assert "age <= :param_0" in sql

    def test_greater_than_or_equal(self):
        """Test compiling >= operator."""
        sql, params = compile_to_sql("age >= 18")
        assert "age >= :param_0" in sql

    def test_like(self):
        """Test compiling ~ (LIKE) operator."""
        sql, params = compile_to_sql("name ~ 'John%'")
        assert "name LIKE :param_0" in sql
        assert params["param_0"] == "John%"


class TestSQLCompilerLogicalOperators:
    """Test compiling logical operators."""

    def test_and(self):
        """Test compiling && operator."""
        sql, params = compile_to_sql("created_by = @request.auth.id && status = 'published'", {"id": "user123"})
        assert "created_by = :auth_id AND status = :param_0" in sql
        assert params["auth_id"] == "user123"
        assert params["param_0"] == "published"

    def test_or(self):
        """Test compiling || operator."""
        sql, params = compile_to_sql("public = true || created_by = @request.auth.id", {"id": "user123"})
        assert "public = :param_0 OR created_by = :auth_id" in sql
        assert params["param_0"] is True
        assert params["auth_id"] == "user123"

    def test_not(self):
        """Test compiling ! operator."""
        sql, params = compile_to_sql("!(status = 'draft')")
        assert "NOT (status = :param_0)" in sql
        assert params["param_0"] == "draft"


class TestSQLCompilerParentheses:
    """Test compiling expressions with parentheses."""

    def test_parentheses_grouping(self):
        """Test that parentheses are preserved in SQL."""
        sql, params = compile_to_sql("(status = 'draft' || status = 'published') && public = true")
        # Logical operators should wrap in parentheses
        assert "OR" in sql
        assert "AND" in sql
        assert "(" in sql
        assert ")" in sql


class TestSQLCompilerComplexExpressions:
    """Test compiling complex expressions."""

    def test_ownership_rule(self):
        """Test compiling ownership rule."""
        sql, params = compile_to_sql("created_by = @request.auth.id", {"id": "user123"})
        assert sql == "created_by = :auth_id"
        assert params == {"auth_id": "user123"}

    def test_ownership_or_public(self):
        """Test compiling ownership or public rule."""
        sql, params = compile_to_sql(
            "created_by = @request.auth.id || public = true",
            {"id": "user123"}
        )
        assert "created_by = :auth_id OR public = :param_0" in sql
        assert params["auth_id"] == "user123"
        assert params["param_0"] is True

    def test_account_isolation(self):
        """Test compiling account isolation rule."""
        sql, params = compile_to_sql(
            "account_id = @request.auth.account_id",
            {"account_id": "acc123"}
        )
        assert sql == "account_id = :auth_account_id"
        assert params == {"auth_account_id": "acc123"}

    def test_multi_condition(self):
        """Test compiling multi-condition rule."""
        sql, params = compile_to_sql(
            "created_by = @request.auth.id && status = 'published' && public = true",
            {"id": "user123"}
        )
        assert "created_by = :auth_id" in sql
        assert "status = :param_0" in sql
        assert "public = :param_1" in sql
        assert "AND" in sql
        assert params["auth_id"] == "user123"
        assert params["param_0"] == "published"
        assert params["param_1"] is True

    def test_like_pattern(self):
        """Test compiling LIKE pattern."""
        sql, params = compile_to_sql("name ~ 'John%'")
        assert sql == "name LIKE :param_0"
        assert params == {"param_0": "John%"}


class TestSQLCompilerSecurity:
    """Test SQL injection prevention."""

    def test_parameterized_queries(self):
        """Test that all values are parameterized."""
        sql, params = compile_to_sql("status = 'published'")
        # Should use parameter, not inline value
        assert "'published'" not in sql
        assert ":param_0" in sql
        assert params["param_0"] == "published"


class TestSQLCompilerEdgeCases:
    """Test edge cases."""

    def test_empty_auth_context(self):
        """Test compilation with empty auth context."""
        sql, params = compile_to_sql("created_by = @request.auth.id", {})
        assert "created_by = :auth_id" in sql
        assert params["auth_id"] == ""  # Default to empty string

    def test_multiple_same_variable(self):
        """Test using same variable multiple times."""
        sql, params = compile_to_sql(
            "created_by = @request.auth.id || updated_by = @request.auth.id",
            {"id": "user123"}
        )
        # Both should use the same parameter
        assert params["auth_id"] == "user123"
        assert sql.count(":auth_id") == 2
