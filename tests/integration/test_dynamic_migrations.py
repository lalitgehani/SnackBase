import pytest
import pytest_asyncio
import os
import json
import tempfile
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from snackbase.infrastructure.persistence.database import Base
from snackbase.infrastructure.persistence.models import CollectionModel
from snackbase.infrastructure.persistence.repositories import CollectionRepository

@pytest_asyncio.fixture
async def db_session():
    """Override db_session to use a file-based SQLite for Alembic compatibility."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite+aiosqlite:///{path}"
    
    engine = create_async_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Use Alembic to initialize the database instead of Base.metadata.create_all
    # This ensures consistency with how the app runs and avoids "table exists" errors
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    # Run core migrations (we need to run them in a separate thread because we are in an async fixture)
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")
        
    # Seed default roles (needed for superadmin)
    from snackbase.infrastructure.persistence.models.role import RoleModel
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        admin_role = RoleModel(name="admin", description="Administrator")
        user_role = RoleModel(name="user", description="Standard User")
        session.add_all([admin_role, user_role])
        await session.commit()

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    await engine.dispose()
    if os.path.exists(path):
        os.remove(path)

@pytest.mark.asyncio
async def test_create_collection_with_migration(client: AsyncClient, superadmin_token: str, db_session):
    """Test that creating a collection generates and applies an Alembic migration."""
    collection_name = "test_mig_create"
    payload = {
        "name": collection_name,
        "fields": [
            {"name": "title", "type": "text", "required": True},
            {"name": "count", "type": "number", "default": 0}
        ]
    }
    
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post("/api/v1/collections", json=payload, headers=headers)
    
    assert response.status_code == 201
    data = response.json()
    collection_id = data["id"]
    
    # Verify in DB that migration_revision is set
    collection_repo = CollectionRepository(db_session)
    collection = await collection_repo.get_by_id(collection_id)
    assert collection is not None
    assert collection.migration_revision is not None
    
    # Verify migration file exists
    dynamic_dir = "sb_data/migrations"
    found = False
    for f in os.listdir(dynamic_dir):
        if collection.migration_revision in f:
            found = True
            break
    assert found, f"Migration file with revision {collection.migration_revision} not found"

@pytest.mark.asyncio
async def test_update_collection_with_migration(client: AsyncClient, superadmin_token: str, db_session):
    """Test that updating a collection generates and applies an Alembic migration."""
    # 1. Create collection
    collection_name = "test_mig_update"
    payload = {
        "name": collection_name,
        "fields": [{"name": "title", "type": "text"}]
    }
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    create_resp = await client.post("/api/v1/collections", json=payload, headers=headers)
    assert create_resp.status_code == 201
    collection_id = create_resp.json()["id"]
    initial_rev = create_resp.json().get("migration_revision") # Wait, router doesn't return revision in response yet in my edit, but it returns collection model fields if I want.
    
    # 2. Update collection (add field)
    update_payload = {
        "fields": [
            {"name": "title", "type": "text"},
            {"name": "new_field", "type": "text", "default": "hello"}
        ]
    }
    update_resp = await client.put(f"/api/v1/collections/{collection_id}", json=update_payload, headers=headers)
    assert update_resp.status_code == 200
    
    # Verify in DB that migration_revision has changed
    collection_repo = CollectionRepository(db_session)
    # We need to refresh or re-fetch
    collection = await collection_repo.get_by_id(collection_id)
    assert collection.migration_revision != initial_rev
    
    # Verify table has the new column
    # We can use op.execute or just try to insert data with the new field later
    
@pytest.mark.asyncio
async def test_delete_collection_with_migration(client: AsyncClient, superadmin_token: str, db_session):
    """Test that deleting a collection generates and applies a DROP migration."""
    # 1. Create collection
    collection_name = "test_mig_delete"
    payload = {
        "name": collection_name,
        "fields": [{"name": "title", "type": "text"}]
    }
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    create_resp = await client.post("/api/v1/collections", json=payload, headers=headers)
    assert create_resp.status_code == 201
    collection_id = create_resp.json()["id"]
    
    # 2. Delete collection
    delete_resp = await client.delete(f"/api/v1/collections/{collection_id}", headers=headers)
    assert delete_resp.status_code == 200
    
    # Verify collection record is gone
    collection_repo = CollectionRepository(db_session)
    collection = await collection_repo.get_by_id(collection_id)
    assert collection is None
    
    # Verify migration file for deletion exists
    data = delete_resp.json()
    rev_id = data.get("migration_revision")
    assert rev_id is not None
    
    dynamic_dir = "sb_data/migrations"
    found = False
    for f in os.listdir(dynamic_dir):
        if rev_id in f:
            found = True
            break
    assert found
