"""Integration tests for collection management API endpoints."""
import json

import pytest
from fastapi import status

from snackbase.infrastructure.persistence.models import CollectionModel


@pytest.mark.asyncio
async def test_list_collections_empty(client, superadmin_token):
    """Test listing collections when none exist."""
    response = await client.get(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1
    assert data["total_pages"] == 0  # 0 pages when no items


@pytest.mark.asyncio
async def test_list_collections_with_data(client, superadmin_token, db_session):
    """Test listing collections with pagination."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder
    
    # Create test collections
    collections = []
    for i in range(3):
        schema = [{"name": "field1", "type": "text"}]
        collection = CollectionModel(
            id=f"col-{i}",
            name=f"Collection{i}",
            schema=json.dumps(schema),
        )
        db_session.add(collection)
        collections.append(collection)
        
        # Create physical tables
        engine = db_session.bind
        await TableBuilder.create_table(engine, f"Collection{i}", schema)
    
    await db_session.commit()
    
    # Test listing
    response = await client.get(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_collections_pagination(client, superadmin_token, db_session):
    """Test collection listing with pagination."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder
    
    # Create 5 test collections
    for i in range(5):
        schema = [{"name": "field1", "type": "text"}]
        collection = CollectionModel(
            id=f"col-{i}",
            name=f"Collection{i}",
            schema=json.dumps(schema),
        )
        db_session.add(collection)
        
        engine = db_session.bind
        await TableBuilder.create_table(engine, f"Collection{i}", schema)
    
    await db_session.commit()
    
    # Get first page (2 items)
    response = await client.get(
        "/api/v1/collections?page=1&page_size=2",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["total_pages"] == 3


@pytest.mark.asyncio
async def test_list_collections_search(client, superadmin_token, db_session):
    """Test collection listing with search."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder
    
    # Create test collections
    names = ["Users", "Products", "Orders"]
    for name in names:
        schema = [{"name": "field1", "type": "text"}]
        collection = CollectionModel(
            id=f"col-{name}",
            name=name,
            schema=json.dumps(schema),
        )
        db_session.add(collection)
        
        engine = db_session.bind
        await TableBuilder.create_table(engine, name, schema)
    
    await db_session.commit()
    
    # Search for "User"
    response = await client.get(
        "/api/v1/collections?search=User",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Users"


@pytest.mark.asyncio
async def test_get_collection_by_id(client, superadmin_token, db_session):
    """Test getting a collection by ID."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder
    
    # Create a test collection
    schema = [
        {"name": "title", "type": "text", "required": True},
        {"name": "count", "type": "number", "default": 0},
    ]
    collection = CollectionModel(
        id="col-123",
        name="TestCollection",
        schema=json.dumps(schema),
    )
    db_session.add(collection)
    
    engine = db_session.bind
    await TableBuilder.create_table(engine, "TestCollection", schema)
    await db_session.commit()
    
    # Get collection
    response = await client.get(
        "/api/v1/collections/col-123",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == "col-123"
    assert data["name"] == "TestCollection"
    assert data["table_name"] == "col_testcollection"
    assert len(data["schema"]) == 2


@pytest.mark.asyncio
async def test_get_collection_not_found(client, superadmin_token):
    """Test getting a non-existent collection."""
    response = await client.get(
        "/api/v1/collections/col-999",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_collection_add_fields(client, superadmin_token, db_session):
    """Test updating a collection by adding new fields."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder
    
    # Create initial collection
    initial_schema = [{"name": "title", "type": "text"}]
    collection = CollectionModel(
        id="col-123",
        name="TestCollection",
        schema=json.dumps(initial_schema),
    )
    db_session.add(collection)
    
    engine = db_session.bind
    await TableBuilder.create_table(engine, "TestCollection", initial_schema)
    await db_session.commit()
    
    # Update with new field
    updated_schema = [
        {"name": "title", "type": "text"},
        {"name": "description", "type": "text"},
    ]
    
    response = await client.put(
        "/api/v1/collections/col-123",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"schema": updated_schema},
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["schema"]) == 2
    assert data["schema"][1]["name"] == "description"


@pytest.mark.asyncio
async def test_update_collection_type_change_rejected(
    client, superadmin_token, db_session
):
    """Test that type changes are rejected."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder
    
    # Create initial collection
    initial_schema = [{"name": "title", "type": "text"}]
    collection = CollectionModel(
        id="col-123",
        name="TestCollection",
        schema=json.dumps(initial_schema),
    )
    db_session.add(collection)
    
    engine = db_session.bind
    await TableBuilder.create_table(engine, "TestCollection", initial_schema)
    await db_session.commit()
    
    # Try to change field type
    invalid_schema = [{"name": "title", "type": "number"}]
    
    response = await client.put(
        "/api/v1/collections/col-123",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"schema": invalid_schema},
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "type change" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_update_collection_field_deletion_rejected(
    client, superadmin_token, db_session
):
    """Test that field deletion is rejected."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder
    
    # Create initial collection with 2 fields
    initial_schema = [
        {"name": "title", "type": "text"},
        {"name": "count", "type": "number"},
    ]
    collection = CollectionModel(
        id="col-123",
        name="TestCollection",
        schema=json.dumps(initial_schema),
    )
    db_session.add(collection)
    
    engine = db_session.bind
    await TableBuilder.create_table(engine, "TestCollection", initial_schema)
    await db_session.commit()
    
    # Try to delete a field
    invalid_schema = [{"name": "title", "type": "text"}]
    
    response = await client.put(
        "/api/v1/collections/col-123",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"schema": invalid_schema},
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "deletion" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_delete_collection(client, superadmin_token, db_session):
    """Test deleting a collection."""
    from snackbase.infrastructure.persistence.table_builder import TableBuilder
    
    # Create a test collection
    schema = [{"name": "field1", "type": "text"}]
    collection = CollectionModel(
        id="col-123",
        name="TestCollection",
        schema=json.dumps(schema),
    )
    db_session.add(collection)
    
    engine = db_session.bind
    await TableBuilder.create_table(engine, "TestCollection", schema)
    await db_session.commit()
    
    # Delete collection
    response = await client.delete(
        "/api/v1/collections/col-123",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["collection_id"] == "col-123"
    assert data["collection_name"] == "TestCollection"
    assert "records_deleted" in data
    
    # Verify collection is deleted
    from snackbase.infrastructure.persistence.repositories import CollectionRepository
    
    repo = CollectionRepository(db_session)
    deleted_collection = await repo.get_by_id("col-123")
    assert deleted_collection is None


@pytest.mark.asyncio
async def test_delete_collection_not_found(client, superadmin_token):
    """Test deleting a non-existent collection."""
    response = await client.delete(
        "/api/v1/collections/col-999",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_collections_require_superadmin(client, regular_user_token):
    """Test that collection endpoints require superadmin access."""
    # List collections
    response = await client.get(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Get collection
    response = await client.get(
        "/api/v1/collections/col-123",
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Update collection
    response = await client.put(
        "/api/v1/collections/col-123",
        headers={"Authorization": f"Bearer {regular_user_token}"},
        json={"schema": []},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Delete collection
    response = await client.delete(
        "/api/v1/collections/col-123",
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
