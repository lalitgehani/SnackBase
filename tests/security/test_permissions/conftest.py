import pytest
import pytest_asyncio
import uuid
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from snackbase.infrastructure.persistence.models import RoleModel, PermissionModel, UserModel
from snackbase.infrastructure.auth.jwt_service import jwt_service

@pytest.fixture
def rbac_collection_name():
    """Unique collection name for RBAC tests."""
    # Must be alphanumeric + underscores, 3-64 chars
    return f"rbac_test_{uuid.uuid4().hex[:8]}"

@pytest_asyncio.fixture
async def setup_rbac_collection(
    attack_client, 
    superadmin_token, 
    rbac_collection_name
):
    """Create the test collection via API to ensure dynamic tables are created."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    
    # Define collection schema
    schema = [
        {"name": "title", "type": "text", "required": True},
        {"name": "content", "type": "text", "required": False}
    ]
    
    response = await attack_client.post(
        "/api/v1/collections",
        json={
            "name": rbac_collection_name,
            "fields": schema
        },
        headers=headers,
        description=f"Setup: Create RBAC test collection {rbac_collection_name}"
    )
    
    assert response.status_code == 201
    
    # Also create a dummy random collection for wildcard test if needed, 
    # but the test typically tries to access a non-existent one or one we create here.
    # The wildcard test logic used "all_mighty_collection" which definitely doesn't exist.
    # We should probably create that one too if we expect it to work!
    # Or change the test to use another created collection.
    
    return response.json()

@pytest_asyncio.fixture
async def rbac_roles(db_session: AsyncSession, rbac_collection_name):
    """Create test roles with specific permission sets."""
    
    def r_name(prefix):
        return f"{prefix}_{uuid.uuid4().hex[:6]}"

    # Create Roles
    no_access_role = RoleModel(name=r_name("no_access"))
    read_only_role = RoleModel(name=r_name("read_only"))
    full_access_role = RoleModel(name=r_name("full_access"))
    wildcard_role = RoleModel(name=r_name("wildcard"))
    
    db_session.add_all([no_access_role, read_only_role, full_access_role, wildcard_role])
    await db_session.flush()
    
    # Define rules
    allow_rule = '{"rule": "true", "fields": "*"}'
    
    # Add permissions
    # Read Only
    perm_read = PermissionModel(
        role_id=read_only_role.id,
        collection=rbac_collection_name,
        rules='{"read": ' + allow_rule + '}'
    )
    db_session.add(perm_read)
    
    # Full Access
    perm_full = PermissionModel(
        role_id=full_access_role.id,
        collection=rbac_collection_name,
        rules='{"create": ' + allow_rule + ', "read": ' + allow_rule + 
              ', "update": ' + allow_rule + ', "delete": ' + allow_rule + '}'
    )
    db_session.add(perm_full)
    
    # Wildcard: permissions on ANY collection ("*")
    perm_wildcard = PermissionModel(
        role_id=wildcard_role.id,
        collection="*",
        rules='{"create": ' + allow_rule + ', "read": ' + allow_rule + 
              ', "update": ' + allow_rule + ', "delete": ' + allow_rule + '}'
    )
    db_session.add(perm_wildcard)
    
    await db_session.commit()
    
    return {
        "no_access": no_access_role,
        "read_only": read_only_role,
        "full_access": full_access_role,
        "wildcard": wildcard_role
    }

@pytest_asyncio.fixture
async def rbac_users_tokens(
    db_session: AsyncSession, 
    rbac_roles, 
    security_test_data,
    setup_rbac_collection # Ensure collection exists before creating users/tokens? No, independent but good to have setup
):
    """Generate tokens for users with each test role and ensure they exist in DB."""
    
    account_id = security_test_data["account_a"].id
    tokens = {}
    
    for role_key, role_model in rbac_roles.items():
        user_id = str(uuid.uuid4())
        email = f"{role_key}_{uuid.uuid4().hex[:8]}@example.com"
        
        user = UserModel(
            id=user_id,
            account_id=account_id,
            email=email,
            password_hash="hashed_secret",
            role_id=role_model.id,
            is_active=True
        )
        db_session.add(user)
        
        token = jwt_service.create_access_token(
            user_id=user_id,
            account_id=account_id,
            email=email,
            role=role_model.name
        )
        tokens[role_key] = token
        
    await db_session.commit()
    return tokens
