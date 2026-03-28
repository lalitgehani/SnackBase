"""Unit tests for the FilterCompiler."""

import pytest

from snackbase.core.rules.filter_compiler import (
    FilterCompilationError,
    compile_filter_to_sql,
)
from snackbase.core.rules.exceptions import RuleSyntaxError


class TestFilterCompilerBasicOperators:
    """Tests for basic comparison operators."""

    def test_equality(self):
        sql, params = compile_filter_to_sql('status = "active"')
        assert '"status" = :fp_0' in sql
        assert params["fp_0"] == "active"

    def test_not_equal(self):
        sql, params = compile_filter_to_sql('status != "archived"')
        assert '"status" != :fp_0' in sql
        assert params["fp_0"] == "archived"

    def test_greater_than(self):
        sql, params = compile_filter_to_sql("price > 100")
        assert '"price" > :fp_0' in sql
        assert params["fp_0"] == 100

    def test_less_than(self):
        sql, params = compile_filter_to_sql("age < 30")
        assert '"age" < :fp_0' in sql
        assert params["fp_0"] == 30

    def test_greater_than_or_equal(self):
        sql, params = compile_filter_to_sql("score >= 90")
        assert '"score" >= :fp_0' in sql
        assert params["fp_0"] == 90

    def test_less_than_or_equal(self):
        sql, params = compile_filter_to_sql("score <= 50")
        assert '"score" <= :fp_0' in sql
        assert params["fp_0"] == 50

    def test_like(self):
        sql, params = compile_filter_to_sql('name ~ "%john%"')
        assert '"name" LIKE :fp_0' in sql
        assert params["fp_0"] == "%john%"

    def test_boolean_true(self):
        sql, params = compile_filter_to_sql("is_active = true")
        assert '"is_active" = :fp_0' in sql
        assert params["fp_0"] is True

    def test_boolean_false(self):
        sql, params = compile_filter_to_sql("is_active = false")
        assert params["fp_0"] is False

    def test_null_literal(self):
        sql, params = compile_filter_to_sql("deleted_by = null")
        assert params["fp_0"] is None

    def test_float_value(self):
        sql, params = compile_filter_to_sql("rating > 4.5")
        assert params["fp_0"] == 4.5


class TestFilterCompilerInOperator:
    """Tests for the IN operator."""

    def test_in_strings(self):
        sql, params = compile_filter_to_sql('status IN ("active", "pending")')
        assert '"status" IN (:fp_0, :fp_1)' in sql
        assert params["fp_0"] == "active"
        assert params["fp_1"] == "pending"

    def test_in_numbers(self):
        sql, params = compile_filter_to_sql("priority IN (1, 2, 3)")
        assert '"priority" IN (:fp_0, :fp_1, :fp_2)' in sql
        assert params["fp_0"] == 1
        assert params["fp_1"] == 2
        assert params["fp_2"] == 3

    def test_in_single_value(self):
        sql, params = compile_filter_to_sql('type IN ("admin")')
        assert '"type" IN (:fp_0)' in sql
        assert params["fp_0"] == "admin"

    def test_in_many_values(self):
        sql, params = compile_filter_to_sql('tag IN ("a", "b", "c", "d", "e")')
        assert len(params) == 5


class TestFilterCompilerIsNull:
    """Tests for IS NULL and IS NOT NULL operators."""

    def test_is_null(self):
        sql, params = compile_filter_to_sql("deleted_at IS NULL")
        assert '"deleted_at" IS NULL' in sql
        assert not params  # No params for IS NULL

    def test_is_not_null(self):
        sql, params = compile_filter_to_sql("deleted_at IS NOT NULL")
        assert '"deleted_at" IS NOT NULL' in sql
        assert not params

    def test_is_null_uppercase(self):
        sql, params = compile_filter_to_sql("deleted_at IS NULL")
        assert "IS NULL" in sql


class TestFilterCompilerLogicalOperators:
    """Tests for AND, OR, NOT logical operators."""

    def test_and_operator(self):
        sql, params = compile_filter_to_sql('status = "active" && price > 100')
        assert "AND" in sql
        assert '"status" = :fp_0' in sql
        assert '"price" > :fp_1' in sql
        assert params["fp_0"] == "active"
        assert params["fp_1"] == 100

    def test_or_operator(self):
        sql, params = compile_filter_to_sql('status = "active" || status = "pending"')
        assert "OR" in sql
        assert params["fp_0"] == "active"
        assert params["fp_1"] == "pending"

    def test_not_operator(self):
        sql, params = compile_filter_to_sql('!( status = "archived")')
        assert "NOT" in sql

    def test_parentheses_grouping(self):
        sql, params = compile_filter_to_sql(
            '(status = "active" || status = "pending") && price > 100'
        )
        assert "AND" in sql
        assert "OR" in sql

    def test_complex_expression(self):
        sql, params = compile_filter_to_sql(
            'status = "active" && price > 100 && deleted_at IS NULL'
        )
        assert "AND" in sql
        assert '"deleted_at" IS NULL' in sql
        assert len(params) == 2  # status and price, not deleted_at


class TestFilterCompilerContextVariableRejection:
    """Tests that context variables are rejected."""

    def test_rejects_auth_id(self):
        with pytest.raises((FilterCompilationError, RuleSyntaxError)):
            compile_filter_to_sql('@request.auth.id = "user123"')

    def test_rejects_auth_email(self):
        with pytest.raises((FilterCompilationError, RuleSyntaxError)):
            compile_filter_to_sql('@request.auth.email = "test@example.com"')

    def test_rejects_request_data(self):
        with pytest.raises((FilterCompilationError, RuleSyntaxError)):
            compile_filter_to_sql('@request.data.title = "test"')


class TestFilterCompilerParameterization:
    """Tests that output is properly parameterized (no SQL injection)."""

    def test_string_values_are_parameterized(self):
        sql, params = compile_filter_to_sql("name = \"'; DROP TABLE users; --\"")
        # The malicious string should be a parameter, not inline SQL
        assert "DROP TABLE" not in sql
        assert params["fp_0"] == "'; DROP TABLE users; --"

    def test_multiple_params_no_collision(self):
        sql, params = compile_filter_to_sql('a = "x" && b = "y" && c = "z"')
        assert "fp_0" in params
        assert "fp_1" in params
        assert "fp_2" in params
        assert len(params) == 3

    def test_in_params_are_parameterized(self):
        sql, params = compile_filter_to_sql("id IN (\"'; DROP TABLE--\", \"ok\")")
        assert "DROP TABLE" not in sql
        assert any("DROP TABLE" in str(v) for v in params.values())


class TestFilterCompilerEmptyExpression:
    """Tests for empty/null filter expressions."""

    def test_empty_string(self):
        sql, params = compile_filter_to_sql("")
        assert sql == "1=1"
        assert not params

    def test_whitespace_only(self):
        sql, params = compile_filter_to_sql("   ")
        assert sql == "1=1"
        assert not params
