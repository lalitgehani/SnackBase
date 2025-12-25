"""Unit tests for PermissionResolver service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services import PermissionResolver, PermissionResult
from snackbase.infrastructure.persistence.models import PermissionModel


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def permission_resolver(mock_session):
    """Create a PermissionResolver instance with mocked session."""
    return PermissionResolver(mock_session)


class TestPermissionResolver:
    """Test suite for PermissionResolver."""

    @pytest.mark.asyncio
    async def test_resolve_permission_with_simple_rule(self, permission_resolver, mock_session):
        """Test resolving permission with a simple 'true' rule."""
        # Mock permission repository
        mock_permission = PermissionModel(
            id=1,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "true", "fields": "*"}
            })
        )
        
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[mock_permission]
        ):
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",
                operation="read",
                context={"user": {"id": "user123"}, "record": {}}
            )
        
        assert result.allowed is True
        assert result.fields == "*"

    @pytest.mark.asyncio
    async def test_resolve_permission_deny_by_default(self, permission_resolver):
        """Test deny by default when no permissions exist."""
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[]
        ):
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",
                operation="read",
                context={"user": {"id": "user123"}, "record": {}}
            )
        
        assert result.allowed is False
        assert result.fields == []

    @pytest.mark.asyncio
    async def test_resolve_permission_with_field_list(self, permission_resolver):
        """Test resolving permission with specific field list."""
        mock_permission = PermissionModel(
            id=1,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "true", "fields": ["name", "email"]}
            })
        )
        
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[mock_permission]
        ):
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",
                operation="read",
                context={"user": {"id": "user123"}, "record": {}}
            )
        
        assert result.allowed is True
        assert result.fields == ["name", "email"]

    @pytest.mark.asyncio
    async def test_resolve_permission_multiple_permissions_or_logic(self, permission_resolver):
        """Test multiple permissions for same collection combined with OR logic."""
        # First permission denies
        mock_permission1 = PermissionModel(
            id=1,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "false", "fields": []}
            })
        )
        
        # Second permission allows with specific fields
        mock_permission2 = PermissionModel(
            id=2,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "true", "fields": ["name", "email"]}
            })
        )
        
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[mock_permission1, mock_permission2]
        ):
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",
                operation="read",
                context={"user": {"id": "user123"}, "record": {}}
            )
        
        # Should be allowed because of OR logic
        assert result.allowed is True
        assert result.fields == ["name", "email"]

    @pytest.mark.asyncio
    async def test_resolve_permission_wildcard_collection(self, permission_resolver):
        """Test resolving permission with wildcard collection."""
        mock_permission = PermissionModel(
            id=1,
            role_id=2,
            collection="*",  # Wildcard collection
            rules=json.dumps({
                "read": {"rule": "true", "fields": "*"}
            })
        )
        
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[mock_permission]
        ):
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",  # Specific collection
                operation="read",
                context={"user": {"id": "user123"}, "record": {}}
            )
        
        assert result.allowed is True
        assert result.fields == "*"

    @pytest.mark.asyncio
    async def test_resolve_permission_field_merging(self, permission_resolver):
        """Test that fields from multiple permissions are merged."""
        mock_permission1 = PermissionModel(
            id=1,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "true", "fields": ["name", "email"]}
            })
        )
        
        mock_permission2 = PermissionModel(
            id=2,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "true", "fields": ["phone", "email"]}  # email is duplicate
            })
        )
        
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[mock_permission1, mock_permission2]
        ):
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",
                operation="read",
                context={"user": {"id": "user123"}, "record": {}}
            )
        
        assert result.allowed is True
        # Should have unique fields
        assert set(result.fields) == {"name", "email", "phone"}

    @pytest.mark.asyncio
    async def test_resolve_permission_wildcard_overrides_fields(self, permission_resolver):
        """Test that wildcard fields override specific field lists."""
        mock_permission1 = PermissionModel(
            id=1,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "true", "fields": ["name"]}
            })
        )
        
        mock_permission2 = PermissionModel(
            id=2,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "true", "fields": "*"}  # Wildcard
            })
        )
        
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[mock_permission1, mock_permission2]
        ):
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",
                operation="read",
                context={"user": {"id": "user123"}, "record": {}}
            )
        
        assert result.allowed is True
        assert result.fields == "*"

    @pytest.mark.asyncio
    async def test_resolve_permission_no_operation_rule(self, permission_resolver):
        """Test when permission exists but no rule for requested operation."""
        mock_permission = PermissionModel(
            id=1,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "create": {"rule": "true", "fields": "*"}
                # No "read" rule
            })
        )
        
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[mock_permission]
        ):
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",
                operation="read",  # Requesting read, but only create exists
                context={"user": {"id": "user123"}, "record": {}}
            )
        
        assert result.allowed is False
        assert result.fields == []

    @pytest.mark.asyncio
    async def test_resolve_permission_with_user_context(self, permission_resolver):
        """Test resolving permission with user context in rule."""
        mock_permission = PermissionModel(
            id=1,
            role_id=2,
            collection="customers",
            rules=json.dumps({
                "read": {"rule": "user.id == 'user123'", "fields": "*"}
            })
        )
        
        with patch.object(
            permission_resolver.permission_repo,
            "get_by_role_id",
            return_value=[mock_permission]
        ):
            # Should allow for user123
            result = await permission_resolver.resolve_permission(
                user_id="user123",
                role_id=2,
                collection="customers",
                operation="read",
                context={"user": {"id": "user123"}, "record": {}}
            )
            assert result.allowed is True
            
            # Should deny for user456
            result = await permission_resolver.resolve_permission(
                user_id="user456",
                role_id=2,
                collection="customers",
                operation="read",
                context={"user": {"id": "user456"}, "record": {}}
            )
            assert result.allowed is False
