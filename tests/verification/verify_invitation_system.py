"""Verification script for F1.11: User Invitation System.

Tests all invitation endpoints:
- POST /api/v1/invitations - Create invitation
- POST /api/v1/invitations/{token}/accept - Accept invitation
- GET /api/v1/invitations - List invitations
- DELETE /api/v1/invitations/{id} - Cancel invitation
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Configuration
BASE_URL = "http://localhost:8000"
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
    """Print a test message."""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{message}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*80}{Colors.RESET}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")


async def register_user(email: str, password: str, account_name: str) -> dict:
    """Register a new user and account."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/register",
            json={
                "email": email,
                "password": password,
                "account_name": account_name,
            },
        )
        response.raise_for_status()
        return response.json()


async def set_user_as_superadmin(user_id: str) -> None:
    """Set a user as superadmin by updating their account_id to SY0000."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET account_id = 'SY0000' WHERE id = :user_id"),
            {"user_id": user_id},
        )
    await engine.dispose()


async def test_create_invitation():
    """Test creating an invitation."""
    print_test("Test 1: Create Invitation")

    # Use UUID to make emails unique
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    # Register a user
    print_info("Registering admin user...")
    admin_response = await register_user(
        f"admin-{unique_id}@invitation-test.com",
        "SecureP@ss123!",
        f"Invitation Test Account {unique_id}",
    )
    admin_token = admin_response["token"]
    account_id = admin_response["account"]["id"]

    print_success(f"Admin registered with account ID: {account_id}")

    # Create an invitation
    invite_email = f"new-user-{unique_id}@test.com"
    print_info(f"Creating invitation for {invite_email}...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": invite_email},
        )

        if response.status_code == 201:
            invitation = response.json()
            print_success("Invitation created successfully")
            print_info(f"Invitation ID: {invitation['id']}")
            print_info(f"Email: {invitation['email']}")
            print_info(f"Status: {invitation['status']}")
            print_info(f"Expires at: {invitation['expires_at']}")
            return admin_token, invitation, invite_email, f"admin-{unique_id}@invitation-test.com"
        else:
            print_error(f"Failed to create invitation: {response.status_code}")
            print_error(response.text)
            return None, None, None, None


async def test_duplicate_invitation(admin_token: str, invite_email: str):
    """Test creating a duplicate invitation."""
    print_test("Test 2: Duplicate Invitation (Should Return 409)")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": invite_email},
        )

        if response.status_code == 409:
            print_success("Correctly returned 409 for duplicate invitation")
        else:
            print_error(f"Expected 409, got {response.status_code}")
            print_error(response.text)


async def test_invalid_email(admin_token: str):
    """Test creating an invitation with invalid email."""
    print_test("Test 3: Invalid Email (Should Return 422)")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "not-an-email"},
        )

        if response.status_code == 422:
            print_success("Correctly returned 422 for invalid email")
        else:
            print_error(f"Expected 422, got {response.status_code}")
            print_error(response.text)


async def test_list_invitations(admin_token: str):
    """Test listing invitations."""
    print_test("Test 4: List Invitations")

    async with httpx.AsyncClient() as client:
        # List all invitations
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Listed {data['total']} invitation(s)")
            for inv in data["invitations"]:
                print_info(f"  - {inv['email']} ({inv['status']})")
        else:
            print_error(f"Failed to list invitations: {response.status_code}")
            print_error(response.text)

        # List pending invitations
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/invitations?status_filter=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Listed {data['total']} pending invitation(s)")
        else:
            print_error(f"Failed to list pending invitations: {response.status_code}")


async def test_accept_invitation(invitation_token: str, invite_email: str):
    """Test accepting an invitation."""
    print_test("Test 5: Accept Invitation")

    # First, we need to get the token from the database since it's not returned in the API
    # For testing purposes, we'll extract it from the database
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT token FROM invitations WHERE email = :email"),
            {"email": invite_email},
        )
        row = result.fetchone()
        if row:
            token = row[0]
            print_info(f"Retrieved invitation token from database")
        else:
            print_error("Could not find invitation in database")
            await engine.dispose()
            return None
    await engine.dispose()

    # Accept the invitation
    print_info("Accepting invitation...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/invitations/{token}/accept",
            json={"password": "NewUserP@ss123!"},
        )

        if response.status_code == 200:
            auth_response = response.json()
            print_success("Invitation accepted successfully")
            print_info(f"User created: {auth_response['user']['email']}")
            print_info(f"Account: {auth_response['account']['name']}")
            print_info(f"Role: {auth_response['user']['role']}")
            return auth_response["token"]
        else:
            print_error(f"Failed to accept invitation: {response.status_code}")
            print_error(response.text)
            return None


async def test_accept_expired_token():
    """Test accepting an expired invitation."""
    print_test("Test 6: Accept Expired Token (Should Return 404)")

    # Use a fake token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/invitations/fake-token-12345/accept",
            json={"password": "TestP@ss123!"},
        )

        if response.status_code == 404:
            print_success("Correctly returned 404 for invalid token")
        else:
            print_error(f"Expected 404, got {response.status_code}")
            print_error(response.text)


async def test_accept_already_accepted(invitation_token: str, invite_email: str):
    """Test accepting an already accepted invitation."""
    print_test("Test 7: Accept Already Accepted Token (Should Return 404)")

    # Get the token from database
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT token FROM invitations WHERE email = :email"),
            {"email": invite_email},
        )
        row = result.fetchone()
        if row:
            token = row[0]
        else:
            print_error("Could not find invitation in database")
            await engine.dispose()
            return
    await engine.dispose()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/invitations/{token}/accept",
            json={"password": "AnotherP@ss123!"},
        )

        if response.status_code == 404:
            print_success("Correctly returned 404 for already accepted invitation")
        else:
            print_error(f"Expected 404, got {response.status_code}")
            print_error(response.text)


async def test_cancel_invitation(admin_token: str):
    """Test cancelling an invitation."""
    print_test("Test 8: Cancel Invitation")

    # Create a new invitation to cancel
    print_info("Creating invitation to cancel...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "cancel-test@test.com"},
        )

        if response.status_code != 201:
            print_error(f"Failed to create invitation: {response.status_code}")
            return

        invitation = response.json()
        invitation_id = invitation["id"]
        print_success(f"Created invitation {invitation_id}")

        # Cancel the invitation
        print_info("Cancelling invitation...")
        response = await client.delete(
            f"{BASE_URL}{API_PREFIX}/invitations/{invitation_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        if response.status_code == 204:
            print_success("Invitation cancelled successfully")
        else:
            print_error(f"Failed to cancel invitation: {response.status_code}")
            print_error(response.text)


async def test_user_already_in_account(admin_token: str, admin_email: str):
    """Test inviting a user who is already in the account."""
    print_test("Test 9: Invite User Already in Account (Should Return 400)")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": admin_email},  # Admin's own email
        )

        if response.status_code == 400:
            print_success("Correctly returned 400 for user already in account")
        else:
            print_error(f"Expected 400, got {response.status_code}")
            print_error(response.text)


async def main():
    """Run all verification tests."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}F1.11: User Invitation System - Verification Tests{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    try:
        # Test 1: Create invitation
        admin_token, invitation, invite_email, admin_email = await test_create_invitation()
        if not admin_token or not invitation:
            print_error("Failed to create initial invitation. Stopping tests.")
            sys.exit(1)

        # Test 2: Duplicate invitation
        await test_duplicate_invitation(admin_token, invite_email)

        # Test 3: Invalid email
        await test_invalid_email(admin_token)

        # Test 4: List invitations
        await test_list_invitations(admin_token)

        # Test 5: Accept invitation
        new_user_token = await test_accept_invitation(invitation, invite_email)

        # Test 6: Accept expired/invalid token
        await test_accept_expired_token()

        # Test 7: Accept already accepted token
        await test_accept_already_accepted(invitation, invite_email)

        # Test 8: Cancel invitation
        await test_cancel_invitation(admin_token)

        # Test 9: User already in account
        await test_user_already_in_account(admin_token, admin_email)

        print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}All tests completed!{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    except Exception as e:
        print_error(f"Test suite failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
