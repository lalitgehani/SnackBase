
import json
import pytest
from fastapi import status
from snackbase.infrastructure.persistence.table_builder import TableBuilder
from snackbase.infrastructure.persistence.models import CollectionModel

# Enable audit hooks for all tests in this module
pytestmark = pytest.mark.enable_audit_hooks

@pytest.mark.asyncio
async def test_audit_log_record_creation(client, superadmin_token, db_session):
    """Test that audit logs are generated for dynamic collection record creation."""
    # 1. Create a collection
    collection_name = "audit_test_col"
    schema = [
        {"name": "name", "type": "text"},
        {"name": "age", "type": "number"}
    ]
    
    collection = CollectionModel(
        id="col-audit-test",
        name=collection_name,
        schema=json.dumps(schema)
    )
    db_session.add(collection)
    
    # Create physical table
    engine = db_session.bind
    await TableBuilder.create_table(engine, collection_name, schema)
    await db_session.commit()
    
    # 2. Create a record via API
    response = await client.post(
        f"/api/v1/records/{collection_name}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": "Alice", "age": 30}
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    record_id = response.json()["id"]
    
    # 3. Verify audit logs
    from sqlalchemy import text
    expected_table_name = TableBuilder.generate_table_name(collection_name)
    
    # We need a fresh query to see the committed audit logs
    result = await db_session.execute(
        text("SELECT * FROM audit_log WHERE table_name = :table_name AND record_id = :record_id"),
        {"table_name": expected_table_name, "record_id": record_id}
    )
    logs = result.fetchall()
    
    # Should have logs for all columns (id, account_id, created_at, created_by, updated_at, updated_by, name, age)
    assert len(logs) >= 8
    
    # Check one log entry
    name_log = next((l for l in logs if l._mapping["column_name"] == "name"), None)
    assert name_log is not None
    assert name_log._mapping["operation"] == "CREATE"
    # Note: PII masking might affect the value
    # Alice -> A*** (if PII service is active)
    assert "A" in name_log._mapping["new_value"]

    # Verify extra_metadata contains auth_method
    extra_meta = name_log._mapping["extra_metadata"]
    # SQLite might return it as a string if not automatically cast, but SQLAlchemy usually handles JSON
    if isinstance(extra_meta, str):
        extra_meta = json.loads(extra_meta)
    
    assert extra_meta is not None
    assert "auth_method" in extra_meta
    # Since we use superadmin_token (JWT)
    assert extra_meta["auth_method"] == "jwt"

@pytest.mark.asyncio
async def test_audit_log_record_update(client, superadmin_token, db_session):
    """Test that audit logs are generated for dynamic collection record update."""
    # 1. Setup collection and record
    collection_name = "audit_update_col"
    schema = [{"name": "name", "type": "text"}]
    
    collection = CollectionModel(
        id="col-audit-update",
        name=collection_name,
        schema=json.dumps(schema)
    )
    db_session.add(collection)
    engine = db_session.bind
    await TableBuilder.create_table(engine, collection_name, schema)
    await db_session.commit()
    
    # Create record
    res = await client.post(
        f"/api/v1/records/{collection_name}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": "Bob"}
    )
    record_id = res.json()["id"]
    
    # 2. Update record
    response = await client.put(
        f"/api/v1/records/{collection_name}/{record_id}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": "Robert"}
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 3. Verify audit logs
    from sqlalchemy import text
    expected_table_name = TableBuilder.generate_table_name(collection_name)
    
    result = await db_session.execute(
        text("SELECT * FROM audit_log WHERE table_name = :table_name AND record_id = :record_id AND operation = 'UPDATE'"),
        {"table_name": expected_table_name, "record_id": record_id}
    )
    logs = result.fetchall()
    
    # Should have logs for changed columns (name, updated_at, updated_by)
    # Actually updated_by might not change if it was the same user, but updated_at will.
    assert len(logs) >= 1
    
    name_log = next((l for l in logs if l._mapping["column_name"] == "name"), None)
    assert name_log is not None
    assert "B" in name_log._mapping["old_value"]
    assert "R" in name_log._mapping["new_value"]

    # Verify extra_metadata
    extra_meta = name_log._mapping["extra_metadata"]
    if isinstance(extra_meta, str):
        extra_meta = json.loads(extra_meta)
    assert extra_meta["auth_method"] == "jwt"

@pytest.mark.asyncio
async def test_audit_log_record_deletion(client, superadmin_token, db_session):
    """Test that audit logs are generated for dynamic collection record deletion."""
    # 1. Setup collection and record
    collection_name = "audit_delete_col"
    schema = [{"name": "name", "type": "text"}]
    
    collection = CollectionModel(
        id="col-audit-delete",
        name=collection_name,
        schema=json.dumps(schema)
    )
    db_session.add(collection)
    engine = db_session.bind
    await TableBuilder.create_table(engine, collection_name, schema)
    await db_session.commit()
    
    # Create record
    res = await client.post(
        f"/api/v1/records/{collection_name}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": "Charlie"}
    )
    record_id = res.json()["id"]
    
    # 2. Delete record
    response = await client.delete(
        f"/api/v1/records/{collection_name}/{record_id}",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # 3. Verify audit logs
    from sqlalchemy import text
    expected_table_name = TableBuilder.generate_table_name(collection_name)
    
    result = await db_session.execute(
        text("SELECT * FROM audit_log WHERE table_name = :table_name AND record_id = :record_id AND operation = 'DELETE'"),
        {"table_name": expected_table_name, "record_id": record_id}
    )
    logs = result.fetchall()
    
    # Should have logs for all columns being deleted
    assert len(logs) >= 7
    
    name_log = next((l for l in logs if l._mapping["column_name"] == "name"), None)
    assert name_log is not None
    assert "C" in name_log._mapping["old_value"]
    assert name_log._mapping["new_value"] is None

    # Verify extra_metadata
    extra_meta = name_log._mapping["extra_metadata"]
    if isinstance(extra_meta, str):
        extra_meta = json.loads(extra_meta)
    assert extra_meta["auth_method"] == "jwt"
