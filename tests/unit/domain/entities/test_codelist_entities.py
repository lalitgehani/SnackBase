"""Unit tests for codelist domain entities."""

import pytest

from snackbase.domain.entities.codelist import (
    Codelist,
    CodelistAccountOverride,
    CodelistValue,
    CodelistValueLabel,
    EffectiveCodelistValue,
)


def test_codelist_valid():
    c = Codelist(
        id="id1",
        code="regions",
        name="Regions",
        account_id="00000000-0000-0000-0000-000000000000",
        scope="system",
        is_builtin=True,
    )
    assert c.is_builtin is True


def test_override_visibility():
    with pytest.raises(ValueError, match="visibility"):
        CodelistAccountOverride(
            id="1",
            account_id="a",
            codelist_id="c",
            value_id="v",
            visibility="deleted",
        )


def test_effective_dto():
    e = EffectiveCodelistValue(
        code="eu-01",
        label="EU",
        definition=None,
        metadata={"country": "DE"},
        is_default=False,
        sort_order=1,
        scope="system",
        is_active=True,
        value_id="v",
        codelist_id="c",
    )
    assert e.metadata["country"] == "DE"
