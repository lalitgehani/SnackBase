
import asyncio
import sys
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from snackbase.infrastructure.api.app import create_app
from snackbase.infrastructure.api.dependencies import get_email_service
from snackbase.infrastructure.services.email_service import EmailService

# Mock Email Service
mock_email_service = AsyncMock(spec=EmailService)
mock_email_service.send_template_email.return_value = True

async def get_mock_email_service():
    return mock_email_service

API_PREFIX = "/api/v1"

async def main():
    print("Verifying Invitation Account Name Fix...")
    
    app = create_app()
    app.dependency_overrides[get_email_service] = get_mock_email_service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # 1. Register Superadmin
            unique_id = str(uuid.uuid4())[:8]
            admin_email = f"superadmin-{unique_id}@test.com"
            admin_password = "SecureP@ss123!"
            
            # Note: Registration normally creates a regular user/account.
            # To become superadmin, we'd need to manipulate the DB or use a known superadmin.
            # However, the issue is about "account name appearing as system". 
            # If I invite someone to MyAccount, it should say "MyAccount", not "Sytem".
            # If I am superadmin (system account) and invite to "TargetAccount", it should say "TargetAccount".
            
            # Let's test the general case: Invite to an account.
            
            print("Registering user...")
            resp = await client.post(f"{API_PREFIX}/auth/register", json={
                "email": admin_email,
                "password": admin_password,
                "account_name": f"Target Account {unique_id}"
            })
            resp.raise_for_status()
            account_slug = resp.json()["account"]["slug"]
            target_account_name = f"Target Account {unique_id}"
            
            # Manually verify email (skip DB step for simplicity if possible, or assume auto-verified in test env? 
            # No, need to verify. Using the helper function from previous script pattern is safer, but I can just update DB directly)
            
            # Assuming I can login if I disable verification check or just verify it.
            # Let's try to login, if 403 then manual verify.
            
            # Actually, let's just make sure we are verifying correctly. 
            # I will use sql helper to verify.
            
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            DATABASE_URL = "sqlite+aiosqlite:///./sb_data/snackbase.db"
            engine = create_async_engine(DATABASE_URL)
            async with engine.begin() as conn:
                await conn.execute(
                    text("UPDATE users SET email_verified = 1 WHERE email = :email"),
                    {"email": admin_email}
                )
            await engine.dispose()

            print("Logging in...")
            resp = await client.post(f"{API_PREFIX}/auth/login", json={
                "email": admin_email,
                "password": admin_password,
                "account": account_slug
            })
            resp.raise_for_status()
            token = resp.json()["token"]
            
            # 2. Create Invitation
            invite_email = f"guest-{unique_id}@test.com"
            print(f"Inviting {invite_email} to {target_account_name}...")
            
            mock_email_service.send_template_email.reset_mock()
            
            resp = await client.post(
                f"{API_PREFIX}/invitations",
                headers={"Authorization": f"Bearer {token}"},
                json={"email": invite_email}
            )
            
            if resp.status_code != 201:
                print(f"Failed to create invitation: {resp.status_code} {resp.text}")
                sys.exit(1)
                
            # 3. Verify Email Service Call
            mock_email_service.send_template_email.assert_called_once()
            call_args = mock_email_service.send_template_email.call_args
            variables = call_args.kwargs.get("variables")
            
            actual_account_name = variables.get("account_name")
            print(f"Email sent with account_name: '{actual_account_name}'")
            
            if actual_account_name == target_account_name:
                print("SUCCESS: Account name matches target account!")
            else:
                print(f"FAILURE: Expected '{target_account_name}', got '{actual_account_name}'")
                sys.exit(1)

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
