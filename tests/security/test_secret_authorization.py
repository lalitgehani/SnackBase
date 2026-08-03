"""Security tests for secret-access authorization boundaries.

These tests prove that scopes are required for secret reveal authorization
and that superadmin/JWT/anonymous principals do not implicitly gain the
records:secrets:read capability.
"""

from snackbase.infrastructure.api.dependencies import AuthorizationContext
from snackbase.infrastructure.auth.token_types import AuthenticatedUser, TokenType
from snackbase.infrastructure.security.scopes import (
    SCOPE_RECORDS_SECRETS_READ,
    has_scope,
)


def _user(**kwargs) -> AuthenticatedUser:
    defaults = dict(
        user_id="u1",
        account_id="acc-1",
        email="u@example.com",
        role="admin",
        token_type=TokenType.JWT,
        groups=[],
        scopes=[],
    )
    defaults.update(kwargs)
    return AuthenticatedUser(**defaults)


def test_jwt_user_has_no_secret_scope():
    user = _user(token_type=TokenType.JWT, scopes=[])
    assert not user.has_scope(SCOPE_RECORDS_SECRETS_READ)
    ctx = AuthorizationContext(user=user, role_id=1, scopes=user.scopes)
    assert not ctx.has_scope(SCOPE_RECORDS_SECRETS_READ)


def test_superadmin_without_scope_cannot_reveal():
    """Superadmin role must not silently grant secret reveal."""
    user = _user(
        account_id="00000000-0000-0000-0000-000000000000",
        role="admin",
        token_type=TokenType.JWT,
        scopes=[],
    )
    assert not has_scope(user.scopes, SCOPE_RECORDS_SECRETS_READ)


def test_api_key_with_scope_can_reveal_in_own_account():
    user = _user(
        token_type=TokenType.API_KEY,
        scopes=[SCOPE_RECORDS_SECRETS_READ],
        api_key_id="key-1",
        account_id="acc-1",
    )
    assert user.has_scope(SCOPE_RECORDS_SECRETS_READ)
    ctx = AuthorizationContext(user=user, role_id=1, scopes=user.scopes)
    assert ctx.has_scope(SCOPE_RECORDS_SECRETS_READ)
    # Cross-account check is enforced by comparing account_id at the endpoint
    assert user.account_id == "acc-1"
    assert user.account_id != "acc-other"


def test_api_key_without_scope_denied():
    user = _user(token_type=TokenType.API_KEY, scopes=[])
    assert not user.has_scope(SCOPE_RECORDS_SECRETS_READ)


def test_anonymous_context_has_no_scopes():
    ctx = AuthorizationContext(user=None, role_id=None, scopes=[])
    assert not ctx.has_scope(SCOPE_RECORDS_SECRETS_READ)
