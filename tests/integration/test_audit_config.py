"""Integration tests for audit logging configuration toggle (F3.7.1)."""

import pytest
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
async def test_audit_logs_created_when_enabled(db_session: AsyncSession):
    """Verify audit logs are created when enabled (default)."""
    from dataclasses import dataclass
    @dataclass
    class MockUser:
        id: str
        email: str

    context = HookContext(
        app=None,
        user=MockUser(id="admin-1", email="admin1@example.com"),
        account_id="acc-1",
        request_id="req-1",
    )
    set_current_context(context)

    try:
        account = AccountModel(id="acc-1", account_code="AC0001", name="Acc 1", slug="acc-1")
        db_session.add(account)
        await db_session.commit()

        audit_repo = AuditLogRepository(db_session)
        count = await audit_repo.count_all()
        assert count > 0, "Audit logs should be created"
    finally:
        clear_current_context()

@pytest.mark.asyncio
async def test_audit_logs_not_created_when_disabled(db_session: AsyncSession, with_audit_disabled):
    """Verify audit logs are NOT created when disabled via config."""
    from dataclasses import dataclass
    @dataclass
    class MockUser:
        id: str
        email: str

    context = HookContext(
        app=None,
        user=MockUser(id="admin-2", email="admin2@example.com"),
        account_id="acc-2",
        request_id="req-2",
    )
    set_current_context(context)

    try:
        account = AccountModel(id="acc-2", account_code="AC0002", name="Acc 2", slug="acc-2")
        db_session.add(account)
        await db_session.commit()

        audit_repo = AuditLogRepository(db_session)
        count = await audit_repo.count_all()
        # We might have logs from previous tests if they use the same database, 
        # but here we use db_session which is fresh per test.
        assert count == 0, "Audit logs should NOT be created when disabled"
    finally:
        clear_current_context()

@pytest.mark.asyncio
async def test_health_check_audit_status(client):
    """Verify health check includes audit logging status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "audit_logging_enabled" in data
    assert data["audit_logging_enabled"] is True

@pytest.mark.asyncio
async def test_ready_check_audit_status(client):
    """Verify readiness check includes audit logging status."""
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert "audit_logging_enabled" in data
    assert data["audit_logging_enabled"] is True

@pytest.mark.asyncio
async def test_audit_log_api_metadata(client, superadmin_token):
    """Verify audit log API metadata includes status."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.get("/api/v1/audit-logs/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "audit_logging_enabled" in data
    assert data["audit_logging_enabled"] is True
