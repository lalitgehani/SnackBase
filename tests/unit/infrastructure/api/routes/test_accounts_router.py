"""Unit tests for Accounts Router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.api.dependencies import require_superadmin
from snackbase.infrastructure.auth.token_types import TokenType
from snackbase.infrastructure.persistence.models import AccountModel


@pytest.fixture
def mock_account_service():
    """Mock AccountService."""
    with patch(
        "snackbase.infrastructure.api.routes.accounts_router.AccountService"
    ) as mock:
        mock_instance = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest_asyncio.fixture
async def async_client():
    """Create a custom AsyncClient for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def clear_overrides():
    """Clear dependency overrides after each test."""
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


def create_superadmin_override():
    """Create a superadmin user override."""
    async def admin_override():
        user = AsyncMock()
        user.user_id = "admin"
        user.account_id = "SY0000"
        user.email = "admin@example.com"
        user.role = "admin"
        user.token_type = TokenType.JWT
        user.groups = []
        return user
    return admin_override


@pytest.mark.asyncio
async def test_list_accounts_success(async_client, mock_account_service):
    """GET /accounts returns list."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    now = datetime.now(timezone.utc)
    mock_items = [
        (AccountModel(id="AA0001", account_code="AA0001", name="Acc 1", slug="acc-1", created_at=now), 5),
        (AccountModel(id="BB0002", account_code="BB0002", name="Acc 2", slug="acc-2", created_at=now), 10)
    ]
    mock_account_service.list_accounts = AsyncMock(return_value=(mock_items, 2))

    response = await async_client.get(
        "/api/v1/accounts",
        headers={"Authorization": "Bearer dummy"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["user_count"] == 5


@pytest.mark.asyncio
async def test_list_accounts_with_search(async_client, mock_account_service):
    """Search filtering works."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    mock_account_service.list_accounts = AsyncMock(return_value=([], 0))

    await async_client.get(
        "/api/v1/accounts?search=query",
        headers={"Authorization": "Bearer dummy"}
    )
    
    mock_account_service.list_accounts.assert_called_with(
        page=1, page_size=25, sort_by="created_at", sort_order="desc", search="query"
    )


@pytest.mark.asyncio
async def test_list_accounts_with_sort(async_client, mock_account_service):
    """Sorting works."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    mock_account_service.list_accounts = AsyncMock(return_value=([], 0))

    await async_client.get(
        "/api/v1/accounts?sort_by=name&sort_order=asc",
        headers={"Authorization": "Bearer dummy"}
    )
    
    mock_account_service.list_accounts.assert_called_with(
        page=1, page_size=25, sort_by="name", sort_order="asc", search=None
    )


@pytest.mark.asyncio
async def test_get_account_success(async_client, mock_account_service):
    """GET /accounts/{id} returns details."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    now = datetime.now(timezone.utc)
    account = AccountModel(
        id="AA0001", account_code="AA0001", name="Test", slug="test", created_at=now, updated_at=now
    )
    mock_account_service.get_account_with_details = AsyncMock(return_value=(account, 3))

    response = await async_client.get(
        "/api/v1/accounts/AA0001",
        headers={"Authorization": "Bearer dummy"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == "AA0001"
    assert data["user_count"] == 3


@pytest.mark.asyncio
async def test_get_account_not_found(async_client, mock_account_service):
    """404 for missing account."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    mock_account_service.get_account_with_details = AsyncMock(
        side_effect=ValueError("Account not found")
    )

    response = await async_client.get(
        "/api/v1/accounts/NONEXISTENT",
        headers={"Authorization": "Bearer dummy"}
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_account_success(async_client, mock_account_service):
    """POST /accounts creates account."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    now = datetime.now(timezone.utc)
    created = AccountModel(id="NEW001", account_code="NE0001", name="New", slug="new", created_at=now, updated_at=now)
    mock_account_service.create_account = AsyncMock(return_value=created)

    payload = {"name": "New", "slug": "new"}
    response = await async_client.post(
        "/api/v1/accounts",
        json=payload,
        headers={"Authorization": "Bearer dummy"}
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == "NEW001"
    
    mock_account_service.create_account.assert_called_with(name="New", slug="new")


@pytest.mark.asyncio
async def test_create_account_validation_error(async_client, mock_account_service):
    """Validation errors."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    # Service error:
    mock_account_service.create_account = AsyncMock(
        side_effect=ValueError("Invalid slug")
    )
    
    response = await async_client.post(
        "/api/v1/accounts",
        json={"name": "A", "slug": "good-slug"},
        headers={"Authorization": "Bearer dummy"}
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "Invalid slug"


@pytest.mark.asyncio
async def test_update_account_success(async_client, mock_account_service):
    """PUT /accounts/{id} updates."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    now = datetime.now(timezone.utc)
    updated = AccountModel(id="AA0001", account_code="AA0001", name="Updated", slug="slug", created_at=now, updated_at=now)
    
    mock_account_service.update_account = AsyncMock(return_value=updated)
    mock_account_service.get_account_with_details = AsyncMock(return_value=(updated, 5))

    response = await async_client.put(
        "/api/v1/accounts/AA0001",
        json={"name": "Updated"},
        headers={"Authorization": "Bearer dummy"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_account_success(async_client, mock_account_service):
    """DELETE /accounts/{id} deletes."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    mock_account_service.delete_account = AsyncMock(return_value=None)

    response = await async_client.delete(
        "/api/v1/accounts/AA0001",
        headers={"Authorization": "Bearer dummy"}
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_account_service.delete_account.assert_called_with("AA0001")


@pytest.mark.asyncio
async def test_delete_system_account_prevented(async_client, mock_account_service):
    """Cannot delete SY0000."""
    app.dependency_overrides[require_superadmin] = create_superadmin_override()
    
    mock_account_service.delete_account = AsyncMock(
        side_effect=ValueError("Cannot delete system account")
    )

    response = await async_client.delete(
        "/api/v1/accounts/SY0000",
        headers={"Authorization": "Bearer dummy"}
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "system account" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_requires_superadmin(async_client, mock_account_service):
    """All endpoints require superadmin."""
    from fastapi import HTTPException
    
    async def mock_forbidden():
        raise HTTPException(status_code=403, detail="Forbidden")
        
    app.dependency_overrides[require_superadmin] = mock_forbidden

    response = await async_client.get(
        "/api/v1/accounts",
        headers={"Authorization": "Bearer dummy"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = await async_client.delete(
        "/api/v1/accounts/AA0001",
        headers={"Authorization": "Bearer dummy"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
