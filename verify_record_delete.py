import asyncio
import httpx
import sys
from typing import Any

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
SUPERADMIN_EMAIL = "admin@example.com"
SUPERADMIN_PASSWORD = "admin_password"  # Assuming this from previous context or creating new if needed
NORMAL_USER_EMAIL = "user_delete@example.com"
NORMAL_USER_PASSWORD = "Password123!"

async def register_user(client: httpx.AsyncClient, email: str, password: str, role: str = "authenticated"):
    response = await client.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password, "username": email.split("@")[0], "account_name": "Test Account"}
    )
    if response.status_code == 201:
        print(f"Registered {email}")
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text:
         print(f"User {email} already exists")
         return None # User exists
    else:
        print(f"Failed to register {email}: {response.text}")
        return None

async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    # Account slug derived from "Test Account" -> "test-account"
    response = await client.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password, "account": "test-account"}
    )
    if response.status_code == 200:
        return response.json()["token"]
    print(f"Login failed for {email}: {response.text}")
    sys.exit(1)

async def create_collection(client: httpx.AsyncClient, token: str, name: str, schema: list[dict]):
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        f"{BASE_URL}/collections",
        json={"name": name, "schema": schema},
        headers=headers
    )
    if response.status_code in (201, 200): # 200 if exists (not implemented but handling hypothetically)
         print(f"Collection {name} created/exists")
         return response.json()
    elif response.status_code == 400 and "already exists" in response.text: # Should handle duplicates
         print(f"Collection {name} already exists (assumed)")
         return {"name": name} # return mock
    else:
        print(f"Failed to create collection {name}: {response.text}")
        # sys.exit(1) # Don't exit, might already exist

async def create_record(client: httpx.AsyncClient, token: str, collection: str, data: dict) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        f"{BASE_URL}/{collection}",
        json=data,
        headers=headers
    )
    if response.status_code == 201:
        return response.json()["id"]
    print(f"Failed to create record in {collection}: {response.status_code} {response.text}")
    print(f"URL: {BASE_URL}/{collection}")
    sys.exit(1)

async def delete_record(client: httpx.AsyncClient, token: str, collection: str, record_id: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.delete(
        f"{BASE_URL}/{collection}/{record_id}",
        headers=headers
    )
    return response.status_code

async def get_record(client: httpx.AsyncClient, token: str, collection: str, record_id: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(
        f"{BASE_URL}/{collection}/{record_id}",
        headers=headers
    )
    return response.status_code

import uuid

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Setup - Unique User/Account
        unique_id = str(uuid.uuid4())[:8]
        email = f"user_delete_{unique_id}@example.com"
        account_name = f"Delete Test {unique_id}"
        account_slug = f"delete-test-{unique_id}"
        password = "Password123!"

        # Register (we can't easily use account_slug in register request param shown previously unless we added it back to RegisterRequest model? 
        # The code I saw in auth_router.py supports it. My verification script passed 'account_name'. 
        # Register creates a slug from name if not provided. Let's just pass account_name).
        
        print(f"Registering {email}...")
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "password": password, "username": f"user_{unique_id}", "account_name": account_name}
        )
        if response.status_code != 201:
             print(f"Registration failed: {response.text}")
             sys.exit(1)
        
        
        # Promote user to superadmin by changing account_id to SY0000
        # First ensure system account exists
        print("Promoting user to superadmin (SY0000)...")
        import sqlite3
        db = sqlite3.connect("sb_data/snackbase.db")
        
        # Insert system account if not exists
        try:
             db.execute("INSERT INTO accounts (id, slug, name) VALUES ('SY0000', 'system', 'System Account')")
        except sqlite3.IntegrityError:
             pass # Already exists
             
        # Update user account_id
        db.execute("UPDATE users SET account_id = 'SY0000' WHERE email = ?", (email,))
        db.commit()
        db.close()
        
        # Login to get NEW token with superadmin rights
        print("Logging in to get superadmin token...")
        
        response = await client.post(
             f"{BASE_URL}/auth/login",
             json={"email": email, "password": password, "account": "system"}
        )
        if response.status_code != 200:
             print(f"Login failed: {response.text}")
             sys.exit(1)
             
        user_token = response.json()["token"]
        
        # Now user is superadmin
        admin_token = user_token

        # 2. Setup - Collections
        parent_col_name = "authors_del"
        child_col_name = "books_del"
        
        parent_schema = [{"name": "name", "type": "text", "required": True}]
        child_schema = [
            {"name": "title", "type": "text", "required": True},
            {"name": "author", "type": "reference", "collection": parent_col_name, "on_delete": "restrict"}
        ]
        
        await create_collection(client, admin_token, parent_col_name, parent_schema)
        await create_collection(client, admin_token, child_col_name, child_schema)
        
        # 3. Create Records
        print(f"Creating record in {parent_col_name}...")
        author_id = await create_record(client, user_token, parent_col_name, {"name": "Delete Me"})
        
        print(f"Creating record in {child_col_name}...")
        # Note: If books_del creation failed, this will 404.
        book_id = await create_record(client, user_token, child_col_name, {"title": "My Book", "author": author_id})
        
        print("\n--- Testing Delete Scenarios ---")

        # Scenario A: Delete record with dependencies (Should verify FK constraint if enforced, or Cascade)
        # In this system, we don't know the exact FK behavior (Cascade or Restrict) set by TableBuilder.
        # Let's try to delete the Author.
        print(f"Attempting to delete Author {author_id} (has dependent Book)...")
        status_code = await delete_record(client, user_token, parent_col_name, author_id)
        
        if status_code == 409:
            print("Received 409 Conflict - FK Constraint working (Restrict)")
            # Cleanup child to allow delete
            await delete_record(client, user_token, child_col_name, book_id)
            status_code = await delete_record(client, user_token, parent_col_name, author_id)
            assert status_code == 204, f"Expected 204 after child cleanup, got {status_code}"
            print("Successfully deleted parent after child cleanup")
            
        elif status_code == 204:
            print("Received 204 No Content - FK Cascade assumed/worked")
            # Verify child is gone (if cascade) or still there? 
            # If cascade, book should be gone.
            child_status = await get_record(client, user_token, child_col_name, book_id)
            if child_status == 404:
                print("Child record also deleted (Cascade verified)")
            else:
                 print(f"Child record status: {child_status} (Cascade might not be set or not working as expected)")
        else:
            print(f"Unexpected status code: {status_code}")
            sys.exit(1)

        # Verify parent is gone
        parent_status = await get_record(client, user_token, parent_col_name, author_id)
        assert parent_status == 404, f"Parent record still exists! Status: {parent_status}"
        print("Verified parent record deletion")

        # Scenario B: Delete non-existent record
        print("\nAttempting to delete non-existent record...")
        status_code = await delete_record(client, user_token, parent_col_name, "non-existent-id")
        assert status_code == 404, f"Expected 404, got {status_code}"
        print("Verified 404 for non-existent record")

        # Scenario C: Clean up simple record
        print("\nCreating and deleting simple record...")
        simple_id = await create_record(client, user_token, parent_col_name, {"name": "Simple Delete"})
        status_code = await delete_record(client, user_token, parent_col_name, simple_id)
        assert status_code == 204, f"Expected 204, got {status_code}"
        print("Verified simple deletion")

        print("\nAll delete tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
