"""Integration tests for audit log immutability constraints (F3.6)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel


@pytest.mark.asyncio
async def test_audit_log_insert_succeeds(db_session: AsyncSession):
    """Test that INSERT operations work correctly on audit_log."""
    audit_entry = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="test_table",
        record_id="test-record-id",
        column_name="test_column",
        old_value=None,
        new_value="new_value",
        user_id="test-user-id",
        user_email="test@example.com",
        user_name="Test User",
        occurred_at=datetime.now(timezone.utc),
    )

    db_session.add(audit_entry)
    await db_session.commit()

    # Verify it was inserted
    assert audit_entry.id is not None


@pytest.mark.asyncio
async def test_audit_log_update_prevented(db_session: AsyncSession):
    """Test that UPDATE operations are prevented by database trigger."""
    # First, insert an audit entry
    audit_entry = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="test_table",
        record_id="test-record-id",
        column_name="test_column",
        old_value=None,
        new_value="original_value",
        user_id="test-user-id",
        user_email="test@example.com",
        user_name="Test User",
        occurred_at=datetime.now(timezone.utc),
    )

    db_session.add(audit_entry)
    await db_session.commit()

    entry_id = audit_entry.id

    # Attempt to update the entry directly via SQL
    # This should be prevented by the database trigger
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.execute(
            text(
                """
                UPDATE audit_log 
                SET new_value = 'modified_value' 
                WHERE id = :id
                """
            ),
            {"id": entry_id},
        )
        await db_session.commit()

    # Verify the error message mentions immutability
    error_message = str(exc_info.value).lower()
    assert "immutable" in error_message or "cannot be updated" in error_message

    # Rollback the failed transaction
    await db_session.rollback()


@pytest.mark.asyncio
async def test_audit_log_delete_prevented(db_session: AsyncSession):
    """Test that DELETE operations are prevented by database trigger."""
    # First, insert an audit entry
    audit_entry = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="test_table",
        record_id="test-record-id",
        column_name="test_column",
        old_value=None,
        new_value="value",
        user_id="test-user-id",
        user_email="test@example.com",
        user_name="Test User",
        occurred_at=datetime.now(timezone.utc),
    )

    db_session.add(audit_entry)
    await db_session.commit()

    entry_id = audit_entry.id

    # Attempt to delete the entry directly via SQL
    # This should be prevented by the database trigger
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.execute(
            text("DELETE FROM audit_log WHERE id = :id"),
            {"id": entry_id},
        )
        await db_session.commit()

    # Verify the error message mentions immutability
    error_message = str(exc_info.value).lower()
    assert "immutable" in error_message or "cannot be deleted" in error_message

    # Rollback the failed transaction
    await db_session.rollback()


@pytest.mark.asyncio
async def test_audit_log_triggers_exist(db_session: AsyncSession):
    """Test that the immutability triggers exist in the database."""

    def get_triggers(conn):
        # SQLite-specific query to get trigger names
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='trigger'")
        )
        return [row[0] for row in result.fetchall()]

    async with db_session.bind.connect() as conn:
        triggers = await conn.run_sync(get_triggers)

    # Check for the expected triggers
    assert "prevent_audit_log_update" in triggers
    assert "prevent_audit_log_delete" in triggers


@pytest.mark.asyncio
async def test_operation_constraint(db_session: AsyncSession):
    """Test that the operation column only accepts valid values."""
    # Valid operations should work
    for operation in ["CREATE", "UPDATE", "DELETE"]:
        audit_entry = AuditLogModel(
            account_id="test-account-id",
            operation=operation,
            table_name="test_table",
            record_id=f"test-record-{operation}",
            column_name="test_column",
            old_value=None,
            new_value="value",
            user_id="test-user-id",
            user_email="test@example.com",
            user_name="Test User",
            occurred_at=datetime.now(timezone.utc),
        )
        db_session.add(audit_entry)
        await db_session.commit()

    # Invalid operation should fail
    with pytest.raises(IntegrityError):
        audit_entry = AuditLogModel(
            account_id="test-account-id",
            operation="INVALID",
            table_name="test_table",
            record_id="test-record-invalid",
            column_name="test_column",
            old_value=None,
            new_value="value",
            user_id="test-user-id",
            user_email="test@example.com",
            user_name="Test User",
            occurred_at=datetime.now(timezone.utc),
        )
        db_session.add(audit_entry)
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_sequence_number_auto_increment(db_session: AsyncSession):
    """Test that sequence_number auto-increments without gaps."""
    # Create multiple audit entries
    entries = []
    for i in range(5):
        audit_entry = AuditLogModel(
            account_id="test-account-id",
            operation="CREATE",
            table_name="test_table",
            record_id=f"test-record-{i}",
            column_name="test_column",
            old_value=None,
            new_value=f"value_{i}",
            user_id="test-user-id",
            user_email="test@example.com",
            user_name="Test User",
            occurred_at=datetime.now(timezone.utc),
        )
        db_session.add(audit_entry)
        await db_session.flush()
        await db_session.refresh(audit_entry)
        entries.append(audit_entry)

    await db_session.commit()

    # Verify IDs are sequential
    ids = [entry.id for entry in entries]
    for i in range(1, len(ids)):
        assert ids[i] == ids[i - 1] + 1

