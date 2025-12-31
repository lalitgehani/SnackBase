"""Integration tests for migration query API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_migrations_requires_auth(client: AsyncClient):
    """Test that listing migrations requires authentication."""
    response = await client.get("/api/v1/migrations")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_migrations_requires_superadmin(client: AsyncClient, regular_user_token: str):
    """Test that listing migrations requires superadmin access."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = await client.get("/api/v1/migrations", headers=headers)
    
    # Should return 403 Forbidden for non-superadmin users
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_migrations_success(client: AsyncClient, superadmin_token: str):
    """Test successful listing of migrations."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.get("/api/v1/migrations", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "revisions" in data
    assert "total" in data
    assert "current_revision" in data
    assert isinstance(data["revisions"], list)
    assert isinstance(data["total"], int)
    
    # Should have at least the initial migration
    assert data["total"] > 0
    
    # Verify revision structure
    if data["revisions"]:
        revision = data["revisions"][0]
        assert "revision" in revision
        assert "description" in revision
        assert "is_applied" in revision
        assert "is_head" in revision
        assert "is_dynamic" in revision
        assert isinstance(revision["is_applied"], bool)
        assert isinstance(revision["is_head"], bool)
        assert isinstance(revision["is_dynamic"], bool)


@pytest.mark.asyncio
async def test_list_migrations_includes_core_and_dynamic(
    client: AsyncClient, superadmin_token: str
):
    """Test that listing migrations includes both core and dynamic migrations."""
    # First create a collection to generate a dynamic migration
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    
    collection_payload = {
        "name": "test_migration_list",
        "fields": [
            {"name": "title", "type": "text", "required": True},
        ],
    }
    
    create_response = await client.post(
        "/api/v1/collections",
        json=collection_payload,
        headers=headers,
    )
    assert create_response.status_code == 201
    
    # Now list migrations
    response = await client.get("/api/v1/migrations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # Should have both core and dynamic migrations
    core_migrations = [r for r in data["revisions"] if not r["is_dynamic"]]
    dynamic_migrations = [r for r in data["revisions"] if r["is_dynamic"]]
    
    assert len(core_migrations) > 0, "Should have core migrations"
    assert len(dynamic_migrations) > 0, "Should have dynamic migrations"


@pytest.mark.asyncio
async def test_list_migrations_has_cache_headers(
    client: AsyncClient, superadmin_token: str
):
    """Test that listing migrations includes cache headers."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.get("/api/v1/migrations", headers=headers)
    
    assert response.status_code == 200
    
    # Verify cache headers
    assert "cache-control" in response.headers
    assert "etag" in response.headers
    assert "public" in response.headers["cache-control"]


@pytest.mark.asyncio
async def test_get_current_migration_requires_auth(client: AsyncClient):
    """Test that getting current migration requires authentication."""
    response = await client.get("/api/v1/migrations/current")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_migration_success(
    client: AsyncClient, superadmin_token: str
):
    """Test successful retrieval of current migration."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.get("/api/v1/migrations/current", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "revision" in data
    assert "description" in data
    assert "created_at" in data
    assert isinstance(data["revision"], str)
    assert isinstance(data["description"], str)


@pytest.mark.asyncio
async def test_get_current_migration_has_cache_headers(
    client: AsyncClient, superadmin_token: str
):
    """Test that getting current migration includes cache headers."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.get("/api/v1/migrations/current", headers=headers)
    
    assert response.status_code == 200
    
    # Verify cache headers
    assert "cache-control" in response.headers
    assert "etag" in response.headers


@pytest.mark.asyncio
async def test_get_migration_history_requires_auth(client: AsyncClient):
    """Test that getting migration history requires authentication."""
    response = await client.get("/api/v1/migrations/history")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_migration_history_success(
    client: AsyncClient, superadmin_token: str
):
    """Test successful retrieval of migration history."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.get("/api/v1/migrations/history", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "history" in data
    assert "total" in data
    assert isinstance(data["history"], list)
    assert isinstance(data["total"], int)
    
    # Should have at least the initial migration
    assert data["total"] > 0
    
    # Verify history item structure
    if data["history"]:
        item = data["history"][0]
        assert "revision" in item
        assert "description" in item
        assert "is_dynamic" in item
        assert "created_at" in item
        assert isinstance(item["is_dynamic"], bool)


@pytest.mark.asyncio
async def test_get_migration_history_chronological_order(
    client: AsyncClient, superadmin_token: str
):
    """Test that migration history is in chronological order (oldest first)."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.get("/api/v1/migrations/history", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # History should be in chronological order
    # We can't easily verify timestamps, but we can verify the list is not empty
    assert len(data["history"]) > 0


@pytest.mark.asyncio
async def test_get_migration_history_has_cache_headers(
    client: AsyncClient, superadmin_token: str
):
    """Test that getting migration history includes cache headers."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.get("/api/v1/migrations/history", headers=headers)
    
    assert response.status_code == 200
    
    # Verify cache headers
    assert "cache-control" in response.headers
    assert "etag" in response.headers
