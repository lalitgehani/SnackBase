"""Unit tests for the ExpressionCompiler."""

import pytest

from snackbase.core.rules.ast import (
    BinaryOp,
    FunctionCall,
    IsNullOp,
    Literal,
    UnaryOp,
    Variable,
)
from snackbase.core.rules.expression_compiler import (
    ExpressionCompiler,
    ExpressionCompilationError,
    compile_expression_to_sql,
)


class TestExpressionCompilerArithmetic:
    """Tests for arithmetic operators."""

    def test_multiply_two_fields(self):
        sql, params = compile_expression_to_sql("price * quantity")
        assert sql == '("price" * "quantity")'
        assert params == {}

    def test_addition(self):
        sql, params = compile_expression_to_sql("a + b")
        assert sql == '("a" + "b")'
        assert params == {}

    def test_subtraction(self):
        sql, params = compile_expression_to_sql("total - discount")
        assert sql == '("total" - "discount")'
        assert params == {}

    def test_division(self):
        sql, params = compile_expression_to_sql("total / count")
        assert sql == '("total" / "count")'
        assert params == {}

    def test_modulo(self):
        sql, params = compile_expression_to_sql("score % 100")
        assert sql == '("score" % :ec_0)'
        assert params == {"ec_0": 100}

    def test_nested_arithmetic(self):
        sql, params = compile_expression_to_sql("(a + b) * c")
        assert sql == '(("a" + "b") * "c")'
        assert params == {}

    def test_field_mixed_with_literal(self):
        sql, params = compile_expression_to_sql("price * 1.1")
        assert sql == '("price" * :ec_0)'
        assert params == {"ec_0": 1.1}

    def test_unary_negation(self):
        sql, params = compile_expression_to_sql("-price")
        assert sql == '(-"price")'
        assert params == {}


class TestExpressionCompilerStringFunctions:
    """Tests for string functions (concat, upper, lower, trim, length, substring)."""

    def test_concat_sqlite(self):
        sql, params = compile_expression_to_sql(
            "concat(first_name, ' ', last_name)", dialect="sqlite"
        )
        assert sql == '("first_name" || :ec_0 || "last_name")'
        assert params == {"ec_0": " "}

    def test_concat_postgresql(self):
        sql, params = compile_expression_to_sql(
            "concat(first_name, ' ', last_name)", dialect="postgresql"
        )
        assert sql == 'CONCAT("first_name", :ec_0, "last_name")'
        assert params == {"ec_0": " "}

    def test_concat_requires_two_args(self):
        with pytest.raises(ExpressionCompilationError, match="concat"):
            compile_expression_to_sql("concat(name)")

    def test_upper(self):
        sql, params = compile_expression_to_sql("upper(name)")
        assert sql == 'UPPER("name")'
        assert params == {}

    def test_lower(self):
        sql, params = compile_expression_to_sql("lower(name)")
        assert sql == 'LOWER("name")'
        assert params == {}

    def test_trim(self):
        sql, params = compile_expression_to_sql("trim(name)")
        assert sql == 'TRIM("name")'
        assert params == {}

    def test_length(self):
        sql, params = compile_expression_to_sql("length(name)")
        assert sql == 'LENGTH("name")'
        assert params == {}

    def test_substring_sqlite_two_args(self):
        sql, params = compile_expression_to_sql("substring(name, 1)", dialect="sqlite")
        assert sql == 'SUBSTR("name", :ec_0)'
        assert params == {"ec_0": 1}

    def test_substring_postgresql_two_args(self):
        sql, params = compile_expression_to_sql("substring(name, 1)", dialect="postgresql")
        assert sql == 'SUBSTRING("name" FROM :ec_0)'
        assert params == {"ec_0": 1}

    def test_substring_sqlite_three_args(self):
        sql, params = compile_expression_to_sql("substring(name, 1, 5)", dialect="sqlite")
        assert sql == 'SUBSTR("name", :ec_0, :ec_1)'
        assert params == {"ec_0": 1, "ec_1": 5}

    def test_substring_postgresql_three_args(self):
        sql, params = compile_expression_to_sql("substring(name, 1, 5)", dialect="postgresql")
        assert sql == 'SUBSTRING("name" FROM :ec_0 FOR :ec_1)'
        assert params == {"ec_0": 1, "ec_1": 5}

    def test_upper_wrong_arg_count(self):
        with pytest.raises(ExpressionCompilationError, match="upper"):
            compile_expression_to_sql("upper(a, b)")


class TestExpressionCompilerMathFunctions:
    """Tests for math functions (abs, round, ceil, floor)."""

    def test_abs(self):
        sql, params = compile_expression_to_sql("abs(price)")
        assert sql == 'ABS("price")'
        assert params == {}

    def test_round_no_decimals(self):
        sql, params = compile_expression_to_sql("round(price)")
        assert sql == 'ROUND("price")'
        assert params == {}

    def test_round_with_decimals(self):
        sql, params = compile_expression_to_sql("round(price, 2)")
        assert sql == 'ROUND("price", :ec_0)'
        assert params == {"ec_0": 2}

    def test_ceil_sqlite(self):
        sql, params = compile_expression_to_sql("ceil(rating)", dialect="sqlite")
        assert sql == 'CAST(ROUND("rating" + 0.4999999999) AS INTEGER)'
        assert params == {}

    def test_ceil_postgresql(self):
        sql, params = compile_expression_to_sql("ceil(rating)", dialect="postgresql")
        assert sql == 'CEIL("rating")'
        assert params == {}

    def test_floor_sqlite(self):
        sql, params = compile_expression_to_sql("floor(rating)", dialect="sqlite")
        assert sql == 'CAST(ROUND("rating" - 0.4999999999) AS INTEGER)'
        assert params == {}

    def test_floor_postgresql(self):
        sql, params = compile_expression_to_sql("floor(rating)", dialect="postgresql")
        assert sql == 'FLOOR("rating")'
        assert params == {}


class TestExpressionCompilerLogicFunctions:
    """Tests for logic functions (if, coalesce, nullif) and unary not."""

    def test_if_basic(self):
        sql, params = compile_expression_to_sql('if(price > 100, "expensive", "cheap")')
        assert sql == 'CASE WHEN ("price" > :ec_0) THEN :ec_1 ELSE :ec_2 END'
        assert params == {"ec_0": 100, "ec_1": "expensive", "ec_2": "cheap"}

    def test_if_wrong_arg_count(self):
        with pytest.raises(ExpressionCompilationError, match="if"):
            compile_expression_to_sql("if(a, b)")

    def test_coalesce(self):
        sql, params = compile_expression_to_sql('coalesce(nick, name, "Unknown")')
        assert sql == 'COALESCE("nick", "name", :ec_0)'
        assert params == {"ec_0": "Unknown"}

    def test_coalesce_requires_two_args(self):
        with pytest.raises(ExpressionCompilationError, match="coalesce"):
            compile_expression_to_sql("coalesce(a)")

    def test_nullif(self):
        sql, params = compile_expression_to_sql("nullif(score, 0)")
        assert sql == 'NULLIF("score", :ec_0)'
        assert params == {"ec_0": 0}

    def test_nullif_wrong_arg_count(self):
        with pytest.raises(ExpressionCompilationError, match="nullif"):
            compile_expression_to_sql("nullif(a, b, c)")

    def test_unary_not(self):
        compiler = ExpressionCompiler(dialect="sqlite")
        node = UnaryOp(operator="!", operand=Variable(name="is_active"))
        sql, params = compiler.compile(node)
        assert sql == '(NOT "is_active")'
        assert params == {}


class TestExpressionCompilerDateFunctions:
    """Tests for date functions (now, date_diff, date_add)."""

    def test_now_sqlite(self):
        sql, params = compile_expression_to_sql("now()", dialect="sqlite")
        assert sql == "datetime('now')"
        assert params == {}

    def test_now_postgresql(self):
        sql, params = compile_expression_to_sql("now()", dialect="postgresql")
        assert sql == "NOW()"
        assert params == {}

    def test_now_no_args_required(self):
        with pytest.raises(ExpressionCompilationError, match="now"):
            compile_expression_to_sql("now(a)")

    def test_date_diff_days_sqlite(self):
        sql, params = compile_expression_to_sql(
            'date_diff(updated_at, created_at, "days")', dialect="sqlite"
        )
        assert sql == '(JULIANDAY("updated_at") - JULIANDAY("created_at"))'
        assert params == {}

    def test_date_diff_hours_sqlite(self):
        sql, params = compile_expression_to_sql(
            'date_diff(updated_at, created_at, "hours")', dialect="sqlite"
        )
        assert sql == '((JULIANDAY("updated_at") - JULIANDAY("created_at")) * 24)'
        assert params == {}

    def test_date_diff_days_postgresql(self):
        sql, params = compile_expression_to_sql(
            'date_diff(updated_at, created_at, "days")', dialect="postgresql"
        )
        assert sql == 'EXTRACT(EPOCH FROM ("updated_at" - "created_at")) / 86400'
        assert params == {}

    def test_date_diff_invalid_unit(self):
        with pytest.raises(ExpressionCompilationError, match="weeks"):
            compile_expression_to_sql('date_diff(a, b, "weeks")')

    def test_date_diff_unit_must_be_literal(self):
        compiler = ExpressionCompiler(dialect="sqlite")
        node = FunctionCall(
            name="date_diff",
            args=[Variable("a"), Variable("b"), Variable("unit")],
        )
        with pytest.raises(ExpressionCompilationError, match="string literal"):
            compiler.compile(node)

    def test_date_add_sqlite(self):
        sql, params = compile_expression_to_sql(
            'date_add(created_at, 7, "days")', dialect="sqlite"
        )
        assert sql == "datetime(\"created_at\", (:ec_0) || ' days')"
        assert params == {"ec_0": 7}

    def test_date_add_postgresql(self):
        sql, params = compile_expression_to_sql(
            'date_add(created_at, 7, "days")', dialect="postgresql"
        )
        assert sql == '("created_at" + (:ec_0 || \' day\')::interval)'
        assert params == {"ec_0": 7}

    def test_date_add_months_unit_singularization(self):
        sql, params = compile_expression_to_sql(
            'date_add(created_at, 1, "months")', dialect="postgresql"
        )
        assert "' month'" in sql
        assert "' months'" not in sql

    def test_date_add_invalid_unit(self):
        with pytest.raises(ExpressionCompilationError, match="weeks"):
            compile_expression_to_sql('date_add(x, 1, "weeks")')


class TestExpressionCompilerFieldValidation:
    """Tests for field name validation using schema_fields."""

    def test_unknown_field_raises_with_schema_fields(self):
        with pytest.raises(ExpressionCompilationError, match="nonexistent"):
            compile_expression_to_sql(
                "nonexistent * 2", schema_fields={"price"}
            )

    def test_known_field_passes_with_schema_fields(self):
        sql, params = compile_expression_to_sql(
            "price * quantity", schema_fields={"price", "quantity"}
        )
        assert '"price"' in sql
        assert '"quantity"' in sql

    def test_no_schema_fields_skips_validation(self):
        # Should not raise even with unknown field when schema_fields=None
        sql, params = compile_expression_to_sql(
            "nonexistent * price", schema_fields=None
        )
        assert '"nonexistent"' in sql

    def test_context_variable_rejected(self):
        compiler = ExpressionCompiler(dialect="sqlite")
        node = Variable(name="@request")
        with pytest.raises(ExpressionCompilationError, match="Context variables"):
            compiler.compile(node)

    def test_system_fields_allowed_when_in_schema_fields(self):
        # System fields are valid when included in schema_fields set
        sql, params = compile_expression_to_sql(
            "length(created_by)",
            schema_fields={"created_by"},
        )
        assert 'LENGTH("created_by")' == sql


class TestExpressionCompilerErrorHandling:
    """Tests for error handling and edge cases."""

    def test_empty_expression_raises(self):
        with pytest.raises(ExpressionCompilationError):
            compile_expression_to_sql("")

    def test_whitespace_only_expression_raises(self):
        with pytest.raises(ExpressionCompilationError):
            compile_expression_to_sql("   ")

    def test_unknown_function_raises(self):
        with pytest.raises(ExpressionCompilationError, match="unknown_func"):
            compile_expression_to_sql("unknown_func(a)")

    def test_unsupported_operator_raises(self):
        compiler = ExpressionCompiler(dialect="sqlite")
        node = BinaryOp(left=Variable("a"), operator="**", right=Variable("b"))
        with pytest.raises(ExpressionCompilationError, match="Unsupported operator"):
            compiler.compile(node)

    def test_parameter_prefix_is_ec(self):
        _, params = compile_expression_to_sql("price * 1.5")
        for key in params:
            assert key.startswith("ec_"), f"Param key '{key}' does not start with 'ec_'"

    def test_param_counter_resets_between_calls(self):
        compiler = ExpressionCompiler(dialect="sqlite")
        node1 = BinaryOp(
            left=Variable("price"), operator="*", right=Literal(value=2)
        )
        sql1, params1 = compiler.compile(node1)
        assert "ec_0" in params1

        # Second compile call should also start from ec_0
        node2 = BinaryOp(
            left=Variable("total"), operator="+", right=Literal(value=5)
        )
        sql2, params2 = compiler.compile(node2)
        assert "ec_0" in params2


class TestExpressionCompilerIsNull:
    """Tests for IS NULL and IS NOT NULL expressions."""

    def test_is_null(self):
        compiler = ExpressionCompiler(dialect="sqlite")
        node = IsNullOp(operand=Variable(name="deleted_at"), is_null=True)
        sql, params = compiler.compile(node)
        assert sql == '("deleted_at" IS NULL)'
        assert params == {}

    def test_is_not_null(self):
        compiler = ExpressionCompiler(dialect="sqlite")
        node = IsNullOp(operand=Variable(name="deleted_at"), is_null=False)
        sql, params = compiler.compile(node)
        assert sql == '("deleted_at" IS NOT NULL)'
        assert params == {}
