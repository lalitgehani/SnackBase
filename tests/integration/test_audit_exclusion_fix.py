import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from snackbase.infrastructure.persistence.models import (
    AccountModel, 
    RefreshTokenModel,
    AuditLogModel,
    ConfigurationModel
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    RefreshTokenRepository,
    ConfigurationRepository
)
from snackbase.core.context import set_current_context, HookContext
from snackbase.infrastructure.persistence.models.user import UserModel

@pytest.mark.asyncio
@pytest.mark.enable_audit_hooks
class TestAuditExclusion:
    """Integration tests to verify audit logging exclusion and masking."""

    @pytest.fixture(autouse=True)
    def setup_context(self):
        """Set a default context for all tests."""
        # Mock user and context
        mock_user = UserModel(id=str(uuid.uuid4()), email="admin@example.com")
        context = HookContext(
            app=None,
            request_id=str(uuid.uuid4()),
            user=mock_user,
            account_id="00000000-0000-0000-0000-000000000000"
        )
        set_current_context(context)
        yield
        set_current_context(None)

    async def test_refresh_token_exclusion(self, db_session: AsyncSession):
        """Verify that operations on refresh_tokens table are NOT audited."""
        # 1. Setup account and user
        account = AccountModel(
            id=str(uuid.uuid4()), 
            account_code="AC" + str(uuid.uuid4().int)[:4].zfill(4), 
            name="Test Token Account", 
            slug="test-token-" + str(uuid.uuid4().hex)[:6]
        )
        db_session.add(account)
        await db_session.flush()

        from snackbase.infrastructure.persistence.repositories import RoleRepository
        role_repo = RoleRepository(db_session)
        admin_role = await role_repo.get_by_name("admin")
        
        user_model = UserModel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            email=f"token-user-{uuid.uuid4().hex[:6]}@example.com",
            password_hash="hash",
            role_id=admin_role.id
        )
        db_session.add(user_model)
        await db_session.commit()
        
        # 2. Create a refresh token
        repo = RefreshTokenRepository(db_session)
        token_model = RefreshTokenModel(
            id=str(uuid.uuid4()),
            token_hash=f"test-hash-{uuid.uuid4().hex[:6]}",
            user_id=user_model.id,
            account_id=account.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        await repo.create(token_model)
        await db_session.commit()

        # 3. Check audit logs
        result = await db_session.execute(
            select(AuditLogModel).where(AuditLogModel.table_name == "refresh_tokens")
        )
        logs = result.scalars().all()
        
        assert len(logs) == 0, f"Expected 0 audit logs for refresh_tokens, found {len(logs)}"

    async def test_oauth_state_exclusion(self, db_session: AsyncSession):
        """Verify that operations on oauth_states table are NOT audited."""
        from snackbase.infrastructure.persistence.models.configuration import OAuthStateModel
        
        # 1. Create an OAuth state
        state = OAuthStateModel(
            id=str(uuid.uuid4()),
            provider_name="google",
            state_token=f"secret-state-{uuid.uuid4().hex[:6]}",
            redirect_uri="http://localhost/callback",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
        )
        db_session.add(state)
        await db_session.commit()

        # 2. Check audit logs
        result = await db_session.execute(
            select(AuditLogModel).where(AuditLogModel.table_name == "oauth_states")
        )
        logs = result.scalars().all()
        
        assert len(logs) == 0, f"Expected 0 audit logs for oauth_states, found {len(logs)}"

    async def test_sensitive_field_masking(self, db_session: AsyncSession):
        """Verify that sensitive fields are masked in audit logs."""
        # 1. Setup account
        account_id = str(uuid.uuid4())
        account = AccountModel(
            id=account_id, 
            account_code="AC" + str(uuid.uuid4().int)[:4].zfill(4), 
            name="Test Masking", 
            slug="test-masking-" + str(uuid.uuid4().hex)[:6]
        )
        db_session.add(account)
        await db_session.flush()

        # 2. Extract admin role
        from snackbase.infrastructure.persistence.repositories import RoleRepository
        role_repo = RoleRepository(db_session)
        admin_role = await role_repo.get_by_name("admin")
    
        # 3. Create user with sensitive field
        user_id = str(uuid.uuid4())
        user = UserModel(
            id=user_id,
            account_id=account_id,
            email=f"test-{user_id}@example.com",
            password_hash="SECRET_HASH",
            role_id=admin_role.id
        )
        db_session.add(user)
        await db_session.commit()

        # 4. Check audit logs for 'password_hash' column
        result = await db_session.execute(
            select(AuditLogModel).where(
                AuditLogModel.table_name == "users",
                AuditLogModel.column_name == "password_hash",
                AuditLogModel.record_id == user_id
            )
        )
        logs = result.scalars().all()
        
        assert len(logs) > 0, "Expected audit log for user creation (password_hash column)"
        for log in logs:
            assert log.new_value == "***", f"Expected masked password_hash, found {log.new_value}"
