
"""Verification script for F1.11: User Invitation System.

Tests all invitation endpoints using in-process ASGI client:
- POST /api/v1/invitations - Create invitation
- POST /api/v1/invitations/{token}/accept - Accept invitation
- GET /api/v1/invitations - List invitations
- DELETE /api/v1/invitations/{id} - Cancel invitation
"""

import asyncio
import sys
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from httpx import AsyncClient, ASGITransport

from snackbase.infrastructure.api.app import create_app
from snackbase.infrastructure.persistence.database import get_db_session

# Configuration
API_PREFIX = "/api/v1"
DATABASE_URL = "sqlite+aiosqlite:///./sb_data/snackbase.db"


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_test(message: str) -> None:
    print(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{message}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*80}{Colors.RESET}")


def print_success(message: str) -> None:
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")


async def verify_user_email(email: str) -> None:
    """Mark user email as verified directly in DB."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET email_verified = 1 WHERE email = :email"),
            {"email": email},
        )
    await engine.dispose()


async def register_user(client: AsyncClient, email: str, password: str, account_name: str) -> dict:
    """Register a new user and account."""
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": email,
            "password": password,
            "account_name": account_name,
        },
    )
    response.raise_for_status()
    return response.json()


async def login_user(client: AsyncClient, email: str, password: str, account: str) -> str:
    """Login and return access token."""
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={
            "email": email,
            "password": password,
            "account": account,
        },
    )
    response.raise_for_status()
    return response.json()["token"]


async def test_create_invitation(client: AsyncClient):
    """Test creating an invitation."""
    print_test("Test 1: Create Invitation")

    unique_id = str(uuid.uuid4())[:8]
    
    # Register Admin
    print_info("Registering admin user...")
    admin_email = f"admin-{unique_id}@test.com"
    admin_password = "SecureP@ss123!"
    
    admin_response = await register_user(
        client,
        admin_email,
        admin_password,
        f"Test Account {unique_id}",
    )
    admin_account_slug = admin_response["account"]["slug"]
    
    # Verify Email
    print_info("Verifying admin email...")
    await verify_user_email(admin_email)
    
    # Login
    print_info("Logging in...")
    admin_token = await login_user(client, admin_email, admin_password, admin_account_slug)
    
    # Get Account ID
    account_id = None
    response = await client.get(
        f"{API_PREFIX}/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    if response.status_code == 200:
        account_id = response.json()["account_id"]
        print_success(f"Admin registered with account ID: {account_id}")
    else:
        print_error("Failed to get user info")
        return None, None, None, None

    # Create Invitation
    invite_email = f"new-user-{unique_id}@test.com"
    print_info(f"Creating invitation for {invite_email}...")
    
    response = await client.post(
        f"{API_PREFIX}/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": invite_email},
    )

    if response.status_code == 201:
        invitation = response.json()
        print_success("Invitation created successfully")
        print_info(f"ID: {invitation['id']}")
        print_info(f"Email Sent: {invitation.get('email_sent')}")
        
        if invitation.get('email_sent') is True:
            print_success("Email sent flag is True")
        else:
            print_error("Email sent flag is False")
            
        return admin_token, invitation, invite_email, admin_email
    else:
        print_error(f"Failed to create invitation: {response.status_code}")
        print_error(response.text)
        return None, None, None, None


async def test_duplicate_invitation(client: AsyncClient, admin_token: str, invite_email: str):
    print_test("Test 2: Duplicate Invitation (Should Return 409)")
    response = await client.post(
        f"{API_PREFIX}/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": invite_email},
    )
    if response.status_code == 409:
        print_success("Correctly returned 409")
    else:
        print_error(f"Expected 409, got {response.status_code}: {response.text}")


async def test_invalid_email(client: AsyncClient, admin_token: str):
    print_test("Test 3: Invalid Email (Should Return 422)")
    response = await client.post(
        f"{API_PREFIX}/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "not-an-email"},
    )
    if response.status_code == 422:
        print_success("Correctly returned 422")
    else:
        print_error(f"Expected 422, got {response.status_code}: {response.text}")


async def test_list_invitations(client: AsyncClient, admin_token: str):
    print_test("Test 4: List Invitations")
    response = await client.get(
        f"{API_PREFIX}/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    if response.status_code == 200:
        data = response.json()
        print_success(f"Listed {data['total']} invitation(s)")
        for inv in data["invitations"]:
            print_info(f"  - {inv['email']} ({inv['status']}) [{inv.get('account_code')}]")
    else:
        print_error(f"Failed to list: {response.status_code}: {response.text}")


async def test_accept_invitation(client: AsyncClient, invite_email: str):
    print_test("Test 5: Accept Invitation")
    
    # Get token from DB
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT token FROM invitations WHERE email = :email"),
            {"email": invite_email},
        )
        row = result.fetchone()
        token = row[0] if row else None
    await engine.dispose()
    
    if not token:
        print_error("Invitation token not found in DB")
        return None

    # Accept
    print_info("Accepting invitation...")
    response = await client.post(
        f"{API_PREFIX}/invitations/{token}/accept",
        json={"password": "NewUserP@ss123!"},
    )

    if response.status_code == 200:
        auth = response.json()
        print_success(f"Accepted! New User: {auth['user']['email']}")
        return auth["token"]
    else:
        print_error(f"Failed to accept: {response.status_code}: {response.text}")
        return None


async def test_cancel_invitation(client: AsyncClient, admin_token: str):
    print_test("Test 8: Cancel Invitation")
    
    # Create temp invitation
    resp = await client.post(
        f"{API_PREFIX}/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "cancel-me@test.com"},
    )
    if resp.status_code != 201:
        print_error("Failed to create temp invitation")
        return
        
    inv_id = resp.json()["id"]
    print_success(f"Created temp invitation {inv_id}")
    
    # Cancel
    resp = await client.delete(
        f"{API_PREFIX}/invitations/{inv_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    if resp.status_code == 204:
        print_success("Invitation cancelled successfully")
    else:
        print_error(f"Failed to cancel: {resp.status_code}: {resp.text}")


async def main():
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}F1.11: User Invitation System - Verification Tests (In-Process){Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    app = create_app()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # Run tests
            admin_token, invitation, invite_email, admin_email = await test_create_invitation(client)
            if not admin_token:
                sys.exit(1)
                
            await test_duplicate_invitation(client, admin_token, invite_email)
            await test_invalid_email(client, admin_token)
            await test_list_invitations(client, admin_token)
            
            new_token = await test_accept_invitation(client, invite_email)
            
            # Additional tests like expired token, etc. omitted for brevity if needed, 
            # but can be added.
            
            await test_cancel_invitation(client, admin_token)
            
            print(f"\n{Colors.GREEN}{Colors.BOLD}All tests completed!{Colors.RESET}\n")
            
        except Exception as e:
            print_error(f"Test suite failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
