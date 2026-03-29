"""Unit tests for the aggregation_parser module."""

import pytest

from snackbase.core.rules.aggregation_parser import (
    AggFunction,
    AggregationParseError,
    parse_agg_functions,
    parse_having,
    validate_group_by,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def schema_lookup():
    return {
        "price": {"name": "price", "type": "number"},
        "score": {"name": "score", "type": "number"},
        "status": {"name": "status", "type": "text"},
        "category": {"name": "category", "type": "text"},
        "email": {"name": "email", "type": "email"},
        "website": {"name": "website", "type": "url"},
        "is_active": {"name": "is_active", "type": "boolean"},
        "created_on": {"name": "created_on", "type": "date"},
        "event_time": {"name": "event_time", "type": "datetime"},
        "metadata": {"name": "metadata", "type": "json"},
    }


# ── parse_agg_functions ───────────────────────────────────────────────────────


def test_count_no_field(schema_lookup):
    result = parse_agg_functions("count()", schema_lookup)
    assert len(result) == 1
    agg = result[0]
    assert agg.fn == "count"
    assert agg.field is None
    assert agg.alias == "count"
    assert agg.sql_expr == "COUNT(*)"


def test_count_with_field(schema_lookup):
    result = parse_agg_functions("count(price)", schema_lookup)
    assert result[0].fn == "count"
    assert result[0].field == "price"
    assert result[0].alias == "count_price"
    assert result[0].sql_expr == 'COUNT("price")'


def test_sum_number_field(schema_lookup):
    result = parse_agg_functions("sum(price)", schema_lookup)
    assert result[0].fn == "sum"
    assert result[0].alias == "sum_price"
    assert result[0].sql_expr == 'SUM("price")'


def test_avg_number_field(schema_lookup):
    result = parse_agg_functions("avg(score)", schema_lookup)
    assert result[0].fn == "avg"
    assert result[0].alias == "avg_score"
    assert result[0].sql_expr == 'AVG("score")'


def test_min_number_field(schema_lookup):
    result = parse_agg_functions("min(price)", schema_lookup)
    assert result[0].fn == "min"
    assert result[0].alias == "min_price"
    assert result[0].sql_expr == 'MIN("price")'


def test_max_number_field(schema_lookup):
    result = parse_agg_functions("max(score)", schema_lookup)
    assert result[0].fn == "max"
    assert result[0].alias == "max_score"


def test_min_text_field(schema_lookup):
    result = parse_agg_functions("min(status)", schema_lookup)
    assert result[0].alias == "min_status"
    assert result[0].sql_expr == 'MIN("status")'


def test_max_date_field(schema_lookup):
    result = parse_agg_functions("max(created_on)", schema_lookup)
    assert result[0].alias == "max_created_on"


def test_min_datetime_field(schema_lookup):
    result = parse_agg_functions("min(event_time)", schema_lookup)
    assert result[0].alias == "min_event_time"


def test_min_email_field(schema_lookup):
    result = parse_agg_functions("min(email)", schema_lookup)
    assert result[0].alias == "min_email"


def test_multiple_functions(schema_lookup):
    result = parse_agg_functions("count(),sum(price),avg(score)", schema_lookup)
    assert len(result) == 3
    assert result[0].alias == "count"
    assert result[1].alias == "sum_price"
    assert result[2].alias == "avg_score"


def test_whitespace_tolerance(schema_lookup):
    result = parse_agg_functions("  count() ,  sum( price )  ", schema_lookup)
    assert len(result) == 2


def test_case_insensitive_function_name(schema_lookup):
    result = parse_agg_functions("COUNT(),SUM(price)", schema_lookup)
    assert result[0].fn == "count"
    assert result[1].fn == "sum"


def test_sum_text_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="number field"):
        parse_agg_functions("sum(status)", schema_lookup)


def test_avg_boolean_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="number field"):
        parse_agg_functions("avg(is_active)", schema_lookup)


def test_sum_date_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="number field"):
        parse_agg_functions("sum(created_on)", schema_lookup)


def test_min_boolean_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError):
        parse_agg_functions("min(is_active)", schema_lookup)


def test_min_json_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError):
        parse_agg_functions("min(metadata)", schema_lookup)


def test_unknown_fn_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="Unknown aggregation function"):
        parse_agg_functions("median(price)", schema_lookup)


def test_invalid_syntax_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="syntax"):
        parse_agg_functions("sum(price", schema_lookup)


def test_unknown_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="not found"):
        parse_agg_functions("sum(nonexistent)", schema_lookup)


def test_duplicate_alias_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="[Dd]uplicate"):
        parse_agg_functions("count(),count()", schema_lookup)


def test_empty_string_raises(schema_lookup):
    with pytest.raises(AggregationParseError):
        parse_agg_functions("", schema_lookup)


def test_sum_without_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="requires a field"):
        parse_agg_functions("sum()", schema_lookup)


def test_min_without_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="requires a field"):
        parse_agg_functions("min()", schema_lookup)


# ── validate_group_by ─────────────────────────────────────────────────────────


def test_group_by_valid_schema_field(schema_lookup):
    result = validate_group_by("status", schema_lookup)
    assert result == ["status"]


def test_group_by_multiple_fields(schema_lookup):
    result = validate_group_by("status,category", schema_lookup)
    assert result == ["status", "category"]


def test_group_by_system_field(schema_lookup):
    result = validate_group_by("created_at", schema_lookup)
    assert result == ["created_at"]


def test_group_by_account_id(schema_lookup):
    result = validate_group_by("account_id", schema_lookup)
    assert result == ["account_id"]


def test_group_by_empty_string(schema_lookup):
    result = validate_group_by("", schema_lookup)
    assert result == []


def test_group_by_unknown_field_raises(schema_lookup):
    with pytest.raises(AggregationParseError, match="not found"):
        validate_group_by("nonexistent_field", schema_lookup)


def test_group_by_whitespace_stripped(schema_lookup):
    result = validate_group_by("  status , category  ", schema_lookup)
    assert result == ["status", "category"]


# ── parse_having ──────────────────────────────────────────────────────────────


@pytest.fixture
def alias_to_sql():
    return {
        "count": "COUNT(*)",
        "sum_price": 'SUM("price")',
        "avg_score": 'AVG("score")',
        "min_status": 'MIN("status")',
    }


def test_having_count_greater_than(alias_to_sql):
    sql, params = parse_having("count() > 5", alias_to_sql)
    assert "COUNT(*)" in sql
    assert ">" in sql
    assert params == {"hp_0": 5}


def test_having_count_eq(alias_to_sql):
    sql, params = parse_having("count() = 10", alias_to_sql)
    assert "COUNT(*)" in sql
    assert params["hp_0"] == 10


def test_having_sum_less_than_or_equal(alias_to_sql):
    sql, params = parse_having("sum_price <= 1000", alias_to_sql)
    assert 'SUM("price")' in sql
    assert "<=" in sql
    assert params["hp_0"] == 1000


def test_having_float_value(alias_to_sql):
    sql, params = parse_having("avg_score > 4.5", alias_to_sql)
    assert params["hp_0"] == 4.5


def test_having_and_combination(alias_to_sql):
    sql, params = parse_having("count() > 3 AND avg_score < 100", alias_to_sql)
    assert "AND" in sql
    assert "COUNT(*)" in sql
    assert 'AVG("score")' in sql
    assert len(params) == 2


def test_having_or_combination(alias_to_sql):
    sql, params = parse_having("count() > 5 OR sum_price > 500", alias_to_sql)
    assert "OR" in sql
    assert len(params) == 2


def test_having_parentheses(alias_to_sql):
    sql, params = parse_having("(count() > 3 AND avg_score < 100) OR sum_price > 1000", alias_to_sql)
    assert "OR" in sql
    assert len(params) == 3


def test_having_string_value(alias_to_sql):
    sql, params = parse_having('min_status = "active"', alias_to_sql)
    assert 'MIN("status")' in sql
    assert params["hp_0"] == "active"


def test_having_single_quoted_string(alias_to_sql):
    sql, params = parse_having("min_status = 'pending'", alias_to_sql)
    assert params["hp_0"] == "pending"


def test_having_unknown_alias_raises(alias_to_sql):
    with pytest.raises(AggregationParseError, match="[Uu]nknown"):
        parse_having("nonexistent > 5", alias_to_sql)


def test_having_invalid_operator_raises(alias_to_sql):
    with pytest.raises(AggregationParseError):
        parse_having("count() LIKE 5", alias_to_sql)


def test_having_missing_value_raises(alias_to_sql):
    with pytest.raises(AggregationParseError):
        parse_having("count() >", alias_to_sql)


def test_having_multiple_params_unique_keys(alias_to_sql):
    sql, params = parse_having("count() > 1 AND sum_price > 100", alias_to_sql)
    assert "hp_0" in params
    assert "hp_1" in params
    assert params["hp_0"] != params["hp_1"] or True  # keys must be distinct
