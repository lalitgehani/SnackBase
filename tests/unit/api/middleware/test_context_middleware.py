import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import Request, Response
from snackbase.infrastructure.api.middleware.context_middleware import ContextMiddleware
from snackbase.infrastructure.auth.token_types import AuthenticatedUser, TokenType
from snackbase.core.context import get_current_context

@pytest.mark.asyncio
async def test_context_middleware_anonymous():
    """Test that context is initialized for anonymous requests."""
    app = MagicMock()
    request = MagicMock(spec=Request)
    request.app = app
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "test-agent"}
    request.state = MagicMock(spec=[]) # Ensure no attributes exist by default
    
    # We need to verify context inside call_next since it's cleared in finally block
    async def side_effect(req):
        context = get_current_context()
        assert context is not None
        assert context.user is None
        assert context.account_id is None
        assert context.ip_address == "127.0.0.1"
        assert context.user_agent == "test-agent"
        return Response()

    call_next = AsyncMock(side_effect=side_effect)
    
    middleware = ContextMiddleware(app)
    await middleware.dispatch(request, call_next)
    
    # Verify it's cleared
    assert get_current_context() is None

@pytest.mark.asyncio
async def test_context_middleware_authenticated():
    """Test that context is enriched for authenticated requests."""
    app = MagicMock()
    request = MagicMock(spec=Request)
    request.app = app
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "test-agent"}
    
    auth_user = AuthenticatedUser(
        user_id="usr_123",
        account_id="acc_456",
        email="test@example.com",
        role="admin",
        token_type=TokenType.JWT
    )
    request.state = MagicMock()
    request.state.authenticated_user = auth_user
    
    async def side_effect(req):
        context = get_current_context()
        assert context is not None
        assert context.user == auth_user
        assert context.account_id == "acc_456"
        assert context.user_name == "test@example.com"
        return Response()

    call_next = AsyncMock(side_effect=side_effect)
    
    middleware = ContextMiddleware(app)
    await middleware.dispatch(request, call_next)
    
    # Verify it's cleared
    assert get_current_context() is None
