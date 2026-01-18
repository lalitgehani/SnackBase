import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from snackbase.infrastructure.api.middleware.authorization import check_collection_permission
from snackbase.infrastructure.api.dependencies import AuthorizationContext
from snackbase.infrastructure.api.middleware import RuleFilter

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def mock_auth_context():
    auth_ctx = MagicMock(spec=AuthorizationContext)
    auth_ctx.user = MagicMock()
    auth_ctx.user.user_id = "user-123"
    auth_ctx.user.email = "test@example.com"
    auth_ctx.user.role = "user"
    auth_ctx.user.account_id = "acc-123"
    return auth_ctx

@patch("snackbase.infrastructure.api.middleware.authorization.CollectionRuleRepository")
@patch("snackbase.infrastructure.api.middleware.authorization.MacroExpander")
@patch("snackbase.infrastructure.api.middleware.authorization.compile_to_sql")
@pytest.mark.asyncio
async def test_check_collection_permission_calls_expander(
    mock_compile,
    mock_expander_cls,
    mock_rule_repo_cls,
    mock_auth_context,
    mock_session
):
    # Setup
    mock_rule_repo = mock_rule_repo_cls.return_value
    mock_rules = MagicMock()
    mock_rules.view_rule = "@owns_record"
    mock_rules.view_fields = "*"
    mock_rule_repo.get_by_collection_name = AsyncMock(return_value=mock_rules)
    
    mock_expander = mock_expander_cls.return_value
    mock_expander.expand = AsyncMock(return_value="created_by = @request.auth.id")
    
    mock_compile.return_value = ("created_by = :auth_id", {"auth_id": "user-123"})
    
    # Act
    result = await check_collection_permission(
        mock_auth_context, "posts", "view", mock_session
    )
    
    # Assert
    assert isinstance(result, RuleFilter)
    assert result.sql == "created_by = :auth_id"
    
    mock_expander.expand.assert_called_once_with("@owns_record")
    mock_compile.assert_called_once_with("created_by = @request.auth.id", {
        "id": "user-123",
        "email": "test@example.com",
        "role": "user",
        "account_id": "acc-123"
    })

@patch("snackbase.infrastructure.api.middleware.authorization.CollectionRuleRepository")
@patch("snackbase.infrastructure.api.middleware.authorization.MacroExpander")
@pytest.mark.asyncio
async def test_check_collection_permission_expander_error(
    mock_expander_cls,
    mock_rule_repo_cls,
    mock_auth_context,
    mock_session
):
    # Setup
    mock_rule_repo = mock_rule_repo_cls.return_value
    mock_rules = MagicMock()
    mock_rules.view_rule = "@broken"
    mock_rule_repo.get_by_collection_name = AsyncMock(return_value=mock_rules)
    
    mock_expander = mock_expander_cls.return_value
    mock_expander.expand = AsyncMock(side_effect=Exception("Expansion failed"))
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc:
        await check_collection_permission(
            mock_auth_context, "posts", "view", mock_session
        )
    
    assert exc.value.status_code == 500
    assert "macro expansion failed" in exc.value.detail
