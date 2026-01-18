import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import AccountModel, UserModel, RoleModel
from tests.security.conftest import AttackClient

@pytest_asyncio.fixture
async def isolation_test_data(db_session: AsyncSession):
    """Setup data for isolation testing: Two accounts with records and users."""
    # 1. Create Account A and User A
    account_a = AccountModel(
        id="AC0001",
        account_code="AC0001",
        name="Account A",
        slug="account-a"
    )
    db_session.add(account_a)
    
    # 2. Create Account B and User B
    account_b = AccountModel(
        id="AC0002",
        account_code="AC0002",
        name="Account B",
        slug="account-b"
    )
    db_session.add(account_b)
    
    # Get roles
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    user_role = result.scalar_one()
    # result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    # admin_role = result.scalar_one()

    # User A
    user_a = UserModel(
        id="user-a",
        email="user-a@example.com",
        account_id=account_a.id,
        password_hash="hashed",
        role_id=user_role.id,
        is_active=True
    )
    db_session.add(user_a)
    
    # User B
    user_b = UserModel(
        id="user-b",
        email="user-b@example.com",
        account_id=account_b.id,
        password_hash="hashed",
        role_id=user_role.id,
        is_active=True
    )
    db_session.add(user_b)
    
    await db_session.commit()
    
    # Tokens
    token_a = jwt_service.create_access_token(
        user_id=user_a.id,
        account_id=user_a.account_id,
        email=user_a.email,
        role="user"
    )
    
    token_b = jwt_service.create_access_token(
        user_id=user_b.id,
        account_id=user_b.account_id,
        email=user_b.email,
        role="user"
    )
    
    return {
        "account_a": account_a,
        "account_b": account_b,
        "user_a_token": token_a,
        "user_b_token": token_b
    }

@pytest_asyncio.fixture
async def isolation_collection(client: AsyncClient, superadmin_token, isolation_test_data):
    """Create a collection for isolation testing."""
    collection_name = f"secrets_{uuid.uuid4().hex[:8]}"
    
    collection_data = {
        "name": collection_name,
        "schema": [
            {"name": "title", "type": "text", "required": True},
            {"name": "secret_data", "type": "text", "required": True},
        ],
        # Add default rules for isolation testing
        "list_rule": "true",
        "view_rule": "true",
        "create_rule": "true",
        "update_rule": "true",
        "delete_rule": "true",
    }
    
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post("/api/v1/collections", json=collection_data, headers=headers)
    assert response.status_code == 201
    
    return collection_name
