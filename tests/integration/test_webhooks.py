"""Integration tests for outbound webhooks (F7.1)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from snackbase.infrastructure.persistence.models.webhook import (
    WebhookDeliveryModel,
    WebhookModel,
)
from snackbase.infrastructure.auth.jwt_service import jwt_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def account(db_session: AsyncSession) -> AccountModel:
    """Create a test account."""
    acc = AccountModel(
        id="00000000-0000-0000-0000-000000000002",
        account_code="WH0001",
        name="Webhook Test Account",
        slug="webhook-test",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


@pytest_asyncio.fixture
async def user_token(db_session: AsyncSession, account: AccountModel) -> str:
    """Create a user in the test account and return their access token."""
    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()

    user = UserModel(
        id="wh-test-user",
        email="user@webhooktest.com",
        account_id=account.id,
        password_hash="hashed",
        role=user_role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()

    token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=user.account_id,
        email=user.email,
        role="user",
    )
    return token


@pytest_asyncio.fixture
async def existing_webhook(db_session: AsyncSession, account: AccountModel) -> WebhookModel:
    """Create an existing webhook for test account."""
    wh = WebhookModel(
        account_id=account.id,
        url="https://example.com/hook",
        collection="posts",
        events=["create", "update"],
        secret="test-secret-abc123",
        enabled=True,
    )
    db_session.add(wh)
    await db_session.commit()
    return wh


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_webhook(client: AsyncClient, user_token: str) -> None:
    """POST /api/v1/webhooks creates a webhook and returns secret once."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "collection": "posts",
            "events": ["create", "update"],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["url"] == "https://example.com/hook"
    assert data["collection"] == "posts"
    assert set(data["events"]) == {"create", "update"}
    assert data["enabled"] is True
    assert "secret" in data  # Secret returned only at creation
    assert len(data["secret"]) > 0


@pytest.mark.asyncio
async def test_create_webhook_auto_generates_secret(
    client: AsyncClient, user_token: str
) -> None:
    """Webhook secret is auto-generated if not provided."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/auto-secret",
            "collection": "orders",
            "events": ["create"],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["secret"]) >= 32  # Auto-generated = 64 hex chars


@pytest.mark.asyncio
async def test_create_webhook_invalid_event(client: AsyncClient, user_token: str) -> None:
    """Invalid event name returns 422."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "collection": "posts",
            "events": ["create", "invalid_event"],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_webhook_http_url_in_production_rejected(
    client: AsyncClient, user_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HTTP URLs are rejected in production."""
    from snackbase.core.config import get_settings

    monkeypatch.setenv("SNACKBASE_ENVIRONMENT", "production")
    get_settings.cache_clear()

    try:
        response = await client.post(
            "/api/v1/webhooks",
            json={
                "url": "http://example.com/hook",
                "collection": "posts",
                "events": ["create"],
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 422
        assert "HTTPS" in response.json()["detail"]
    finally:
        monkeypatch.delenv("SNACKBASE_ENVIRONMENT", raising=False)
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_create_webhook_private_ip_rejected(
    client: AsyncClient, user_token: str
) -> None:
    """Private IP addresses are rejected."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "http://192.168.1.1/hook",
            "collection": "posts",
            "events": ["create"],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 422
    assert "private" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_webhooks(
    client: AsyncClient,
    user_token: str,
    existing_webhook: WebhookModel,
) -> None:
    """GET /api/v1/webhooks lists webhooks for the account."""
    response = await client.get(
        "/api/v1/webhooks",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    ids = [item["id"] for item in data["items"]]
    assert existing_webhook.id in ids
    # Secret must NOT appear in list response
    for item in data["items"]:
        assert "secret" not in item


@pytest.mark.asyncio
async def test_get_webhook(
    client: AsyncClient,
    user_token: str,
    existing_webhook: WebhookModel,
) -> None:
    """GET /api/v1/webhooks/{id} returns webhook details without secret."""
    response = await client.get(
        f"/api/v1/webhooks/{existing_webhook.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == existing_webhook.id
    assert "secret" not in data


@pytest.mark.asyncio
async def test_get_webhook_not_found(client: AsyncClient, user_token: str) -> None:
    """GET /api/v1/webhooks/{id} returns 404 for unknown ID."""
    response = await client.get(
        "/api/v1/webhooks/nonexistent-id",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_webhook(
    client: AsyncClient,
    user_token: str,
    existing_webhook: WebhookModel,
) -> None:
    """PUT /api/v1/webhooks/{id} updates a webhook."""
    response = await client.put(
        f"/api/v1/webhooks/{existing_webhook.id}",
        json={"enabled": False, "events": ["delete"]},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["events"] == ["delete"]


@pytest.mark.asyncio
async def test_delete_webhook(
    client: AsyncClient,
    user_token: str,
    existing_webhook: WebhookModel,
    db_session: AsyncSession,
) -> None:
    """DELETE /api/v1/webhooks/{id} removes the webhook."""
    response = await client.delete(
        f"/api/v1/webhooks/{existing_webhook.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 204

    # Verify it's gone
    result = await db_session.execute(
        select(WebhookModel).where(WebhookModel.id == existing_webhook.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient) -> None:
    """Webhook endpoints require authentication."""
    response = await client.get("/api/v1/webhooks")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Delivery list and test endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_deliveries_empty(
    client: AsyncClient,
    user_token: str,
    existing_webhook: WebhookModel,
) -> None:
    """GET /api/v1/webhooks/{id}/deliveries returns empty list initially."""
    response = await client.get(
        f"/api/v1/webhooks/{existing_webhook.id}/deliveries",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_deliveries_with_records(
    client: AsyncClient,
    user_token: str,
    existing_webhook: WebhookModel,
    db_session: AsyncSession,
) -> None:
    """GET /api/v1/webhooks/{id}/deliveries returns delivery records."""
    # Seed a delivery record
    delivery = WebhookDeliveryModel(
        webhook_id=existing_webhook.id,
        event="records.create",
        payload={"event": "records.create", "collection": "posts", "record": {}},
        status="delivered",
        response_status=200,
        attempt_number=1,
        delivered_at=datetime.now(timezone.utc),
    )
    db_session.add(delivery)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/webhooks/{existing_webhook.id}/deliveries",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "delivered"
    assert data["items"][0]["event"] == "records.create"


@pytest.mark.asyncio
async def test_test_webhook_endpoint(
    client: AsyncClient,
    user_token: str,
    existing_webhook: WebhookModel,
) -> None:
    """POST /api/v1/webhooks/{id}/test sends a test payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"

    with patch(
        "snackbase.infrastructure.webhooks.webhook_service.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_http_client = AsyncMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http_client

        response = await client.post(
            f"/api/v1/webhooks/{existing_webhook.id}/test",
            headers={"Authorization": f"Bearer {user_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status_code"] == 200


@pytest.mark.asyncio
async def test_test_webhook_failure(
    client: AsyncClient,
    user_token: str,
    existing_webhook: WebhookModel,
) -> None:
    """Test webhook endpoint returns success=False on non-2xx response."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch(
        "snackbase.infrastructure.webhooks.webhook_service.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_http_client = AsyncMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http_client

        response = await client.post(
            f"/api/v1/webhooks/{existing_webhook.id}/test",
            headers={"Authorization": f"Bearer {user_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status_code"] == 500


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def test_sign_payload() -> None:
    """HMAC-SHA256 signature is computed correctly."""
    from snackbase.infrastructure.webhooks.webhook_service import sign_payload

    secret = "test-secret"
    body = b'{"event":"records.create"}'
    sig = sign_payload(secret, body)
    assert sig.startswith("sha256=")
    assert len(sig) > 7

    # Verify determinism
    assert sign_payload(secret, body) == sig

    # Different secret → different signature
    assert sign_payload("other-secret", body) != sig


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


def test_validate_url_allows_https() -> None:
    from snackbase.infrastructure.webhooks.webhook_service import validate_webhook_url
    validate_webhook_url("https://example.com/hook", require_https=True)  # no exception


def test_validate_url_rejects_http_in_production() -> None:
    from snackbase.infrastructure.webhooks.webhook_service import validate_webhook_url
    with pytest.raises(ValueError, match="HTTPS"):
        validate_webhook_url("http://example.com/hook", require_https=True)


def test_validate_url_allows_http_in_dev() -> None:
    from snackbase.infrastructure.webhooks.webhook_service import validate_webhook_url
    validate_webhook_url("http://example.com/hook", require_https=False)  # no exception


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/hook",
        "http://10.0.0.1/hook",
        "http://192.168.1.1/hook",
        "http://172.16.0.1/hook",
    ],
)
def test_validate_url_rejects_private_ips(url: str) -> None:
    from snackbase.infrastructure.webhooks.webhook_service import validate_webhook_url
    with pytest.raises(ValueError, match="private"):
        validate_webhook_url(url, require_https=False)


# ---------------------------------------------------------------------------
# Filter evaluation
# ---------------------------------------------------------------------------


def test_filter_evaluation_match() -> None:
    from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter
    record = {"status": "published", "author_id": "user-123"}
    assert _evaluate_filter('status = "published"', record) is True


def test_filter_evaluation_no_match() -> None:
    from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter
    record = {"status": "draft"}
    assert _evaluate_filter('status = "published"', record) is False


def test_filter_evaluation_in_operator() -> None:
    from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter
    record = {"status": "active"}
    assert _evaluate_filter('status IN ("active", "pending")', record) is True
    assert _evaluate_filter('status IN ("inactive", "deleted")', record) is False


def test_filter_evaluation_null() -> None:
    from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter
    record = {"deleted_at": None, "name": "test"}
    assert _evaluate_filter("deleted_at IS NULL", record) is True
    assert _evaluate_filter("name IS NULL", record) is False


def test_filter_evaluation_and_or() -> None:
    from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter
    record = {"status": "published", "score": 10}
    assert _evaluate_filter('status = "published" && score > 5', record) is True
    assert _evaluate_filter('status = "draft" || score > 5', record) is True
    assert _evaluate_filter('status = "draft" && score > 5', record) is False


def test_filter_evaluation_bad_expression_allows_delivery() -> None:
    """Invalid filter expression should not block delivery — default to True."""
    from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter
    record = {"status": "active"}
    # Malformed expression; should return True (allow delivery)
    result = _evaluate_filter("this is not valid @@#$", record)
    assert result is True


def test_filter_evaluation_no_filter_allows_delivery() -> None:
    """Empty filter string allows delivery."""
    from snackbase.infrastructure.webhooks.webhook_service import _evaluate_filter
    # An empty string would fail to parse; should still return True
    result = _evaluate_filter("", {})
    assert result is True


# ---------------------------------------------------------------------------
# Per-account webhook limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_webhooks_per_account(
    client: AsyncClient,
    user_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cannot create more webhooks than the per-account limit."""
    from snackbase.core.config import get_settings

    # Set a very low limit
    monkeypatch.setenv("SNACKBASE_MAX_WEBHOOKS_PER_ACCOUNT", "1")
    get_settings.cache_clear()

    try:
        # Create first webhook — should succeed
        r1 = await client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/1", "collection": "a", "events": ["create"]},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r1.status_code == 201

        # Create second webhook — should be rejected
        r2 = await client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/2", "collection": "b", "events": ["create"]},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r2.status_code == 400
        assert "Maximum" in r2.json()["detail"]
    finally:
        monkeypatch.delenv("SNACKBASE_MAX_WEBHOOKS_PER_ACCOUNT", raising=False)
        get_settings.cache_clear()
