"""Integration tests for audit log database schema (F3.6)."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession


# Enable audit hooks for all tests in this module
pytestmark = pytest.mark.enable_audit_hooks


@pytest.mark.asyncio
async def test_audit_log_table_exists(db_session: AsyncSession):
    """Test that the audit_log table exists in the database."""

    def get_table_names(conn):
        inspector = inspect(conn)
        return inspector.get_table_names()

    async with db_session.bind.connect() as conn:
        table_names = await conn.run_sync(get_table_names)

    assert "audit_log" in table_names, "audit_log table not found in database"


@pytest.mark.asyncio
async def test_audit_log_table_schema(db_session: AsyncSession):
    """Test that the audit_log table has all required columns."""

    def get_columns(conn):
        inspector = inspect(conn)
        return {col["name"]: col for col in inspector.get_columns("audit_log")}

    async with db_session.bind.connect() as conn:
        columns = await conn.run_sync(get_columns)

    # Core identification columns
    assert "id" in columns
    assert "account_id" in columns
    assert "operation" in columns
    assert "table_name" in columns
    assert "record_id" in columns
    assert "column_name" in columns

    # Value tracking columns
    assert "old_value" in columns
    assert "new_value" in columns

    # User context columns
    assert "user_id" in columns
    assert "user_email" in columns
    assert "user_name" in columns

    # Electronic signature columns
    assert "es_username" in columns
    assert "es_reason" in columns
    assert "es_timestamp" in columns

    # Request metadata columns
    assert "ip_address" in columns
    assert "user_agent" in columns
    assert "request_id" in columns

    # Timing and integrity columns
    assert "occurred_at" in columns
    assert "checksum" in columns
    assert "previous_hash" in columns

    # Additional data
    assert "extra_metadata" in columns

    # Check nullability for required fields
    assert not columns["id"]["nullable"]
    assert not columns["account_id"]["nullable"]
    assert not columns["operation"]["nullable"]
    assert not columns["table_name"]["nullable"]
    assert not columns["record_id"]["nullable"]
    assert not columns["column_name"]["nullable"]
    assert not columns["user_id"]["nullable"]
    assert not columns["user_email"]["nullable"]
    assert not columns["user_name"]["nullable"]
    assert not columns["occurred_at"]["nullable"]

    # Check nullability for optional fields
    assert columns["old_value"]["nullable"]
    assert columns["new_value"]["nullable"]
    assert columns["es_username"]["nullable"]
    assert columns["es_reason"]["nullable"]
    assert columns["es_timestamp"]["nullable"]
    assert columns["ip_address"]["nullable"]
    assert columns["user_agent"]["nullable"]
    assert columns["request_id"]["nullable"]
    assert columns["checksum"]["nullable"]
    assert columns["previous_hash"]["nullable"]
    assert columns["extra_metadata"]["nullable"]


@pytest.mark.asyncio
async def test_audit_log_indexes(db_session: AsyncSession):
    """Test that the audit_log table has all required indexes."""

    def get_indexes(conn):
        inspector = inspect(conn)
        return inspector.get_indexes("audit_log")

    async with db_session.bind.connect() as conn:
        indexes = await conn.run_sync(get_indexes)

    # Convert to a more searchable format
    index_names = {idx["name"] for idx in indexes}
    index_columns = {idx["name"]: idx["column_names"] for idx in indexes}

    # Check for required indexes
    # Note: SQLite may create indexes with different names, so we check for column combinations
    expected_index_columns = [
        ["account_id"],
        ["table_name"],
        ["record_id"],
        ["user_id"],
        ["occurred_at"],
        ["account_id", "table_name"],
        ["table_name", "record_id"],
    ]

    # Verify that we have indexes on the expected column combinations
    for expected_cols in expected_index_columns:
        found = any(
            set(idx_cols) == set(expected_cols) for idx_cols in index_columns.values()
        )
        assert found, f"Missing index on columns: {expected_cols}"


@pytest.mark.asyncio
async def test_audit_log_primary_key(db_session: AsyncSession):
    """Test that the audit_log table has the correct primary key."""

    def get_pk_constraint(conn):
        inspector = inspect(conn)
        return inspector.get_pk_constraint("audit_log")

    async with db_session.bind.connect() as conn:
        pk_constraint = await conn.run_sync(get_pk_constraint)

    assert "id" in pk_constraint["constrained_columns"]
    assert len(pk_constraint["constrained_columns"]) == 1


@pytest.mark.asyncio
async def test_audit_log_no_foreign_keys(db_session: AsyncSession):
    """Test that the audit_log table has no foreign key constraints.

    The audit log is intentionally independent to ensure it remains
    intact even if referenced records are deleted.
    """

    def get_foreign_keys(conn):
        inspector = inspect(conn)
        return inspector.get_foreign_keys("audit_log")

    async with db_session.bind.connect() as conn:
        foreign_keys = await conn.run_sync(get_foreign_keys)

    assert len(foreign_keys) == 0, "Audit log should not have foreign key constraints"
