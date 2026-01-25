"""Integration test for account deletion cascade."""
import pytest
from sqlalchemy import text
from typing import cast
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from snackbase.domain.services import AccountService, CollectionService
from snackbase.infrastructure.persistence.repositories import RecordRepository, AccountRepository
from snackbase.infrastructure.persistence.table_builder import TableBuilder

@pytest.mark.asyncio
async def test_records_deleted_on_account_deletion(db_session):
    """Test that records are deleted when the account is deleted."""
    engine = cast(AsyncEngine, db_session.bind)
    
    # 1. Services setup
    res = await db_session.execute(text("PRAGMA foreign_keys"))
    val = res.scalar()
    print(f"DEBUG: foreign_keys={val}")
    
    account_service = AccountService(db_session)
    collection_service = CollectionService(db_session, engine)
    record_repo = RecordRepository(db_session)
    account_repo = AccountRepository(db_session)

    # 2. Create an Account
    # We can't use service.create_account directly as it needs a user/context sometimes? 
    # Let's inspect AccountService or just use Repository/Model directly for simplicity.
    # Actually AccountService.create_account takes (name, user_id=None).
    
    # Use repo to create account manually to be sure
    from snackbase.infrastructure.persistence.models import AccountModel
    import uuid
    
    account = AccountModel(
        id=str(uuid.uuid4()),
        name="Cascade Test Account",
        account_code="XX1234",
        slug="cascade-test"
    )
    db_session.add(account)
    await db_session.commit()
    account_id = account.id

    # 3. Create a Collection
    collection_name = "CascadeCollection"
    schema = [{"name": "title", "type": "text"}]
    
    # Ensure collection doesn't exist (cleanup from previous runs if any)
    existing_collection = await collection_service.repository.get_by_name(collection_name)
    if existing_collection:
        # Two-phase deletion
        result = await collection_service.prepare_collection_deletion(existing_collection.id)
        await collection_service.migration_service.apply_migrations()
        await collection_service.finalize_collection_deletion(existing_collection.id)
        await db_session.commit()
    
    # Create collection (this will create table with FK constraint if our fix works)
    collection_model = await collection_service.create_collection(
        collection_name, schema, "superadmin"
    )
    collection_id = collection_model.id
    await db_session.commit()

    # 4. Insert a Record for this Account
    record_id = str(uuid.uuid4())
    record_data = {"title": "Test Record"}
    
    await record_repo.insert_record(
        collection_name=collection_name,
        record_id=record_id,
        account_id=account_id,
        created_by="user1",
        data=record_data,
        schema=schema
    )
    await db_session.commit()

    # Verify record exists
    record = await record_repo.get_by_id(collection_name, record_id, account_id, schema)
    assert record is not None, "Record should exist before account deletion"

    # 5. Delete Account
    await account_repo.delete(account)
    await db_session.commit()

    # 6. Verify Record is Gone
    # We need to bypass get_by_id's standard check? No, get_by_id should return None.
    # But get_by_id might return None if account is passed.
    # Let's verify via raw SQL to be absolutely sure it's gone from the table.
    
    table_name = TableBuilder.generate_table_name(collection_name)
    result = await db_session.execute(
        text(f'SELECT count(*) FROM "{table_name}" WHERE id = :id'),
        {"id": record_id}
    )
    count = result.scalar()
    
    assert count == 0, "Record should be deleted via cascade when account is deleted"

    # Cleanup: Delete collection (two-phase)
    result = await collection_service.prepare_collection_deletion(collection_id)
    await db_session.close()
    await collection_service.migration_service.apply_migrations()
    # Open new session for finalization using the same engine
    from sqlalchemy.orm import sessionmaker
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as new_session:
        new_collection_service = CollectionService(new_session, engine)
        await new_collection_service.finalize_collection_deletion(collection_id)
        await new_session.commit()
