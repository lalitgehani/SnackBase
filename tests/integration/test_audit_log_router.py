"""Integration tests for audit log router."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
from snackbase.infrastructure.persistence.repositories.audit_log_repository import AuditLogRepository


@pytest_asyncio.fixture
async def sample_logs(db_session):
    """Create sample audit logs for testing."""
    repo = AuditLogRepository(db_session)
    
    logs = [
        AuditLogModel(
            account_id="00000000-0000-0000-0000-000000000001",
            operation="CREATE",
            table_name="users",
            record_id="u1",
            column_name="email",
            old_value=None,
            new_value="test1@example.com",
            user_id="admin1",
            user_email="admin1@example.com",
            user_name="Admin One",
            occurred_at=datetime.now(timezone.utc) - timedelta(hours=2),
        ),
        AuditLogModel(
            account_id="00000000-0000-0000-0000-000000000001",
            operation="UPDATE",
            table_name="users",
            record_id="u1",
            column_name="name",
            old_value="Old Name",
            new_value="New Name",
            user_id="admin1",
            user_email="admin1@example.com",
            user_name="Admin One",
            occurred_at=datetime.now(timezone.utc) - timedelta(hours=1),
        ),
        AuditLogModel(
            account_id="00000000-0000-0000-0000-000000000002",
            operation="DELETE",
            table_name="records",
            record_id="r1",
            column_name="title",
            old_value="Some Title",
            new_value=None,
            user_id="admin2",
            user_email="admin2@example.com",
            user_name="Admin Two",
            occurred_at=datetime.now(timezone.utc),
        ),
    ]
    
    await repo.create_batch(logs)
    await db_session.commit()
    return logs


@pytest.mark.asyncio
async def test_list_audit_logs_success(client, superadmin_token, sample_logs):
    """Test listing audit logs with superadmin access."""
    response = await client.get(
        "/api/v1/audit-logs/",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_list_audit_logs_filters(client, superadmin_token, sample_logs):
    """Test filtering audit logs."""
    # Filter by table_name
    response = await client.get(
        "/api/v1/audit-logs/?table_name=users",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    
    # Filter by operation
    response = await client.get(
        "/api/v1/audit-logs/?operation=DELETE",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["operation"] == "DELETE"


@pytest.mark.asyncio
async def test_get_audit_log_detail(client, superadmin_token, sample_logs):
    """Test getting single audit log detail."""
    log_id = sample_logs[0].id
    response = await client.get(
        f"/api/v1/audit-logs/{log_id}",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == log_id
    assert data["table_name"] == "users"
    assert "checksum" in data
    assert "previous_hash" in data


@pytest.mark.asyncio
async def test_export_audit_logs_csv(client, superadmin_token, sample_logs):
    """Test exporting audit logs to CSV."""
    response = await client.get(
        "/api/v1/audit-logs/export?format=csv",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=audit_logs" in response.headers["content-disposition"]
    
    content = response.text
    lines = content.strip().split("\n")
    assert len(lines) == 4  # Header + 3 rows
    assert "Operation" in lines[0]


@pytest.mark.asyncio
async def test_audit_logs_requires_superadmin(client, regular_user_token, sample_logs):
    """Test that regular users cannot access audit logs."""
    response = await client.get(
        "/api/v1/audit-logs/",
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response.status_code == 403
