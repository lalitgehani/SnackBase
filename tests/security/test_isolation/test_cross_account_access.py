import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
from snackbase.infrastructure.persistence.models import AccountModel, UserModel, GroupModel, InvitationModel
from tests.security.conftest import AttackClient

@pytest.mark.asyncio
async def test_iso_xa_001_access_user_from_other_account(
    attack_client: AttackClient,
    isolation_test_data
):
    """ISO-XA-001: Access user from other account (GET /api/v1/accounts/{B}/users) -> 403 Forbidden."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    acc_b_id = isolation_test_data["account_b"].id
    
    resp = await attack_client.get(
        f"/api/v1/accounts/{acc_b_id}/users",
        headers=headers_a,
        description="User A attempts to access Account B's users list"
    )
    
    # Non-superadmins should not be able to access the accounts resource for other accounts
    assert resp.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_iso_xa_002_access_groups_from_other_account(
    attack_client: AttackClient,
    isolation_test_data,
    db_session: AsyncSession
):
    """ISO-XA-002: Access groups from other account (GET /api/v1/groups as A) -> Only see A's groups."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    acc_b_id = isolation_test_data["account_b"].id
    
    # 1. Create a group in Account B
    group_b = GroupModel(
        id=str(uuid.uuid4()),
        name="Security Team B",
        account_id=acc_b_id,
        description="B's group"
    )
    db_session.add(group_b)
    await db_session.commit()
    
    # 2. User A lists groups
    resp = await attack_client.get(
        "/api/v1/groups",
        headers=headers_a,
        description="User A lists groups (should not see B's groups)"
    )
    
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify User A doesn't see Group B
    # /api/v1/groups returns a flat list
    group_names = [g["name"] for g in data]
    assert "Security Team B" not in group_names

@pytest.mark.asyncio
async def test_iso_xa_003_access_invitations_from_other_account(
    attack_client: AttackClient,
    isolation_test_data,
    db_session: AsyncSession
):
    """ISO-XA-003: Access invitations from other account (GET /api/v1/invitations as A) -> Only see A's invitations."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    acc_b_id = isolation_test_data["account_b"].id
    
    # 1. Create an invitation in Account B
    inv_b = InvitationModel(
        id=str(uuid.uuid4()),
        email="invite-b@example.com",
        account_id=acc_b_id,
        token="token-b-" + str(uuid.uuid4())[:8],
        invited_by="user-b",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db_session.add(inv_b)
    await db_session.commit()
    
    # 2. User A lists invitations
    resp = await attack_client.get(
        "/api/v1/invitations",
        headers=headers_a,
        description="User A lists invitations (should not see B's)"
    )
    
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify User A doesn't see Invitation B
    # /api/v1/invitations returns a dict with 'invitations' key
    emails = [inv["email"] for inv in data["invitations"]]
    assert "invite-b@example.com" not in emails

@pytest.mark.asyncio
async def test_iso_xa_004_create_record_in_other_account(
    attack_client: AttackClient,
    isolation_test_data,
    isolation_collection
):
    """ISO-XA-004: Create record in other account (POST /api/v1/records/{collection} with account_id=B) -> 422."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    acc_b_id = isolation_test_data["account_b"].id
    
    record_data = {
        "title": "Cross-Account Record",
        "secret_data": "attempt",
        "account_id": acc_b_id
    }
    
    resp = await attack_client.post(
        f"/api/v1/records/{isolation_collection}",
        json=record_data,
        headers=headers_a,
        description="User A attempts to create a record explicitly linked to Account B"
    )
    
    # account_id is a system field and should be rejected if provided in body
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

@pytest.mark.asyncio
async def test_iso_xa_005_update_account_id_field(
    attack_client: AttackClient,
    isolation_test_data,
    isolation_collection
):
    """ISO-XA-005: Update account_id field (PATCH /api/v1/records/{collection}/{id} with account_id=B) -> 422."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    acc_b_id = isolation_test_data["account_b"].id
    
    # 1. Create record as A
    create_resp = await attack_client.post(
        f"/api/v1/records/{isolation_collection}",
        json={"title": "A's Record", "secret_data": "initial"},
        headers=headers_a
    )
    record_id = create_resp.json()["id"]
    
    # 2. Try to update account_id to B
    update_data = {"account_id": acc_b_id}
    resp = await attack_client.patch(
        f"/api/v1/records/{isolation_collection}/{record_id}",
        json=update_data,
        headers=headers_a,
        description="User A attempts to move their record to Account B"
    )
    
    # account_id is immutable/system field and should be rejected
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

@pytest.mark.asyncio
async def test_iso_xa_006_jwt_token_with_swapped_account_id(
    attack_client: AttackClient,
    isolation_test_data
):
    """ISO-XA-006: JWT token with swapped account_id -> 401/403."""
    # We simulate a tampered token where the account_id claim is changed but signature remains valid 
    # (this would only happen if the secret was known, but here we test if the backend 
    # validates that the user actually belongs to that account if it checks).
    # However, SnackBase extracts account_id from the token and uses it to scope queries.
    # If the token is validly signed but has a wrong account_id, the user would see 
    # the other account's data IF they are allowed to use that token.
    # BUT register/login generates the token with the CORRECT account_id.
    
    # Scenario: An attacker manages to get a token for THEIR user but with OTHER account_id.
    # We can craft such a token using the internal service for this test.
    
    tampered_token = jwt_service.create_access_token(
        user_id="user-a",
        account_id="AC0002", # Swapped to B
        email="user-a@example.com",
        role="user"
    )
    
    headers = {"Authorization": f"Bearer {tampered_token}"}
    
    # Try to access sensitive info
    resp = await attack_client.get(
        "/api/v1/auth/me",
        headers=headers,
        description="Attacker uses a tampered token with swapped account_id"
    )
    
    # If the backend validates that user-a actually belongs to AC0002, this should fail.
    # If it just trusts the token, it might succeed but return 'me' details for that user.
    # However, the record repository uses account_id from the token to filter.
    
    # Let's see what happens. Ideally, the auth middleware or the 'me' endpoint 
    # should verify the user-account relationship.
    
    # If it returns 200, we should check if it's safe. 
    # Actually, the PRD says expected result is "401 Invalid token" or similar.
    # This implies that a token with a mismatched user/account should be rejected.
    
    assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
