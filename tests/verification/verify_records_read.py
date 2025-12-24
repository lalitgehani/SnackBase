import asyncio
import httpx
import sys
import uuid
import sqlite3
import os

BASE_URL = "http://localhost:8000/api/v1"
DB_PATH = "sb_data/snackbase.db"

async def register_user(email: str, password: str, account_name: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": password,
                "account_name": account_name
            }
        )
        if response.status_code != 201:
            print(f"Failed to register {email}: {response.text}")
            sys.exit(1)
        resp_json = response.json()
        print(f"Registration response: {resp_json}")
        return resp_json

async def login_user(email: str, password: str, account_id: str) -> dict:
     async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": email,
                "password": password,
                "account": account_id
            }
        )
        if response.status_code != 200:
            print(f"Failed to login {email}: {response.text}")
            sys.exit(1)
        return response.json()

async def create_collection(token: str, name: str, schema: list):
    async with httpx.AsyncClient() as client:
        # Note: empty string path because of recent fix
        response = await client.post(
            f"{BASE_URL}/collections",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": name, "schema": schema}
        )
        if response.status_code == 409:
            print(f"Collection {name} already exists.")
            return
        if response.status_code != 201:
            print(f"Failed to create collection {name}: {response.text}")
            sys.exit(1)

async def create_record(token: str, collection: str, data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{collection}",
            headers={"Authorization": f"Bearer {token}"},
            json=data
        )
        if response.status_code != 201:
            print(f"Failed to create record: {response.text}")
            sys.exit(1)
        return response.json()

def promote_to_superadmin(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Ensure SY0000 account exists
    cursor.execute("SELECT id FROM accounts WHERE id = 'SY0000'")
    if not cursor.fetchone():
        print("Creating system account SY0000...")
        cursor.execute("""
            INSERT INTO accounts (id, slug, name, created_at, updated_at)
            VALUES ('SY0000', 'system', 'System Account', datetime('now'), datetime('now'))
        """)
    
    # 2. Update user account_id
    print(f"Moving user {user_id} to SY0000...")
    cursor.execute("UPDATE users SET account_id = 'SY0000' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

async def main():
    # 1. Register Admin User A
    email_a = f"admin_a_{uuid.uuid4().hex[:8]}@example.com"
    account_name_a = f"Account A {uuid.uuid4().hex[:8]}"
    password = "Password123!"
    print(f"Registering User A: {email_a}")
    auth_a = await register_user(email_a, password, account_name_a)
    user_id_a = auth_a["user"]["id"]
    
    # Promote A to superadmin
    promote_to_superadmin(user_id_a)
    
    # Login A again to get superadmin token
    print("Logging in as User A (Superadmin)...")
    auth_a = await login_user(email_a, password, "SY0000")
    token_a = auth_a["token"]
    account_id_a = "SY0000"
    
    # 2. Register Admin User B
    email_b = f"admin_b_{uuid.uuid4().hex[:8]}@example.com"
    account_name_b = f"Account B {uuid.uuid4().hex[:8]}"
    print(f"Registering User B: {email_b}")
    auth_b = await register_user(email_b, password, account_name_b)
    token_b = auth_b["token"]
    account_id_b = auth_b["account"]["id"] # Still using user's own account

    # 3. Create Collection
    collection_name = f"notes_{uuid.uuid4().hex[:8]}"
    schema = [
        {"name": "title", "type": "text", "required": True},
        {"name": "priority", "type": "number", "default": 1}
    ]
    
    print(f"Creating collection {collection_name} as User A (Superadmin)")
    # We call create_collection with token_a (superadmin)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/collections",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": collection_name, "schema": schema}
        )
        if response.status_code == 201:
             print("Collection created.")
        else:
             print(f"Collection creation response: {response.status_code} {response.text}")
             if response.status_code != 409:
                 return

    # 4. Create Records for A
    print("Creating 50 records for User A...")
    items = []
    for i in range(50):
        try:
            res = await create_record(token_a, collection_name, {
                "title": f"Note A {i}",
                "priority": i
            })
            items.append(res)
        except SystemExit:
            return

    # 5. Verify List for A (Default)
    print("Verifying List (Default)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{collection_name}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert resp.status_code == 200, f"List failed: {resp.text}"
        data = resp.json()
        assert data["total"] == 50, f"Expected 50 total, got {data['total']}"
        assert len(data["items"]) == 30, f"Expected 30 items (default limit), got {len(data['items'])}"
        print(f"List OK: Got {len(data['items'])} items, total {data['total']}")

    # 6. Verify Pagination
    print("Verifying Pagination (skip=30)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{collection_name}?skip=30",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        data = resp.json()
        assert len(data["items"]) == 20, f"Expected 20 items, got {len(data['items'])}"
        print(f"Pagination OK: Got {len(data['items'])} items")

    # 7. Verify Sorting
    print("Verifying Sorting (-priority)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{collection_name}?sort=-priority&limit=5",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        data = resp.json()
        sorted_items = data["items"]
        assert sorted_items[0]["priority"] == 49, f"Expected priority 49, got {sorted_items[0]['priority']}"
        print("Sorting OK")
        
    # 8. Verify Filtering
    print("Verifying Filtering (priority=10)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{collection_name}?priority=10",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        data = resp.json()
        assert data["total"] == 1, f"Expected 1 record, got {data['total']}"
        assert data["items"][0]["priority"] == 10
        print("Filtering OK")

    # 9. Verify Isolation (User B)
    print("Verifying Isolation (User B)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{collection_name}",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        # B should see 0 records because account_id is different.
        assert resp.status_code == 200, f"User B List failed: {resp.text}"
        data = resp.json()
        assert data["total"] == 0, f"User B should see 0 records, got {data['total']}"
        print("Isolation OK")
        
    # 10. Verify Get Single
    record_id = items[0]["id"]
    print(f"Verifying Get Single ({record_id})...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{collection_name}/{record_id}",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == record_id
        print("Get Single OK")
        
    # 11. Verify Get Single Isolation (User B)
    print("Verifying Get Single Isolation (User B)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{collection_name}/{record_id}",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert resp.status_code == 404, f"User B should get 404, got {resp.status_code}"
        print("Get Single Isolation OK")

    print("\nALL VERIFICATION TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
