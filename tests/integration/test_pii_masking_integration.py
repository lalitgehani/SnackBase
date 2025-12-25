"""Integration tests for PII data masking."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import (
    AccountModel,
    RoleModel,
    UserModel,
    GroupModel,
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    RoleRepository,
    UserRepository,
    CollectionRepository,
    RecordRepository,
)
from snackbase.infrastructure.auth import jwt_service


@pytest.mark.asyncio
class TestPIIMasking:
    """Integration tests for PII masking in API responses."""

    async def test_pii_masking_for_user_without_pii_access(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that PII fields are masked for users without pii_access group."""
        # 1. Create account
        account_repo = AccountRepository(db_session)
        account = AccountModel(
            id="AC0001",
            slug="testaccount",
            name="Test Account",
        )
        await account_repo.create(account)

        # 2. Create role
        role_repo = RoleRepository(db_session)
        role = RoleModel(name="user", description="Regular user")
        await role_repo.create(role)

        # 3. Create user WITHOUT pii_access group
        user_repo = UserRepository(db_session)
        user = UserModel(
            id="user_test_001",
            account_id=account.id,
            email="test@example.com",
            password_hash="hashed_password",
            role_id=role.id,
            is_active=True,
        )
        await user_repo.create(user)
        await db_session.commit()

        # 4. Create collection with PII fields
        collection_repo = CollectionRepository(db_session)
        collection = await collection_repo.create(
            name="customers",
            schema=[
                {"name": "email", "type": "email", "pii": True, "mask_type": "email"},
                {"name": "ssn", "type": "text", "pii": True, "mask_type": "ssn"},
                {"name": "phone", "type": "text", "pii": True, "mask_type": "phone"},
                {"name": "full_name", "type": "text", "pii": True, "mask_type": "name"},
                {"name": "notes", "type": "text", "pii": True, "mask_type": "full"},
                {"name": "age", "type": "number", "pii": False},
            ],
        )
        await db_session.commit()

        # 5. Create record with PII data
        record_repo = RecordRepository(db_session)
        record_id = "rec_001"
        await record_repo.insert_record(
            collection_name="customers",
            record_id=record_id,
            account_id=account.id,
            created_by=user.id,
            data={
                "email": "john.doe@example.com",
                "ssn": "123-45-6789",
                "phone": "+1-555-123-4567",
                "full_name": "John Doe",
                "notes": "Sensitive information",
                "age": 30,
            },
            schema=collection.schema,
        )
        await db_session.commit()

        # 6. Generate JWT token for user
        token = jwt_service.create_access_token(
            user_id=user.id,
            account_id=account.id,
            email=user.email,
            role="user",
        )

        # 7. Get record via API
        response = await client.get(
            f"/api/v1/records/customers/{record_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # 8. Verify PII fields are masked
        assert data["email"] == "j***@example.com"
        assert data["ssn"] == "***-**-****"
        assert data["phone"] == "+1-***-***-4567"
        assert data["full_name"] == "J*** D***"
        assert data["notes"] == "***********************"  # Same length as original
        assert data["age"] == 30  # Non-PII field should not be masked

    async def test_pii_unmasked_for_user_with_pii_access(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that PII fields are NOT masked for users with pii_access group."""
        # 1. Create account
        account_repo = AccountRepository(db_session)
        account = AccountModel(
            id="AC0002",
            slug="testaccount2",
            name="Test Account 2",
        )
        await account_repo.create(account)

        # 2. Create pii_access group
        from snackbase.infrastructure.persistence.models import GroupModel
        import uuid

        pii_group = GroupModel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            name="pii_access",
            description="Can view PII data",
        )
        db_session.add(pii_group)

        # 3. Get pre-seeded admin role
        from sqlalchemy import select
        result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
        role = result.scalar_one()

        # 4. Create user WITH pii_access group
        user_repo = UserRepository(db_session)
        user = UserModel(
            id="user_test_002",
            account_id=account.id,
            email="admin@example.com",
            password_hash="hashed_password",
            role_id=role.id,
            is_active=True,
        )
        await user_repo.create(user)

        # Add user to pii_access group
        user.groups.append(pii_group)
        await db_session.commit()

        # 5. Create collection with PII fields
        collection_repo = CollectionRepository(db_session)
        collection = await collection_repo.create(
            name="customers2",
            schema=[
                {"name": "email", "type": "email", "pii": True, "mask_type": "email"},
                {"name": "ssn", "type": "text", "pii": True, "mask_type": "ssn"},
                {"name": "phone", "type": "text", "pii": True, "mask_type": "phone"},
                {"name": "full_name", "type": "text", "pii": True, "mask_type": "name"},
            ],
        )
        await db_session.commit()

        # 6. Create record with PII data
        record_repo = RecordRepository(db_session)
        record_id = "rec_002"
        await record_repo.insert_record(
            collection_name="customers2",
            record_id=record_id,
            account_id=account.id,
            created_by=user.id,
            data={
                "email": "jane.smith@example.com",
                "ssn": "987-65-4321",
                "phone": "+1-555-987-6543",
                "full_name": "Jane Smith",
            },
            schema=collection.schema,
        )
        await db_session.commit()

        # 7. Generate JWT token for user
        token = jwt_service.create_access_token(
            user_id=user.id,
            account_id=account.id,
            email=user.email,
            role="admin",
        )

        # 8. Get record via API
        response = await client.get(
            f"/api/v1/records/customers2/{record_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # 9. Verify PII fields are NOT masked
        assert data["email"] == "jane.smith@example.com"
        assert data["ssn"] == "987-65-4321"
        assert data["phone"] == "+1-555-987-6543"
        assert data["full_name"] == "Jane Smith"

    async def test_pii_masking_in_list_endpoint(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that PII masking works in list endpoint."""
        # 1. Create account
        account_repo = AccountRepository(db_session)
        account = AccountModel(
            id="AC0003",
            slug="testaccount3",
            name="Test Account 3",
        )
        await account_repo.create(account)

        # 2. Create role
        role_repo = RoleRepository(db_session)
        role = RoleModel(name="user", description="Regular user")
        await role_repo.create(role)

        # 3. Create user WITHOUT pii_access group
        user_repo = UserRepository(db_session)
        user = UserModel(
            id="user_test_003",
            account_id=account.id,
            email="user3@example.com",
            password_hash="hashed_password",
            role_id=role.id,
            is_active=True,
        )
        await user_repo.create(user)
        await db_session.commit()

        # 4. Create collection with PII fields
        collection_repo = CollectionRepository(db_session)
        collection = await collection_repo.create(
            name="employees",
            schema=[
                {"name": "email", "type": "email", "pii": True, "mask_type": "email"},
                {"name": "name", "type": "text", "pii": True, "mask_type": "name"},
            ],
        )
        await db_session.commit()

        # 5. Create multiple records
        record_repo = RecordRepository(db_session)
        for i in range(3):
            await record_repo.insert_record(
                collection_name="employees",
                record_id=f"emp_{i}",
                account_id=account.id,
                created_by=user.id,
                data={
                    "email": f"employee{i}@example.com",
                    "name": f"Employee {i}",
                },
                schema=collection.schema,
            )
        await db_session.commit()

        # 6. Generate JWT token
        token = jwt_service.create_access_token(
            user_id=user.id,
            account_id=account.id,
            email=user.email,
            role="user",
        )

        # 7. List records via API
        response = await client.get(
            "/api/v1/records/employees",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # 8. Verify all records have masked PII
        assert len(data["items"]) == 3
        for item in data["items"]:
            assert item["email"].startswith("e***@")
            assert item["name"].startswith("E***")

    async def test_database_stores_unmasked_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that database always stores unmasked data."""
        # 1. Create account
        account_repo = AccountRepository(db_session)
        account = AccountModel(
            id="AC0004",
            slug="testaccount4",
            name="Test Account 4",
        )
        await account_repo.create(account)

        # 2. Create role
        role_repo = RoleRepository(db_session)
        role = RoleModel(name="user", description="Regular user")
        await role_repo.create(role)

        # 3. Create user
        user_repo = UserRepository(db_session)
        user = UserModel(
            id="user_test_004",
            account_id=account.id,
            email="user4@example.com",
            password_hash="hashed_password",
            role_id=role.id,
            is_active=True,
        )
        await user_repo.create(user)
        await db_session.commit()

        # 4. Create collection
        collection_repo = CollectionRepository(db_session)
        collection = await collection_repo.create(
            name="contacts",
            schema=[
                {"name": "email", "type": "email", "pii": True, "mask_type": "email"},
            ],
        )
        await db_session.commit()

        # 5. Create record via API
        token = jwt_service.create_access_token(
            user_id=user.id,
            account_id=account.id,
            email=user.email,
            role="user",
        )

        response = await client.post(
            "/api/v1/records/contacts",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "original@example.com"},
        )

        assert response.status_code == 201
        record_id = response.json()["id"]

        # 6. Verify database has unmasked data
        record_repo = RecordRepository(db_session)
        db_record = await record_repo.get_by_id(
            collection_name="contacts",
            record_id=record_id,
            account_id=account.id,
            schema=collection.schema,
        )

        assert db_record["email"] == "original@example.com"  # Unmasked in DB
