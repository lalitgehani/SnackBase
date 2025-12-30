"""Integration tests for audit log repository operations (F3.6)."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)


@pytest.mark.asyncio
async def test_create_audit_log_entry(db_session: AsyncSession):
    """Test creating a single audit log entry."""
    repo = AuditLogRepository(db_session)

    audit_entry = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-123",
        column_name="email",
        old_value=None,
        new_value="test@example.com",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        request_id="req-789",
        occurred_at=datetime.now(timezone.utc),
    )

    created_entry = await repo.create(audit_entry)
    await db_session.commit()

    # Verify entry was created
    assert created_entry.id is not None
    assert created_entry.checksum is not None
    assert created_entry.previous_hash is None  # First entry has no previous


@pytest.mark.asyncio
async def test_create_batch_audit_log_entries(db_session: AsyncSession):
    """Test creating multiple audit log entries in a batch."""
    repo = AuditLogRepository(db_session)

    # Create multiple entries for a multi-column update
    entries = [
        AuditLogModel(
            account_id="test-account-id",
            operation="UPDATE",
            table_name="customers",
            record_id="customer-123",
            column_name=column,
            old_value=f"old_{column}",
            new_value=f"new_{column}",
            user_id="user-456",
            user_email="admin@example.com",
            user_name="Admin User",
            occurred_at=datetime.now(timezone.utc),
        )
        for column in ["name", "email", "phone"]
    ]

    created_entries = await repo.create_batch(entries)
    await db_session.commit()

    # Verify all entries were created
    assert len(created_entries) == 3
    for entry in created_entries:
        assert entry.id is not None
        assert entry.checksum is not None


@pytest.mark.asyncio
async def test_checksum_calculation(db_session: AsyncSession):
    """Test that checksums are calculated correctly."""
    repo = AuditLogRepository(db_session)

    audit_entry = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-123",
        column_name="email",
        old_value=None,
        new_value="test@example.com",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        occurred_at=datetime.now(timezone.utc),
    )

    created_entry = await repo.create(audit_entry)
    await db_session.commit()

    # Verify checksum is a 64-character hex string (SHA-256)
    assert created_entry.checksum is not None
    assert len(created_entry.checksum) == 64
    assert all(c in "0123456789abcdef" for c in created_entry.checksum)


@pytest.mark.asyncio
async def test_previous_hash_chain(db_session: AsyncSession):
    """Test that the previous_hash chain links entries correctly."""
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

    # Verify the chain
    assert created_entry1.previous_hash is None  # First entry
    assert created_entry2.previous_hash == created_entry1.checksum  # Links to first


@pytest.mark.asyncio
async def test_sequence_number_generation(db_session: AsyncSession):
    """Test that sequence numbers are generated sequentially."""
    repo = AuditLogRepository(db_session)

    # Create multiple entries
    entries = []
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
        created_entry = await repo.create(entry)
        await db_session.flush()
        await db_session.refresh(created_entry)
        entries.append(created_entry)

    await db_session.commit()

    # Verify IDs are sequential
    for i in range(1, len(entries)):
        assert entries[i].id == entries[i - 1].id + 1



@pytest.mark.asyncio
async def test_count_all(db_session: AsyncSession):
    """Test counting all audit log entries."""
    repo = AuditLogRepository(db_session)

    # Initially should be 0
    count = await repo.count_all()
    assert count == 0

    # Create some entries
    for i in range(3):
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

    await db_session.commit()

    # Should now be 3
    count = await repo.count_all()
    assert count == 3


@pytest.mark.asyncio
async def test_electronic_signature_fields(db_session: AsyncSession):
    """Test that electronic signature fields are stored correctly."""
    repo = AuditLogRepository(db_session)

    es_timestamp = datetime.now(timezone.utc)
    audit_entry = AuditLogModel(
        account_id="test-account-id",
        operation="UPDATE",
        table_name="customers",
        record_id="customer-123",
        column_name="status",
        old_value="pending",
        new_value="approved",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        es_username="approver@example.com",
        es_reason="Approved after review",
        es_timestamp=es_timestamp,
        occurred_at=datetime.now(timezone.utc),
    )

    created_entry = await repo.create(audit_entry)
    await db_session.commit()

    # Verify electronic signature fields
    assert created_entry.es_username == "approver@example.com"
    assert created_entry.es_reason == "Approved after review"
    # SQLite stores datetime without timezone, so compare without tz
    assert created_entry.es_timestamp.replace(tzinfo=None) == es_timestamp.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_metadata_field(db_session: AsyncSession):
    """Test that extra_metadata JSON field is stored correctly."""
    repo = AuditLogRepository(db_session)

    extra_metadata = {
        "source": "api",
        "version": "1.0",
        "custom_field": "custom_value",
    }

    audit_entry = AuditLogModel(
        account_id="test-account-id",
        operation="CREATE",
        table_name="customers",
        record_id="customer-123",
        column_name="name",
        old_value=None,
        new_value="Test Customer",
        user_id="user-456",
        user_email="admin@example.com",
        user_name="Admin User",
        extra_metadata=extra_metadata,
        occurred_at=datetime.now(timezone.utc),
    )

    created_entry = await repo.create(audit_entry)
    await db_session.commit()

    # Verify metadata
    assert created_entry.extra_metadata == extra_metadata
    assert created_entry.extra_metadata["source"] == "api"
    assert created_entry.extra_metadata["version"] == "1.0"
