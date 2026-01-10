
"""Verification script for F5.3: Invitation Resend.

Tests the resend invitation endpoint:
- POST /api/v1/invitations/{id}/resend
"""

import asyncio
import sys
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from httpx import AsyncClient, ASGITransport

from snackbase.infrastructure.api.app import create_app

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
    if response.status_code == 409: # Already exists
         return {} 
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


async def test_resend_invitation(client: AsyncClient):
    """Test resending an invitation."""
    print_test("Test: Resend Invitation")

    unique_id = str(uuid.uuid4())[:8]
    
    # 1. Register Admin
    print_info("Registering admin user...")
    admin_email = f"admin-resend-{unique_id}@test.com"
    admin_password = "SecureP@ss123!"
    
    admin_response = await register_user(
        client,
        admin_email,
        admin_password,
        f"Test Account {unique_id}",
    )
    
    # Check if admin created (might fail if email conflict, but we used unique id)
    if not admin_response: # Fallback login if exists? Unlikely with uuid
        print_error("Failed to register admin")
        return

    admin_account_slug = admin_response["account"]["slug"]
    
    # Verify Email
    await verify_user_email(admin_email)
    
    # Login
    print_info("Logging in...")
    admin_token = await login_user(client, admin_email, admin_password, admin_account_slug)
    
    # 2. Create Invitation
    invite_email = f"invite-resend-{unique_id}@test.com"
    print_info(f"Creating invitation for {invite_email}...")
    
    response = await client.post(
        f"{API_PREFIX}/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": invite_email},
    )

    if response.status_code != 201:
        print_error(f"Failed to create invitation: {response.text}")
        return

    invitation = response.json()
    invitation_id = invitation["id"]
    print_success(f"Invitation created: {invitation_id}")
    
    # Check if token is present (New Schema check)
    if "token" in invitation:
        print_success(f"Token present in response: {invitation['token'][:8]}...")
    else:
        print_error("Token NOT present in response")

    # 3. Resend Invitation
    print_info("Resending invitation...")
    response = await client.post(
        f"{API_PREFIX}/invitations/{invitation_id}/resend",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    if response.status_code == 200:
        print_success("Resend successful")
        print_info(f"Response: {response.json()}")
    else:
        print_error(f"Resend failed: {response.status_code}: {response.text}")
        
    # 4. List invitations to check token visibility there too
    print_info("Listing invitations to check token...")
    response = await client.get(
        f"{API_PREFIX}/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    if response.status_code == 200:
        invs = response.json()["invitations"]
        if invs and "token" in invs[0]:
             print_success("Token present in list response")
        else:
             print_error("Token NOT present in list response")
    

async def main():
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}F5.3: Invitation Resend - Verification Tests{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    app = create_app()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            await test_resend_invitation(client)
            print(f"\n{Colors.GREEN}{Colors.BOLD}All tests completed!{Colors.RESET}\n")
            
        except Exception as e:
            print_error(f"Test suite failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
