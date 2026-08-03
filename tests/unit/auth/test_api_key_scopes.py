"""Unit tests for API-key scope create and propagation."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from snackbase.core.config import get_settings
from snackbase.infrastructure.auth.api_key_service import api_key_service
from snackbase.infrastructure.auth.token_codec import TokenCodec
from snackbase.infrastructure.security.scopes import SCOPE_RECORDS_SECRETS_READ


@pytest.mark.asyncio
async def test_create_api_key_persists_scopes():
    session = AsyncMock()
    session.add = MagicMock()

    plaintext, model = await api_key_service.create_api_key(
        session=session,
        user_id="user-1",
        email="admin@example.com",
        account_id="acc-1",
        role="admin",
        name="Service Key",
        scopes=[SCOPE_RECORDS_SECRETS_READ],
    )

    assert model.scopes == [SCOPE_RECORDS_SECRETS_READ]
    settings = get_settings()
    payload = TokenCodec.decode(plaintext, settings.token_secret)
    assert SCOPE_RECORDS_SECRETS_READ in payload.scopes


@pytest.mark.asyncio
async def test_create_api_key_rejects_unapproved_scope():
    session = AsyncMock()
    session.add = MagicMock()

    with pytest.raises(ValueError, match="Unapproved"):
        await api_key_service.create_api_key(
            session=session,
            user_id="user-1",
            email="admin@example.com",
            account_id="acc-1",
            role="admin",
            name="Bad Key",
            scopes=["cross-account:secrets"],
        )


@pytest.mark.asyncio
async def test_create_api_key_without_scopes():
    session = AsyncMock()
    session.add = MagicMock()

    plaintext, model = await api_key_service.create_api_key(
        session=session,
        user_id="user-1",
        email="admin@example.com",
        account_id="acc-1",
        role="admin",
        name="Plain Key",
    )
    assert model.scopes is None
    settings = get_settings()
    payload = TokenCodec.decode(plaintext, settings.token_secret)
    assert payload.scopes == []
