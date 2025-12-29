"""Integration tests for PII data masking."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import (
    RoleModel,
    UserModel,
    GroupModel,
    AccountModel,
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    UserRepository,
)
from snackbase.infrastructure.auth import jwt_service
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID


@pytest.mark.asyncio
class TestPIIMasking:
    """Integration tests for PII masking in API responses."""

    @pytest.fixture
    def superadmin_headers(self):
        """Create headers for a superadmin user."""
        token = jwt_service.create_access_token(
            user_id="superadmin-id",
            account_id=SYSTEM_ACCOUNT_ID,
            email="admin@system.com",
            role="admin",
        )
        return {"Authorization": f"Bearer {token}"}

    async def test_pii_masking_for_user_without_pii_access(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        superadmin_headers,
    ):
        """Test that PII fields are masked for users without pii_access group."""
        # 1. Create collection with PII fields via API
        collection_data = {
            "name": "customers",
            "schema": [
                {"name": "email", "type": "email", "required":True, "pii": True, "mask_type": "email"},
                {"name": "ssn", "type": "text", "pii": True, "mask_type": "ssn"},
                {"name": "phone", "type": "text", "pii": True, "mask_type": "phone"},
                {"name": "full_name", "type": "text", "pii": True, "mask_type": "name"},
                {"name": "notes", "type": "text", "pii": True, "mask_type": "full"},
                {"name": "age", "type": "number", "pii": False},
            ],
        }
        response = await client.post("/api/v1/collections", json=collection_data, headers=superadmin_headers)
        assert response.status_code == 201

        # 2. Setup user without pii_access
        # Get user role
        from sqlalchemy import select
        result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
        role = result.scalar_one()

        # Create user
        user_repo = UserRepository(db_session)
        
        # Create account for user
        # Format must be AC + 4 digits? Or just valid string?
        # Previous error: CHECK constraint failed: ck_accounts_id_format
        # Let's use AC0010 to be safe
        account = AccountModel(id="AC0010", account_code="AC0010", name="Test Account", slug="test-acc-1")
        db_session.add(account)
        await db_session.flush()
        
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

        # 3. Create permissions
        permission_data = {
            "role_id": role.id,
            "collection": "customers",
            "rules": {
                "create": {"rule": "true", "fields": "*"},
                "read": {"rule": "true", "fields": "*"}, 
            },
        }
        await client.post("/api/v1/permissions", json=permission_data, headers=superadmin_headers)

        # 4. Create record as User
        token = jwt_service.create_access_token(
            user_id=user.id,
            account_id=account.id,
            email=user.email,
            role="user",
        )
        user_headers = {"Authorization": f"Bearer {token}"}

        record_data = {
            "email": "john.doe@example.com",
            "ssn": "123-45-6789",
            "phone": "+1-555-123-4567",
            "full_name": "John Doe",
            "notes": "Sensitive information",
            "age": 30,
        }
        
        create_response = await client.post("/api/v1/records/customers", json=record_data, headers=user_headers)
        assert create_response.status_code == 201
        record_id = create_response.json()["id"]

        # 5. Get record
        response = await client.get(f"/api/v1/records/customers/{record_id}", headers=user_headers)
        assert response.status_code == 200
        data = response.json()

        # 6. Verify masking
        assert data["email"] == "j***@example.com"
        assert data["ssn"] == "***-**-****"
        assert data["notes"] == "*********************"  # full mask

    async def test_pii_unmasked_for_user_with_pii_access(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        superadmin_headers,
    ):
        """Test that PII fields are NOT masked for users with pii_access group."""
        # 1. Create collection with PII fields via API
        collection_data = {
            "name": "customers2",
            "schema": [
                {"name": "email", "type": "email", "pii": True, "mask_type": "email"},
            ],
        }
        await client.post("/api/v1/collections", json=collection_data, headers=superadmin_headers)

        # 2. Create user/account
        from sqlalchemy import select
        result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
        role = result.scalar_one()

        account = AccountModel(id="AC0011", account_code="AC0011", name="Test Account 2", slug="test-acc-2")
        db_session.add(account)
        await db_session.flush()

        # Create pii_access group
        import uuid
        pii_group = GroupModel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            name="pii_access",
            description="Can view PII data",
        )
        db_session.add(pii_group)

        user = UserModel(
            id="user_test_002",
            account_id=account.id,
            email="pii@example.com",
            password_hash="hashed",
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        # Add to group
        user.groups.append(pii_group)
        await db_session.commit()

        # 3. Permissions
        permission_data = {
            "role_id": role.id,
            "collection": "customers2",
            "rules": {
                "create": {"rule": "true", "fields": "*"},
                "read": {"rule": "true", "fields": "*"},
            },
        }
        await client.post("/api/v1/permissions", json=permission_data, headers=superadmin_headers)

        # 4. Create record
        token = jwt_service.create_access_token(
            user_id=user.id,
            account_id=account.id,
            email=user.email,
            role="user",
        )
        user_headers = {"Authorization": f"Bearer {token}"}

        record_data = {"email": "john.doe@example.com"}
        create_res = await client.post("/api/v1/records/customers2", json=record_data, headers=user_headers)
        assert create_res.status_code == 201
        record_id = create_res.json()["id"]

        # 5. Get record
        response = await client.get(f"/api/v1/records/customers2/{record_id}", headers=user_headers)
        assert response.status_code == 200
        data = response.json()

        # 6. Verify UNMASKED
        assert data["email"] == "john.doe@example.com"

    async def test_pii_masking_in_list_endpoint(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        superadmin_headers,
    ):
         """Test that PII masking works in list endpoint."""
         # 1. Create collection
         collection_data = {
            "name": "employees_list",
            "schema": [
                {"name": "email", "type": "email", "pii": True, "mask_type": "email"},
            ],
         }
         await client.post("/api/v1/collections", json=collection_data, headers=superadmin_headers)

         # 2. User/Account
         from sqlalchemy import select
         result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
         role = result.scalar_one()

         account = AccountModel(id="AC0012", account_code="AC0012", name="Test Account 3", slug="test-acc-3")
         db_session.add(account)
         await db_session.flush()

         user = UserModel(
            id="user_test_003",
            account_id=account.id,
            email="user3@example.com",
            password_hash="pwd",
            role_id=role.id,
            is_active=True,
         )
         db_session.add(user)
         await db_session.commit()

         # 3. Permissions
         await client.post("/api/v1/permissions", json={
             "role_id": role.id,
             "collection": "employees_list",
             "rules": {"create": {"rule":"true", "fields":"*"}, "read": {"rule":"true", "fields":"*"}}
         }, headers=superadmin_headers)

         # 4. Create records
         token = jwt_service.create_access_token(user_id=user.id, account_id=account.id, email=user.email, role="user")
         headers = {"Authorization": f"Bearer {token}"}

         for i in range(3):
             await client.post("/api/v1/records/employees_list", json={"email": f"emp{i}@example.com"}, headers=headers)

         # 5. List
         response = await client.get("/api/v1/records/employees_list", headers=headers)
         assert response.status_code == 200
         data = response.json()
         
         assert len(data["items"]) == 3
         for item in data["items"]:
             assert "***" in item["email"]

    async def test_database_stores_unmasked_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        superadmin_headers,
    ):
         """Test database stores unmasked data."""
         # 1. Collection
         await client.post("/api/v1/collections", json={
             "name": "contacts_db",
             "schema": [{"name": "email", "type": "email", "pii": True, "mask_type": "email"}]
         }, headers=superadmin_headers)

         # 2. User/Account
         from sqlalchemy import select
         result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
         role = result.scalar_one()

         account = AccountModel(id="AC0013", account_code="AC0013", name="Acc4", slug="acc-4")
         db_session.add(account)
         await db_session.flush()

         user = UserModel(id="u4", account_id=account.id, email="u4@e.com", password_hash="p", role_id=role.id, is_active=True)
         db_session.add(user)
         await db_session.commit()

         # 3. Permissions
         await client.post("/api/v1/permissions", json={
             "role_id": role.id,
             "collection": "contacts_db",
             "rules": {"create": {"rule":"true", "fields":"*"}, "read": {"rule":"true", "fields":"*"}}
         }, headers=superadmin_headers)

         # 4. Create record
         token = jwt_service.create_access_token(user_id=user.id, account_id=account.id, email=user.email, role="user")
         headers = {"Authorization": f"Bearer {token}"}
         
         res = await client.post("/api/v1/records/contacts_db", json={"email": "raw@example.com"}, headers=headers)
         assert res.status_code == 201
         rec_id = res.json()["id"]

         # 5. Check DB directly
         from snackbase.infrastructure.persistence.repositories import RecordRepository
         from snackbase.infrastructure.persistence.repositories import CollectionRepository
         
         coll_repo = CollectionRepository(db_session)
         coll = await coll_repo.get_by_name("contacts_db")
         
         import json
         schema = json.loads(coll.schema)
         
         rec_repo = RecordRepository(db_session)
         
         db_record = await rec_repo.get_by_id("contacts_db", rec_id, account.id, schema)
         assert db_record["email"] == "raw@example.com"
