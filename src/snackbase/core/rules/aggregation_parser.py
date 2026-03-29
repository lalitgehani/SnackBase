"""Aggregation query parser and validator.

Provides parsing and validation for the GET /{collection}/aggregate endpoint.
Supports COUNT, SUM, AVG, MIN, MAX with GROUP BY and HAVING clauses.
"""

import re
from dataclasses import dataclass
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_AGG_FUNCTIONS = {"count", "sum", "avg", "min", "max"}

# Types allowed for SUM and AVG
NUMERIC_TYPES = {"number"}

# Types allowed for MIN and MAX
ORDERABLE_TYPES = {"number", "date", "datetime", "text", "email", "url"}

# System fields that can be used in GROUP BY without being in the schema
SYSTEM_GROUPABLE_FIELDS = {"id", "account_id", "created_at", "updated_at", "created_by", "updated_by"}

# Regex to parse a single aggregation token like count(), sum(price), avg(field_name)
_AGG_TOKEN_RE = re.compile(r"^\s*(\w+)\(\s*(\w*)\s*\)\s*$", re.IGNORECASE)

# HAVING tokeniser
_HAVING_TOKEN_RE = re.compile(
    r"""
      (?P<number>-?\d+(?:\.\d+)?)
    | (?P<string>"[^"]*"|'[^']*')
    | (?P<op>>=|<=|!=|>|<|=)
    | (?P<and_kw>\bAND\b|\band\b|&&)
    | (?P<or_kw>\bOR\b|\bor\b|\|\|)
    | (?P<lparen>\()
    | (?P<rparen>\))
    | (?P<ident>[a-zA-Z_][a-zA-Z0-9_]*)
    | (?P<ws>\s+)
    """,
    re.VERBOSE,
)


# ── Error class ───────────────────────────────────────────────────────────────


class AggregationParseError(ValueError):
    """Raised when an aggregation expression cannot be parsed or validated."""


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class AggFunction:
    """A parsed and validated aggregation function."""

    fn: str            # "count", "sum", "avg", "min", "max"
    field: str | None  # None for count()
    alias: str         # Result key in response, e.g. "count", "sum_price"
    sql_expr: str      # SQL fragment, e.g. 'COUNT(*)', 'SUM("price")'


# ── Public API ────────────────────────────────────────────────────────────────


def parse_agg_functions(
    functions_str: str,
    schema_lookup: dict[str, dict],
) -> list[AggFunction]:
    """Parse and validate a comma-separated aggregation functions string.

    Args:
        functions_str: e.g. "count(),sum(price),avg(price)"
        schema_lookup: mapping of field name → field definition dict from collection schema.

    Returns:
        List of validated AggFunction instances.

    Raises:
        AggregationParseError: if any function is invalid, field is unknown, or type mismatch.
    """
    if not functions_str.strip():
        raise AggregationParseError("At least one aggregation function is required")

    raw_tokens = functions_str.split(",")
    results: list[AggFunction] = []
    seen_aliases: set[str] = set()

    for raw in raw_tokens:
        token = raw.strip()
        if not token:
            continue

        match = _AGG_TOKEN_RE.match(token)
        if not match:
            raise AggregationParseError(
                f"Invalid aggregation function syntax: '{token}'. "
                f"Expected format: fn() or fn(field_name)"
            )

        fn = match.group(1).lower()
        field = match.group(2) or None  # empty string → None

        if fn not in VALID_AGG_FUNCTIONS:
            raise AggregationParseError(
                f"Unknown aggregation function '{fn}'. "
                f"Supported functions: {', '.join(sorted(VALID_AGG_FUNCTIONS))}"
            )

        # Build alias and sql_expr
        if fn == "count" and field is None:
            alias = "count"
            sql_expr = "COUNT(*)"
        elif fn == "count" and field is not None:
            _validate_identifier(field)
            alias = f"count_{field}"
            sql_expr = f'COUNT("{field}")'
        else:
            # sum, avg, min, max all require a field
            if field is None:
                raise AggregationParseError(
                    f"Function '{fn}' requires a field argument, e.g. {fn}(field_name)"
                )
            _validate_identifier(field)

            # Validate field exists in schema
            field_def = schema_lookup.get(field)
            if field_def is None:
                raise AggregationParseError(
                    f"Field '{field}' not found in collection schema"
                )

            field_type = field_def.get("type", "text").lower()

            if fn in ("sum", "avg"):
                if field_type not in NUMERIC_TYPES:
                    raise AggregationParseError(
                        f"Function '{fn}' requires a number field, "
                        f"but field '{field}' has type '{field_type}'"
                    )
            elif fn in ("min", "max"):
                if field_type not in ORDERABLE_TYPES:
                    raise AggregationParseError(
                        f"Function '{fn}' is not supported for field type '{field_type}'. "
                        f"Supported types: {', '.join(sorted(ORDERABLE_TYPES))}"
                    )

            alias = f"{fn}_{field}"
            fn_upper = fn.upper()
            sql_expr = f'{fn_upper}("{field}")'

        # Check for duplicate aliases
        if alias in seen_aliases:
            raise AggregationParseError(
                f"Duplicate aggregation alias '{alias}'. "
                f"Each aggregation function must produce a unique result key"
            )
        seen_aliases.add(alias)

        results.append(AggFunction(fn=fn, field=field, alias=alias, sql_expr=sql_expr))

    if not results:
        raise AggregationParseError("At least one aggregation function is required")

    return results


def validate_group_by(
    group_by_str: str,
    schema_lookup: dict[str, dict],
) -> list[str]:
    """Parse and validate a comma-separated GROUP BY fields string.

    Args:
        group_by_str: e.g. "status,category"
        schema_lookup: mapping of field name → field definition dict from collection schema.

    Returns:
        List of validated field names.

    Raises:
        AggregationParseError: if any field is unknown or has an unsafe name.
    """
    if not group_by_str.strip():
        return []

    fields = [f.strip() for f in group_by_str.split(",")]
    result: list[str] = []

    for field in fields:
        if not field:
            continue
        _validate_identifier(field)
        if field not in schema_lookup and field not in SYSTEM_GROUPABLE_FIELDS:
            raise AggregationParseError(
                f"Field '{field}' not found in collection schema"
            )
        result.append(field)

    return result


def parse_having(
    having_str: str,
    alias_to_sql: dict[str, str],
) -> tuple[str, dict[str, Any]]:
    """Parse a HAVING expression referencing aggregation aliases.

    The grammar supports:
        expr     := and_expr (OR and_expr)*
        and_expr := cmp_expr (AND cmp_expr)*
        cmp_expr := '(' expr ')' | alias op value
        op       := '=' | '!=' | '<' | '>' | '<=' | '>='
        value    := number | string

    Identifiers are validated against alias_to_sql. When matched, the alias is
    substituted with its SQL expression (e.g. 'count' → 'COUNT(*)') for
    portability across SQL dialects that don't allow aliases in HAVING.

    Args:
        having_str: e.g. "count() > 5" or "sum_price > 100 AND count() > 1"
        alias_to_sql: mapping of alias → SQL expression from parse_agg_functions.

    Returns:
        (sql_fragment, params) where params use 'hp_' prefix.

    Raises:
        AggregationParseError: on unknown alias, invalid operator, or syntax error.
    """
    tokens = _tokenise_having(having_str)
    parser = _HavingParser(tokens, alias_to_sql)
    sql = parser.parse_expr()
    if parser.pos < len(parser.tokens):
        remaining = parser.tokens[parser.pos]
        raise AggregationParseError(
            f"Unexpected token '{remaining}' in HAVING expression"
        )
    return sql, parser.params


# ── Internal helpers ──────────────────────────────────────────────────────────


def _validate_identifier(name: str) -> None:
    """Validate that a field/alias name is a safe SQL identifier."""
    if not name.replace("_", "").isalnum():
        raise AggregationParseError(
            f"Invalid identifier '{name}': must contain only letters, digits, and underscores"
        )


def _tokenise_having(having_str: str) -> list[str]:
    """Tokenise a HAVING expression string into a flat list of token strings."""
    tokens: list[str] = []
    for m in _HAVING_TOKEN_RE.finditer(having_str):
        if m.lastgroup == "ws":
            continue
        tokens.append(m.group())
    return tokens


class _HavingParser:
    """Recursive-descent parser for HAVING expressions."""

    def __init__(self, tokens: list[str], alias_to_sql: dict[str, str]) -> None:
        self.tokens = tokens
        self.alias_to_sql = alias_to_sql
        self.pos = 0
        self._param_counter = 0
        self.params: dict[str, Any] = {}

    def _peek(self) -> str | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _consume(self) -> str:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, expected: str) -> None:
        tok = self._peek()
        if tok != expected:
            raise AggregationParseError(
                f"Expected '{expected}' but got '{tok}' in HAVING expression"
            )
        self.pos += 1

    def _is_and(self, tok: str | None) -> bool:
        return tok is not None and tok.upper() in ("AND", "&&")

    def _is_or(self, tok: str | None) -> bool:
        return tok is not None and tok.upper() in ("OR", "||")

    def parse_expr(self) -> str:
        left = self._parse_and_expr()
        while self._is_or(self._peek()):
            self._consume()
            right = self._parse_and_expr()
            left = f"({left} OR {right})"
        return left

    def _parse_and_expr(self) -> str:
        left = self._parse_cmp_expr()
        while self._is_and(self._peek()):
            self._consume()
            right = self._parse_cmp_expr()
            left = f"({left} AND {right})"
        return left

    def _parse_cmp_expr(self) -> str:
        tok = self._peek()
        if tok is None:
            raise AggregationParseError("Unexpected end of HAVING expression")

        if tok == "(":
            self._consume()
            inner = self.parse_expr()
            self._expect(")")
            return f"({inner})"

        # Must be an identifier (alias reference, optionally with `()` suffix)
        if not (tok and tok.replace("_", "").isalnum()):
            raise AggregationParseError(
                f"Expected an aggregate alias but got '{tok}' in HAVING expression"
            )
        self._consume()
        alias_name = tok

        # Support function-call notation: count(), sum(price), etc.
        # If the next tokens are `(` ... `)`, consume them and reconstruct the alias.
        if self._peek() == "(":
            self._consume()  # consume '('
            # Collect optional field name inside parens
            inner_tok = self._peek()
            field_part = ""
            if inner_tok and inner_tok != ")":
                self._consume()
                field_part = inner_tok
            self._expect(")")
            # Reconstruct alias: count() → "count", sum(price) → "sum_price"
            if field_part:
                alias_name = f"{alias_name}_{field_part}"

        if alias_name not in self.alias_to_sql:
            raise AggregationParseError(
                f"Unknown aggregate alias '{alias_name}' in HAVING expression. "
                f"Valid aliases: {', '.join(sorted(self.alias_to_sql))}"
            )
        sql_expr = self.alias_to_sql[alias_name]

        # Operator
        op_tok = self._peek()
        valid_ops = {"=", "!=", "<", ">", "<=", ">="}
        if op_tok not in valid_ops:
            raise AggregationParseError(
                f"Expected operator after '{tok}' but got '{op_tok}'. "
                f"Valid operators: {', '.join(sorted(valid_ops))}"
            )
        self._consume()
        op = op_tok

        # Value
        val_tok = self._peek()
        if val_tok is None:
            raise AggregationParseError(
                f"Expected a value after operator '{op}' in HAVING expression"
            )
        self._consume()

        param_name = f"hp_{self._param_counter}"
        self._param_counter += 1

        # Parse value
        if val_tok.startswith(("'", '"')):
            # String literal — strip quotes
            self.params[param_name] = val_tok[1:-1]
        elif "." in val_tok:
            try:
                self.params[param_name] = float(val_tok)
            except ValueError:
                raise AggregationParseError(f"Invalid numeric value '{val_tok}' in HAVING expression")
        else:
            try:
                self.params[param_name] = int(val_tok)
            except ValueError:
                raise AggregationParseError(f"Invalid value '{val_tok}' in HAVING expression")

        return f"{sql_expr} {op} :{param_name}"
