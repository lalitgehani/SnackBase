import pytest

from types import SimpleNamespace

from snackbase.domain.services.view_query_validator import ViewQueryValidator


class FakeResult:
    def __init__(self, keys):
        self._keys = keys

    def keys(self):
        return list(self._keys)


class FakeSession:
    def __init__(self, result_keys):
        self._result_keys = result_keys

    async def execute(self, *_args, **_kwargs):
        return FakeResult(self._result_keys)


class FakeCollectionRepo:
    def __init__(self, session):
        self._session = session

    async def get_by_name(self, name):
        # Pretend all referenced collections exist and are base collections
        return SimpleNamespace(type="base")


@pytest.mark.asyncio
async def test_view_missing_system_columns_fails(monkeypatch):
    query = "SELECT o.id, o.account_id, o.total, c.name AS customer_name FROM orders o JOIN customers c ON o.customer_id = c.id"

    # Simulate DB returning columns that omit system timestamp and user columns
    result_keys = ["id", "account_id", "total", "customer_name"]
    session = FakeSession(result_keys)

    # Patch CollectionRepository used inside the validator (imported from repositories package)
    monkeypatch.setattr(
        "snackbase.infrastructure.persistence.repositories.CollectionRepository",
        FakeCollectionRepo,
    )

    errors, translated = await ViewQueryValidator.validate(query, session)

    assert errors, "Expected validation errors for missing system columns"
    codes = [e.code for e in errors]
    assert "missing_system_columns" in codes


@pytest.mark.asyncio
async def test_view_with_all_system_columns_passes(monkeypatch):
    query = (
        "SELECT o.id AS id, o.account_id AS account_id, o.total, o.created_at AS created_at, "
        "o.created_by AS created_by, o.updated_at AS updated_at, o.updated_by AS updated_by "
        "FROM orders o"
    )

    # Simulate DB returning all required system columns
    result_keys = ["id", "account_id", "total", "created_at", "created_by", "updated_at", "updated_by"]
    session = FakeSession(result_keys)

    monkeypatch.setattr(
        "snackbase.infrastructure.persistence.repositories.CollectionRepository",
        FakeCollectionRepo,
    )

    errors, translated = await ViewQueryValidator.validate(query, session)

    assert not errors, f"Expected no errors but got: {errors}"
    assert isinstance(translated, str) and translated.strip(), "Translated SQL should be returned"
