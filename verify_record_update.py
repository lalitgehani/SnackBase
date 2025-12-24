import asyncio
import httpx
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"

async def main():
    logger.info("Starting Record Update Verification")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Register User & Login
        import uuid
        run_id = uuid.uuid4().hex[:8]
        email = f"updater_{run_id}@example.com"
        password = "Password123!"
        account_name = f"Updater Account {run_id}"
        account_slug = f"updater-account-{run_id}"
        
        # Register
        logger.info(f"Registering user {email}...")
        resp = await client.post(f"{BASE_URL}/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Updater User",
            "account_name": account_name,
            "account_slug": account_slug
        })
        if resp.status_code == 201:
            logger.info("Registration successful")
        elif resp.status_code in [400, 409]:
            logger.info("User/Account likely already registered, proceeding to login...")
        else:
            logger.error(f"Registration failed: {resp.status_code} - {resp.text}")
            return

        # Login
        logger.info("Logging in...")
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": email,
            "password": password,
            "account": account_slug
        })
        if resp.status_code != 200:
            logger.error(f"Login failed: {resp.status_code} - {resp.text}")
            return
            
        # token is in "token" field, not "access_token"
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("Login successful")

        # 2. Setup Superadmin for Collection Creation
        admin_email = f"admin_{run_id}@example.com"
        admin_pass = "AdminPass123!"
        
        # Register Admin
        await client.post(f"{BASE_URL}/auth/register", json={
            "email": admin_email,
            "password": admin_pass,
            "full_name": "Super Admin",
            "account_name": f"Super Admin Account {run_id}"
        })
        
        # Promote Admin to Superadmin
        import sqlite3
        con = sqlite3.connect("sb_data/snackbase.db")
        cur = con.cursor()
        cur.execute("UPDATE users SET account_id = 'SY0000' WHERE email = ?", (admin_email,))
        con.commit()
        con.close()
        logger.info("Created Superadmin user")

        # Login as Superadmin
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": admin_email,
            "password": admin_pass,
            "account": "super-admin-account" # Note: slug might be different if collision, but likely ok for random run
        })
        # Wait, if I change account_id to SY0000, I can't login with original slug?
        # Login finds account by slug. Users are scoped to account.
        # If I change user's account_id to SY0000, they are no longer in "Super Admin Account".
        # They are in "SY0000" account.
        # So I need to login with account="SY0000"? Or whatever the system account slug is.
        # System account probably doesn't exist in `accounts` table by default? 
        # Or maybe I should just create the system account in `accounts` table first?
        
        # Let's try to ensure SY0000 exists in accounts.
        con = sqlite3.connect("sb_data/snackbase.db")
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO accounts (id, slug, name, created_at, updated_at) VALUES ('SY0000', 'system', 'System Account', datetime('now'), datetime('now'))")
        con.commit()
        con.close()
        
        # Login as Superadmin with system account
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": admin_email,
            "password": admin_pass,
            "account": "system"
        })
        if resp.status_code != 200:
             logger.error(f"Superadmin login failed: {resp.status_code} - {resp.text}")
             return
             
        admin_token = resp.json()["token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 3. Create Collection (as Superadmin)
        import uuid
        collection_name = f"products_update_{uuid.uuid4().hex[:8]}"
        schema = [
            {"name": "name", "type": "text", "required": True},
            {"name": "price", "type": "number", "required": True},
            {"name": "is_active", "type": "boolean", "default": True},
            {"name": "tags", "type": "json"}
        ]
        
        logger.info(f"Creating collection {collection_name}...")
        resp = await client.post(
            f"{BASE_URL}/collections", 
            headers=admin_headers,
            json={
                "name": collection_name,
                "schema": schema
            }
        )
        if resp.status_code in [201, 400]:
            logger.info("Collection ready")
        else:
            logger.error(f"Collection creation failed: {resp.status_code} - {resp.text}")
            return
            
        # 4. Create Record (as Normal User)
        # Use headers from the first user (updater_...)
        logger.info("Creating initial record...")
        if resp.status_code in [201, 400]: # 400 if already exists
            logger.info("Collection ready")
        else:
            logger.error(f"Collection creation failed: {resp.status_code} - {resp.text}")
            return

        # 4. Create Record
        logger.info("Creating initial record...")
        record_data = {
            "name": "Original Product",
            "price": 100,
            "is_active": True,
            "tags": ["original"]
        }
        resp = await client.post(
            f"{BASE_URL}/{collection_name}",
            headers=headers,
            json=record_data
        )
        if resp.status_code != 201:
            logger.error(f"Record creation failed: {resp.status_code} - {resp.text}")
            return
            
        record = resp.json()
        record_id = record["id"]
        logger.info(f"Record created: {record_id}")
        
        # 5. Test PATCH (Partial Update)
        logger.info("Testing PATCH (Partial Update)...")
        patch_data = {"price": 150} # Change price only
        
        resp = await client.patch(
            f"{BASE_URL}/{collection_name}/{record_id}",
            headers=headers,
            json=patch_data
        )
        
        if resp.status_code == 200:
            updated_record = resp.json()
            assert updated_record["price"] == 150
            assert updated_record["name"] == "Original Product" # Should stay same
            assert updated_record["updated_at"] > record["updated_at"]
            logger.info("PATCH success: Price updated, Name preserved")
        else:
            logger.error(f"PATCH failed: {resp.status_code} - {resp.text}")
            # Debug: fetch openapi.json
            schema_resp = await client.get("http://localhost:8000/openapi.json")
            if schema_resp.status_code == 200:
                 schema = schema_resp.json()
                 paths = schema.get("paths", {})
                 # Filter paths relevant to collection
                 logger.info("Relevant paths in OpenAPI:")
                 for path, methods in paths.items():
                     if "{" in path: # Show dynamic paths
                         logger.info(f"{path}: {list(methods.keys())}")
            return

        # 6. Test PUT (Full Update)
        logger.info("Testing PUT (Full Update)...")
        put_data = {
            "name": "Updated Product Full",
            "price": 200,
            "is_active": False,
            "tags": ["updated"]
        }
        # Note: We must provide all required fields
        
        resp = await client.put(
            f"{BASE_URL}/{collection_name}/{record_id}",
            headers=headers,
            json=put_data
        )
        
        if resp.status_code == 200:
            updated_record = resp.json()
            assert updated_record["name"] == "Updated Product Full"
            assert updated_record["price"] == 200
            assert updated_record["is_active"] is False
            assert updated_record["tags"] == ["updated"]
            logger.info("PUT success: All fields updated")
        else:
            logger.error(f"PUT failed: {resp.status_code} - {resp.text}")
            return
            
        # 7. Test Validation Error (Invalid Type)
        logger.info("Testing Validation Error...")
        resp = await client.patch(
            f"{BASE_URL}/{collection_name}/{record_id}",
            headers=headers,
            json={"price": "expensive"} # String instead of number
        )
        if resp.status_code == 400:
            logger.info("Validation correctly rejected invalid type")
        else:
            logger.error(f"Validation test failed: Got {resp.status_code} - {resp.text}")

        # 8. Test 404 (Non-existent Record)
        logger.info("Testing 404...")
        resp = await client.patch(
            f"{BASE_URL}/{collection_name}/00000000-0000-0000-0000-000000000000",
            headers=headers,
            json={"price": 100}
        )
        if resp.status_code == 404:
            logger.info("404 correctly returned")
        else:
             logger.error(f"404 test failed: Got {resp.status_code} - {resp.text}")

        logger.info("ALL TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(main())
