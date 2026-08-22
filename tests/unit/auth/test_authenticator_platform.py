"""Unit tests for platform JWT authentication path (F2.3)."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from tests.helpers.platform_tokens import (
    build_jwks,
    generate_rsa_keypair,
    mint_platform_token,
    platform_settings_env,
)

from snackbase.core.config import Settings, get_settings
from snackbase.infrastructure.auth.authenticator import Authenticator
from snackbase.infrastructure.auth.platform_jwks import reset_platform_jwks_client
from snackbase.infrastructure.auth.token_codec import AuthenticationError
from snackbase.infrastructure.auth.token_types import TokenType


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def authenticator():
    return Authenticator()


@pytest.fixture(autouse=True)
def _reset_platform_client():
    get_settings.cache_clear()
    reset_platform_jwks_client()
    yield
    get_settings.cache_clear()
    reset_platform_jwks_client()


def _enable_platform(monkeypatch, private_key, public_key):
    env = platform_settings_env()
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()

    jwks = build_jwks(public_key)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = jwks
    return patch("snackbase.infrastructure.auth.platform_jwks.httpx.get", return_value=mock_response)


@pytest.mark.asyncio
async def test_valid_rs256_token_maps_claims(authenticator, mock_session, monkeypatch):
    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(
        private_key,
        sub="user-abc",
        email="alice@example.com",
        role="admin",
    )

    with _enable_platform(monkeypatch, private_key, public_key):
        with (
            patch.object(authenticator, "_resolve_platform_user", new=AsyncMock()) as mock_resolve,
            patch.object(authenticator, "_verify_user_account", new=AsyncMock()),
        ):
            mock_user = MagicMock()
            mock_user.id = "user-abc"
            mock_user.account_id = "acct-1"
            mock_user.email = "alice@example.com"
            mock_resolve.return_value = mock_user

            user = await authenticator.authenticate(
                {"Authorization": f"Bearer {token}"},
                session=mock_session,
            )

    assert user.token_type == TokenType.PLATFORM
    assert user.user_id == "user-abc"
    assert user.email == "alice@example.com"
    assert user.role == "admin"


@pytest.mark.asyncio
async def test_hs256_algorithm_confusion_rejected(authenticator, mock_session, monkeypatch):
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": "https://platform.example.com",
            "aud": "snackbase-instance",
            "sub": "user-1",
            "email": "x@example.com",
            "snackbase_role": "admin",
            "iat": now,
            "exp": now + 120,
        },
        "not-the-jwks-public-key-32bytes-min!!",
        algorithm="HS256",
        headers={"kid": "test-key"},
    )

    with _enable_platform(monkeypatch, *generate_rsa_keypair()):
        with pytest.raises(AuthenticationError, match="Unsupported token algorithm"):
            await authenticator.authenticate(
                {"Authorization": f"Bearer {token}"},
                session=mock_session,
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claim_overrides,match",
    [
        ({"issuer": "https://wrong.example.com"}, "Invalid token"),
        ({"audience": "wrong-aud"}, "Invalid token"),
        ({"exp": int(time.time()) - 60}, "expired"),
        ({"iat": int(time.time()) - 600}, "too old"),
    ],
)
async def test_claim_violations_rejected(
    authenticator,
    mock_session,
    monkeypatch,
    claim_overrides,
    match,
):
    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(private_key, **claim_overrides)

    with _enable_platform(monkeypatch, private_key, public_key):
        with patch.object(authenticator, "_resolve_platform_user", new=AsyncMock()) as mock_resolve:
            mock_resolve.return_value = MagicMock(
                id="user-abc", account_id="acct-1", email="alice@example.com"
            )
            with pytest.raises(AuthenticationError, match=match):
                await authenticator.authenticate(
                    {"Authorization": f"Bearer {token}"},
                    session=mock_session,
                )


@pytest.mark.asyncio
async def test_none_algorithm_rejected(authenticator, mock_session, monkeypatch):
    token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL3BsYXRmb3JtLmV4YW1wbGUuY29tIn0."

    with _enable_platform(monkeypatch, *generate_rsa_keypair()):
        with pytest.raises(AuthenticationError):
            await authenticator.authenticate(
                {"Authorization": f"Bearer {token}"},
                session=mock_session,
            )


@pytest.mark.asyncio
async def test_platform_disabled_rejects_structurally_valid_token(
    authenticator, mock_session, monkeypatch
):
    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(private_key)

    with patch("snackbase.infrastructure.auth.authenticator.jwt_service.validate_access_token") as mock_jwt:
        from snackbase.infrastructure.auth.jwt_service import InvalidTokenError

        mock_jwt.side_effect = InvalidTokenError("bad")
        with pytest.raises(AuthenticationError):
            await authenticator.authenticate(
                {"Authorization": f"Bearer {token}"},
                session=mock_session,
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["user", "member", "nonexistent-role", "ADMIN", "admin "])
async def test_non_operator_role_rejected_without_user_creation(
    authenticator, db_session, monkeypatch, role
):
    """Only the exact role `admin` denotes an instance operator. Everything else fails
    closed at the authentication boundary, before any user row is written. Case and
    whitespace variants are rejected too rather than being normalised into an operator."""
    from sqlalchemy import func, select

    from snackbase.infrastructure.persistence.models import UserModel

    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(private_key, role=role, sub="new-user")

    with _enable_platform(monkeypatch, private_key, public_key):
        with pytest.raises(AuthenticationError):
            await authenticator.authenticate(
                {"Authorization": f"Bearer {token}"},
                session=db_session,
            )

    count = (
        await db_session.execute(select(func.count()).select_from(UserModel))
    ).scalar_one()
    assert count == 0


def test_startup_validation_allows_platform_without_single_tenant():
    """Platform auth no longer requires single-tenant mode: principals resolve into the
    system account, so a multi-tenant instance can serve the integrated Studio."""
    settings = Settings(
        platform_issuer="https://platform.example.com",
        platform_jwks_url="https://platform.example.com/jwks",
        platform_audience="snackbase-instance",
        single_tenant_mode=False,
    )
    assert settings.platform_auth_enabled is True
