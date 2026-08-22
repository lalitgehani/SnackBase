"""Security tests for disabled-by-default platform auth posture (F2.5)."""

import json
from unittest.mock import patch

import pytest
from fastapi import status

from snackbase.core.config import get_settings
from snackbase.infrastructure.auth.platform_jwks import reset_platform_jwks_client
from tests.helpers.platform_tokens import generate_rsa_keypair, mint_platform_token


@pytest.fixture(autouse=True)
def _ensure_platform_disabled(monkeypatch):
    for var in (
        "SNACKBASE_PLATFORM_ISSUER",
        "SNACKBASE_PLATFORM_JWKS_URL",
        "SNACKBASE_PLATFORM_AUDIENCE",
    ):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    reset_platform_jwks_client()
    yield
    get_settings.cache_clear()
    reset_platform_jwks_client()


@pytest.mark.asyncio
async def test_platform_token_rejected_when_unconfigured(client):
    private_key, _ = generate_rsa_keypair()
    token = mint_platform_token(private_key)

    with patch("snackbase.infrastructure.auth.platform_jwks.httpx.get") as mock_get:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        mock_get.assert_not_called()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_health_identical_without_platform_config(client):
    health = await client.get("/health")
    assert health.status_code == status.HTTP_200_OK
    baseline = health.content

    with patch.dict("os.environ", {}, clear=False):
        get_settings.cache_clear()
        health_again = await client.get("/health")
        assert health_again.content == baseline


@pytest.mark.asyncio
async def test_openapi_identical_without_platform_config(client):
    openapi = await client.get("/openapi.json")
    assert openapi.status_code == status.HTTP_200_OK
    baseline = json.dumps(openapi.json(), sort_keys=True)

    get_settings.cache_clear()
    openapi_again = await client.get("/openapi.json")
    assert json.dumps(openapi_again.json(), sort_keys=True) == baseline


@pytest.mark.asyncio
async def test_local_jwt_still_works_without_platform_config(client, superadmin_token):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
