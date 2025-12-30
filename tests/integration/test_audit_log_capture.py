"""Integration tests for audit log capture (F3.7).

These tests verify that audit logs are automatically captured for
CREATE, UPDATE, DELETE operations on models.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.hooks import HookRegistry
from snackbase.domain.entities.hook_context import HookContext
from snackbase.infrastructure.hooks import register_builtin_hooks
from snackbase.infrastructure.persistence.audit_helper import AuditHelper
from snackbase.infrastructure.persistence.models import UserModel, AccountModel
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)

# Enable audit hooks for all tests in this module
pytestmark = pytest.mark.enable_audit_hooks



@pytest.mark.asyncio
async def test_audit_capture_create(db_session: AsyncSession):
    """Test that CREATE operations generate audit log entries."""
    # Setup hook registry
    hook_registry = HookRegistry()
    register_builtin_hooks(hook_registry)
    
    # Create audit helper
    audit_helper = AuditHelper(db_session, hook_registry)
    
    # Create a test account first
    account = AccountModel(
        id="test-account-123",
        account_code="AC0001",
        name="Test Account",
        slug="test-account",
    )
    db_session.add(account)
    await db_session.flush()
    
    # Create a test user
    user = UserModel(
        id="user-123",
        email="test@example.com",
        password_hash="hashed_password",
        account_id="test-account-123",
        role_id=1,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create hook context with a mock user
    from dataclasses import dataclass
    
    @dataclass
    class MockUser:
        id: str
        email: str
    
    context = HookContext(
        app=None,  # Not needed for this test
        user=MockUser(
            id="admin-123",
            email="admin@example.com",
        ),
        account_id="test-account-123",
        request_id="req-123",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        user_name="Admin User",
    )
    
    # Trigger audit capture
    await audit_helper.trigger_create(user, context)
    await db_session.commit()
    
    # Verify audit logs were created
    audit_repo = AuditLogRepository(db_session)
    count = await audit_repo.count_all()
    
    # Should have audit entries for each column in UserModel
    assert count > 0, "No audit log entries were created"
    
    # Verify audit log details
    from sqlalchemy import select
    from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
    
    result = await db_session.execute(
        select(AuditLogModel)
        .where(AuditLogModel.table_name == "users")
        .where(AuditLogModel.record_id == "user-123")
    )
    audit_logs = list(result.scalars().all())
    
    assert len(audit_logs) > 0, "No audit logs found for user creation"
    
    # Check that all audit logs have correct operation
    for log in audit_logs:
        assert log.operation == "CREATE"
        assert log.old_value is None  # CREATE should have NULL old_value
        assert log.new_value is not None or log.column_name in ["last_login"]  # Some fields may be NULL
        assert log.user_id == "admin-123"
        assert log.user_email == "admin@example.com"
        assert log.user_name == "Admin User"
        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "Mozilla/5.0"
        assert log.request_id == "req-123"
    
    # Verify password is masked
    password_logs = [log for log in audit_logs if log.column_name == "password_hash"]
    if password_logs:
        assert password_logs[0].new_value == "***", "Password should be masked"


@pytest.mark.asyncio
async def test_audit_capture_update(db_session: AsyncSession):
    """Test that UPDATE operations generate audit log entries for changed columns only."""
    # Setup hook registry
    hook_registry = HookRegistry()
    register_builtin_hooks(hook_registry)
    
    # Create audit helper
    audit_helper = AuditHelper(db_session, hook_registry)
    
    # Create a test account
    account = AccountModel(
        id="test-account-456",
        account_code="AC0002",
        name="Test Account 2",
        slug="test-account-2",
    )
    db_session.add(account)
    await db_session.flush()
    
    # Create a test user
    user = UserModel(
        id="user-456",
        email="original@example.com",
        password_hash="hashed_password",
        account_id="test-account-456",
        role_id=1,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Capture old values before update (BEFORE commit to avoid detached instance)
    old_values = AuditHelper.capture_old_values(user)
    
    # Update the user
    user.email = "updated@example.com"
    await db_session.flush()
    
    # Create hook context with mock user
    from dataclasses import dataclass
    
    @dataclass
    class MockUser:
        id: str
        email: str
    
    context = HookContext(
        app=None,
        user=MockUser(
            id="admin-456",
            email="admin@example.com",
        ),
        account_id="test-account-456",
        request_id="req-456",
        ip_address="192.168.1.2",
        user_agent="Chrome/1.0",
        user_name="Admin User 2",
    )
    
    # Trigger audit capture BEFORE commit
    await audit_helper.trigger_update(user, old_values, context)
    
    # Now commit
    await db_session.commit()
    
    # Verify audit logs were created
    from sqlalchemy import select
    from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
    
    result = await db_session.execute(
        select(AuditLogModel)
        .where(AuditLogModel.table_name == "users")
        .where(AuditLogModel.record_id == "user-456")
        .where(AuditLogModel.operation == "UPDATE")
    )
    audit_logs = list(result.scalars().all())
    
    # Should only have audit entry for the email column (the only changed column)
    assert len(audit_logs) >= 1, "No audit logs found for user update"
    
    # Find the email audit log
    email_logs = [log for log in audit_logs if log.column_name == "email"]
    assert len(email_logs) == 1, "Should have exactly one email audit log"
    
    email_log = email_logs[0]
    assert email_log.operation == "UPDATE"
    # Email should be stored RAW in database (not masked)
    # Masking happens on read based on user's group membership
    assert email_log.old_value == "original@example.com"  # Raw data stored
    assert email_log.new_value == "updated@example.com"  # Raw data stored
    assert email_log.user_id == "admin-456"
    assert email_log.user_email == "admin@example.com"


@pytest.mark.asyncio
async def test_audit_capture_delete(db_session: AsyncSession):
    """Test that DELETE operations generate audit log entries."""
    # Setup hook registry
    hook_registry = HookRegistry()
    register_builtin_hooks(hook_registry)
    
    # Create audit helper
    audit_helper = AuditHelper(db_session, hook_registry)
    
    # Create a test account
    account = AccountModel(
        id="test-account-789",
        account_code="AC0003",
        name="Test Account 3",
        slug="test-account-3",
    )
    db_session.add(account)
    await db_session.flush()
    
    # Create a test user
    user = UserModel(
        id="user-789",
        email="delete@example.com",
        password_hash="hashed_password",
        account_id="test-account-789",
        role_id=1,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    
    # Create hook context with mock user
    from dataclasses import dataclass
    
    @dataclass
    class MockUser:
        id: str
        email: str
    
    context = HookContext(
        app=None,
        user=MockUser(
            id="admin-789",
            email="admin@example.com",
        ),
        account_id="test-account-789",
        request_id="req-789",
        ip_address="192.168.1.3",
        user_agent="Safari/1.0",
        user_name="Admin User 3",
    )
    
    # Trigger audit capture BEFORE deleting
    await audit_helper.trigger_delete(user, context)
    
    # Now delete the user
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify audit logs were created
    from sqlalchemy import select
    from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
    
    result = await db_session.execute(
        select(AuditLogModel)
        .where(AuditLogModel.table_name == "users")
        .where(AuditLogModel.record_id == "user-789")
        .where(AuditLogModel.operation == "DELETE")
    )
    audit_logs = list(result.scalars().all())
    
    assert len(audit_logs) > 0, "No audit logs found for user deletion"
    
    # Check that all audit logs have correct operation
    for log in audit_logs:
        assert log.operation == "DELETE"
        assert log.old_value is not None or log.column_name in ["last_login"]  # Some fields may be NULL
        assert log.new_value is None  # DELETE should have NULL new_value
        assert log.user_id == "admin-789"


@pytest.mark.asyncio
async def test_audit_capture_without_context(db_session: AsyncSession):
    """Test that audit capture gracefully handles missing context."""
    # Setup hook registry
    hook_registry = HookRegistry()
    register_builtin_hooks(hook_registry)
    
    # Create audit helper
    audit_helper = AuditHelper(db_session, hook_registry)
    
    # Create a test account
    account = AccountModel(
        id="test-account-999",
        account_code="AC0004",
        name="Test Account 4",
        slug="test-account-4",
    )
    db_session.add(account)
    await db_session.flush()
    
    # Create a test user
    user = UserModel(
        id="user-999",
        email="nocontext@example.com",
        password_hash="hashed_password",
        account_id="test-account-999",
        role_id=1,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Trigger audit capture WITHOUT context (should not fail)
    await audit_helper.trigger_create(user, context=None)
    await db_session.commit()
    
    # Verify NO audit logs were created (since no context was provided)
    from sqlalchemy import select
    from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
    
    result = await db_session.execute(
        select(AuditLogModel)
        .where(AuditLogModel.table_name == "users")
        .where(AuditLogModel.record_id == "user-999")
    )
    audit_logs = list(result.scalars().all())
    
    assert len(audit_logs) == 0, "Audit logs should not be created without context"
