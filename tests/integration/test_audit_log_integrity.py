"""Integration tests for audit log integrity chain verification (F3.6)."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession


# Enable audit hooks for all tests in this module
pytestmark = pytest.mark.enable_audit_hooks

from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)


@pytest.mark.asyncio
async def test_verify_integrity_chain_empty(db_session: AsyncSession):
    """Test integrity verification with no entries."""
    repo = AuditLogRepository(db_session)

    is_valid, errors = await repo.verify_integrity_chain()

    assert is_valid is True
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_verify_integrity_chain_single_entry(db_session: AsyncSession):
    """Test integrity verification with a single entry."""
    repo = AuditLogRepository(db_session)

    entry = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-1",
        column_name="name",
        old_value=None,
        new_value="Customer 1",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )
    await repo.create(entry)
    await db_session.commit()

    is_valid, errors = await repo.verify_integrity_chain()

    if not is_valid:
        print(f"Errors: {errors}")
    assert is_valid is True
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_verify_integrity_chain_multiple_entries(db_session: AsyncSession):
    """Test integrity verification with multiple entries."""
    repo = AuditLogRepository(db_session)

    # Create a chain of entries
    for i in range(5):
        entry = AuditLogModel(
            account_id="test-account-id",
            operation="CREATE",
            table_name="customers",
            record_id=f"customer-{i}",
            column_name="name",
            old_value=None,
            new_value=f"Customer {i}",
            user_id="user-456",
            user_email="admin@example.com",
            user_name="Admin User",
            occurred_at=datetime.now(timezone.utc),
        )
        await repo.create(entry)
        await db_session.flush()

    await db_session.commit()

    is_valid, errors = await repo.verify_integrity_chain()

    assert is_valid is True
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_first_entry_has_null_previous_hash(db_session: AsyncSession):
    """Test that the first entry has NULL previous_hash."""
    repo = AuditLogRepository(db_session)

    entry = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-1",
        column_name="name",
        old_value=None,
        new_value="Customer 1",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )
    created_entry = await repo.create(entry)
    await db_session.commit()

    assert created_entry.previous_hash is None


@pytest.mark.asyncio
async def test_subsequent_entries_link_to_previous(db_session: AsyncSession):
    """Test that subsequent entries link to the previous entry's checksum."""
    repo = AuditLogRepository(db_session)

    # Create first entry
    entry1 = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-1",
        column_name="name",
        old_value=None,
        new_value="Customer 1",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )
    created_entry1 = await repo.create(entry1)
    await db_session.commit()

    # Create second entry
    entry2 = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-2",
        column_name="name",
        old_value=None,
        new_value="Customer 2",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )
    created_entry2 = await repo.create(entry2)
    await db_session.commit()

    # Create third entry
    entry3 = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-3",
        column_name="name",
        old_value=None,
        new_value="Customer 3",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )
    created_entry3 = await repo.create(entry3)
    await db_session.commit()

    # Verify the chain
    assert created_entry1.previous_hash is None
    assert created_entry2.previous_hash == created_entry1.checksum
    assert created_entry3.previous_hash == created_entry2.checksum


@pytest.mark.asyncio
async def test_batch_create_maintains_chain(db_session: AsyncSession):
    """Test that batch create maintains the integrity chain."""
    repo = AuditLogRepository(db_session)

    # Create first entry individually
    entry1 = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-1",
        column_name="name",
        old_value=None,
        new_value="Customer 1",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )
    created_entry1 = await repo.create(entry1)
    await db_session.commit()

    # Create batch of entries
    batch_entries = [
        AuditLogModel(
            account_id="test-account-id",
            operation="UPDATE",
            table_name="customers",
            record_id="customer-1",
            column_name=column,
            old_value=f"old_{column}",
            new_value=f"new_{column}",
            user_id="user-456",
            user_email="admin@example.com",
            user_name="Admin User",
            occurred_at=datetime.now(timezone.utc),
        )
        for column in ["email", "phone", "address"]
    ]
    created_batch = await repo.create_batch(batch_entries)
    await db_session.commit()

    # Verify the chain
    assert created_batch[0].previous_hash == created_entry1.checksum
    assert created_batch[1].previous_hash == created_batch[0].checksum
    assert created_batch[2].previous_hash == created_batch[1].checksum


@pytest.mark.asyncio
async def test_checksum_uniqueness(db_session: AsyncSession):
    """Test that different entries have different checksums."""
    repo = AuditLogRepository(db_session)

    # Create two different entries
    entry1 = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-1",
        column_name="name",
        old_value=None,
        new_value="Customer 1",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )
    created_entry1 = await repo.create(entry1)
    await db_session.commit()

    entry2 = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-2",
        column_name="name",
        old_value=None,
        new_value="Customer 2",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )
    created_entry2 = await repo.create(entry2)
    await db_session.commit()

    # Checksums should be different
    assert created_entry1.checksum != created_entry2.checksum
