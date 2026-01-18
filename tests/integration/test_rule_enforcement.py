import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from snackbase.infrastructure.auth.jwt_service import jwt_service

@pytest.mark.asyncio
async def test_rule_enforcement_end_to_end(client: AsyncClient, superadmin_token, regular_user_token, db_session: AsyncSession):
    # Get regular user's account_id
    from snackbase.infrastructure.persistence.models.user import UserModel
    from sqlalchemy import select
    
    res = await db_session.execute(select(UserModel).where(UserModel.id == "regular_user"))
    user1 = res.scalar_one()
    account_id = user1.account_id
    
    # Create another user in the same account
    from snackbase.infrastructure.persistence.models.role import RoleModel
    user_role = (await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))).scalar_one()
    
    user2 = UserModel(
        id="user2",
        email="user2@snackbase.com",
        account_id=account_id,
        password_hash="hashed_secret",
        role=user_role,
        is_active=True,
    )
    db_session.add(user2)
    await db_session.commit()
    
    user2_token = jwt_service.create_access_token(
        user_id=user2.id,
        account_id=user2.account_id,
        email=user2.email,
        role="user",
    )
    
    user1_headers = {"Authorization": f"Bearer {regular_user_token}"}
    user2_headers = {"Authorization": f"Bearer {user2_token}"}
    super_headers = {"Authorization": f"Bearer {superadmin_token}"}
    
    # 1. Create collection 'tasks' as superadmin
    await client.post("/api/v1/collections", json={
        "name": "tasks",
        "label": "Tasks",
        "schema": [
            {"name": "title", "type": "text", "required": True},
            {"name": "is_public", "type": "boolean", "default": False}
        ]
    }, headers=super_headers)
    
    # 2. Set rules: list/view public OR owned
    rules_payload = {
        "list_rule": "is_public = true || created_by = @request.auth.id",
        "view_rule": "is_public = true || created_by = @request.auth.id",
        "create_rule": "@request.auth.id != \"\"",
        "update_rule": "created_by = @request.auth.id",
        "delete_rule": "created_by = @request.auth.id"
    }
    await client.put("/api/v1/collections/tasks/rules", json=rules_payload, headers=super_headers)
    
    # 3. Create records as User 1
    # 3.1 Public task
    res1 = await client.post("/api/v1/records/tasks", json={"title": "User1 Public", "is_public": True}, headers=user1_headers)
    assert res1.status_code == 201
    
    # 3.2 Private task
    res2 = await client.post("/api/v1/records/tasks", json={"title": "User1 Private", "is_public": False}, headers=user1_headers)
    assert res2.status_code == 201
    user1_private_id = res2.json()["id"]
    
    # 4. List as User 2
    # Should see: User1 Public
    # Should NOT see: User1 Private
    list_res = await client.get("/api/v1/records/tasks", headers=user2_headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "User1 Public"
    
    # 5. Access Private task as User 2 (View)
    # Should return 404 because of the rule filter
    view_res = await client.get(f"/api/v1/records/tasks/{user1_private_id}", headers=user2_headers)
    assert view_res.status_code == 404
    
    # 6. Create record as User 2
    res3 = await client.post("/api/v1/records/tasks", json={"title": "User2 Private", "is_public": False}, headers=user2_headers)
    assert res3.status_code == 201
    user2_private_id = res3.json()["id"]
    
    # 7. List as User 2 again
    # Should see: User1 Public AND User2 Private
    list_res = await client.get("/api/v1/records/tasks", headers=user2_headers)
    assert list_res.json()["total"] == 2
    titles = [i["title"] for i in list_res.json()["items"]]
    assert "User1 Public" in titles
    assert "User2 Private" in titles
    
    # 8. Update User1's record as User 2
    # Should fail with 404 (filter doesn't match)
    update_res = await client.patch(f"/api/v1/records/tasks/{user1_private_id}", json={"title": "Hacked"}, headers=user2_headers)
    assert update_res.status_code == 404
    
    # 9. Delete User1's record as User 2
    # Should fail with 404
    delete_res = await client.delete(f"/api/v1/records/tasks/{user1_private_id}", headers=user2_headers)
    assert delete_res.status_code == 404
    
    # 10. Superadmin should see everything (bypass)
    list_super = await client.get("/api/v1/records/tasks", headers=super_headers)
    assert list_super.status_code == 200
    assert list_super.json()["total"] >= 3
    
@pytest.mark.asyncio
async def test_locked_rules(client: AsyncClient, superadmin_token, regular_user_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    user_headers = {"Authorization": f"Bearer {regular_user_token}"}
    
    # Create collection
    await client.post("/api/v1/collections", json={
        "name": "secrets",
        "label": "Secrets",
        "schema": [{"name": "content", "type": "text"}]
    }, headers=headers)
    
    # Set list_rule to null (locked)
    await client.put("/api/v1/collections/secrets/rules", json={"list_rule": None}, headers=headers)
    
    # Try to list as regular user
    res = await client.get("/api/v1/records/secrets", headers=user_headers)
    assert res.status_code == 403
    assert "locked" in res.json()["detail"]

@pytest.mark.asyncio
async def test_create_rule_validation(client: AsyncClient, superadmin_token, regular_user_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    user_headers = {"Authorization": f"Bearer {regular_user_token}"}
    
    # Create collection
    await client.post("/api/v1/collections", json={
        "name": "logs",
        "label": "Logs",
        "schema": [{"name": "level", "type": "text"}]
    }, headers=headers)
    
    # Set create_rule: only 'info' or 'error' logs allowed
    await client.put("/api/v1/collections/logs/rules", json={
        "create_rule": "@request.data.level = \"info\" || @request.data.level = \"error\"",
        "list_rule": ""
    }, headers=headers)
    
    # Create valid log
    res1 = await client.post("/api/v1/records/logs", json={"level": "info"}, headers=user_headers)
    assert res1.status_code == 201
    
    # Create invalid log
    res2 = await client.post("/api/v1/records/logs", json={"level": "debug"}, headers=user_headers)
    assert res2.status_code == 400
    assert "satisfy collection rules" in res2.json()["detail"]
