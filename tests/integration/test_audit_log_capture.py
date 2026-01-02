"""Integration tests for audit log capture (F3.7).

These tests verify that audit logs are automatically captured for
CREATE, UPDATE, DELETE operations on models using the synchronous
audit logging mechanism.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from snackbase.core.context import set_current_context, clear_current_context
from snackbase.domain.entities.hook_context import HookContext
from snackbase.infrastructure.persistence.models import UserModel, AccountModel
from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)

# Enable audit hooks for all tests in this module
pytestmark = pytest.mark.enable_audit_hooks


@pytest.mark.asyncio
async def test_audit_capture_create(db_session: AsyncSession):
    """Test that CREATE operations generate audit log entries."""
    
    # 1. Setup Context
    from dataclasses import dataclass
    
    @dataclass
    class MockUser:
        id: str
        email: str

    context = HookContext(
        app=None,
        user=MockUser(id="admin-123", email="admin@example.com"),
        account_id="test-account-123",
        request_id="req-123",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        user_name="Admin User",
    )
    set_current_context(context)

    try:
        # Create a test account first (audit might happen for this too if context has account_id)
        # Note: synchronus listener handles account creation specifically if account_id is missing
        account = AccountModel(
            id="test-account-123",
            account_code="AC0001",
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        
        # Create a test user
        user = UserModel(
            id="user-123",
            email="test@example.com",
            password_hash="hashed_password",
            account_id="test-account-123",
            role_id=1,
        )
        db_session.add(user)
        
        # 2. Trigger Audit (via commit/flush)
        await db_session.commit()
        
        # 3. Verify
        # Verify audit logs were created
        audit_repo = AuditLogRepository(db_session)
        count = await audit_repo.count_all()
        assert count > 0, "No audit log entries were created"
        
        # Check specific logs for user creation
        result = await db_session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.table_name == "users")
            .where(AuditLogModel.record_id == "user-123")
        )
        audit_logs = list(result.scalars().all())
        
        assert len(audit_logs) > 0, "No audit logs found for user creation"
        
        for log in audit_logs:
            assert log.operation == "CREATE"
            assert log.user_id == "admin-123"
            assert log.request_id == "req-123"

        # Verify password is masked
        password_logs = [log for log in audit_logs if log.column_name == "password_hash"]
        if password_logs:
            assert password_logs[0].new_value == "***", "Password should be masked"

    finally:
        clear_current_context()


@pytest.mark.asyncio
async def test_audit_capture_update(db_session: AsyncSession):
    """Test that UPDATE operations generate audit log entries."""
    
    # 1. Setup Initial Data (without context, or allow it)
    account = AccountModel(
        id="test-account-456",
        account_code="AC0002",
        name="Test Account 2",
        slug="test-account-2",
    )
    db_session.add(account)
    
    user = UserModel(
        id="user-456",
        email="original@example.com",
        password_hash="hashed_password",
        account_id="test-account-456",
        role_id=1,
    )
    db_session.add(user)
    await db_session.commit()
    
    # 2. Setup Context for Update
    from dataclasses import dataclass
    @dataclass
    class MockUser:
        id: str
        email: str

    context = HookContext(
        app=None,
        user=MockUser(id="admin-456", email="admin@example.com"),
        account_id="test-account-456",
        request_id="req-456",
        ip_address="192.168.1.2",
        user_agent="Chrome/1.0",
        user_name="Admin User 2",
    )
    set_current_context(context)
    
    try:
        # 3. Perform Update
        # Need to fetch fresh instance attached to session
        user = await db_session.get(UserModel, "user-456")
        user.email = "updated@example.com"
        
        await db_session.commit()
        
        # 4. Verify
        result = await db_session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.table_name == "users")
            .where(AuditLogModel.record_id == "user-456")
            # Only check update logs (ignore create logs from setup if any)
            .where(AuditLogModel.operation == "UPDATE")
        )
        audit_logs = list(result.scalars().all())
        
        assert len(audit_logs) >= 1, "No audit logs found for user update"
        
        # Check specific log for email
        email_logs = [log for log in audit_logs if log.column_name == "email"]
        assert len(email_logs) == 1, "Should have exactly one email audit log"
        
        email_log = email_logs[0]
        assert email_log.operation == "UPDATE"
        assert email_log.old_value == "original@example.com"
        assert email_log.new_value == "updated@example.com"
        assert email_log.user_id == "admin-456"

    finally:
        clear_current_context()


@pytest.mark.asyncio
async def test_audit_capture_delete(db_session: AsyncSession):
    """Test that DELETE operations generate audit log entries."""
    
    # 1. Setup Initial Data
    account = AccountModel(
        id="test-account-789",
        account_code="AC0003",
        name="Test Account 3",
        slug="test-account-3",
    )
    db_session.add(account)
    
    user = UserModel(
        id="user-789",
        email="delete@example.com",
        password_hash="hashed_password",
        account_id="test-account-789",
        role_id=1,
    )
    db_session.add(user)
    await db_session.commit()
    
    # 2. Setup Context for Delete
    from dataclasses import dataclass
    @dataclass
    class MockUser:
        id: str
        email: str

    context = HookContext(
        app=None,
        user=MockUser(id="admin-789", email="admin@example.com"),
        account_id="test-account-789",
        request_id="req-789",
        ip_address="192.168.1.3",
        user_agent="Safari/1.0",
        user_name="Admin User 3",
    )
    set_current_context(context)
    
    try:
        # 3. Perform Delete
        user = await db_session.get(UserModel, "user-789")
        await db_session.delete(user)
        await db_session.commit()
        
        # 4. Verify
        result = await db_session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.table_name == "users")
            .where(AuditLogModel.record_id == "user-789")
            .where(AuditLogModel.operation == "DELETE")
        )
        audit_logs = list(result.scalars().all())
        
        assert len(audit_logs) > 0, "No audit logs found for user deletion"
        
        for log in audit_logs:
            assert log.operation == "DELETE"
            assert log.new_value is None
            assert log.user_id == "admin-789"

    finally:
        clear_current_context()


@pytest.mark.asyncio
async def test_audit_capture_without_context(db_session: AsyncSession):
    """Test that audit capture gracefully handles missing context (no logs created)."""
    
    # Ensure no context is set
    clear_current_context()
    
    account = AccountModel(
        id="test-account-999",
        account_code="AC0004",
        name="Test Account 4",
        slug="test-account-4",
    )
    db_session.add(account)
    
    user = UserModel(
        id="user-999",
        email="nocontext@example.com",
        password_hash="hashed_password",
        account_id="test-account-999",
        role_id=1,
    )
    db_session.add(user)
    await db_session.commit()
    
    # Verify NO audit logs were created
    result = await db_session.execute(
        select(AuditLogModel)
        .where(AuditLogModel.table_name == "users")
        .where(AuditLogModel.record_id == "user-999")
    )
    audit_logs = list(result.scalars().all())
    
    assert len(audit_logs) == 0, "Audit logs should not be created without context"
