"""Computed list SQL must qualify field names against the record alias."""

from snackbase.infrastructure.persistence.repositories.record_repository import (
    _build_computed_select_parts,
)


def test_list_alias_qualifies_name_against_record_table():
    schema = [
        {"name": "name", "type": "text"},
        {
            "name": "label",
            "type": "computed",
            "expression": "concat(name, '')",
            "return_type": "text",
        },
    ]
    parts, _params = _build_computed_select_parts(schema, dialect="sqlite", table_alias="r")
    sql = parts[0][0]
    assert 'r."name"' in sql
    assert '"name"' in sql
    # Unqualified "name" would be ambiguous with accounts.name on list joins.
    assert sql.count('r."name"') >= 1
