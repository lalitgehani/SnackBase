"""Router for outbound webhook management.

Account-scoped endpoints to create, list, update, delete webhooks and
inspect delivery history.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import AuthenticatedUser, get_db_session
from snackbase.infrastructure.api.schemas.webhook_schemas import (
    WebhookCreateRequest,
    WebhookCreateResponse,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookTestResponse,
    WebhookUpdateRequest,
)
from snackbase.infrastructure.persistence.models.webhook import WebhookModel
from snackbase.infrastructure.persistence.repositories.webhook_repository import (
    WebhookDeliveryRepository,
    WebhookRepository,
)
from snackbase.infrastructure.webhooks.webhook_service import (
    generate_webhook_secret,
    test_webhook,
    validate_webhook_url,
)

router = APIRouter(tags=["Webhooks"])
logger = get_logger(__name__)


def get_webhook_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WebhookRepository:
    """Get the webhook repository."""
    return WebhookRepository(session)


def get_webhook_delivery_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WebhookDeliveryRepository:
    """Get the webhook delivery repository."""
    return WebhookDeliveryRepository(session)


WebhookRepo = Annotated[WebhookRepository, Depends(get_webhook_repository)]
DeliveryRepo = Annotated[WebhookDeliveryRepository, Depends(get_webhook_delivery_repository)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=WebhookCreateResponse,
    summary="Create a new webhook",
)
async def create_webhook(
    data: WebhookCreateRequest,
    current_user: AuthenticatedUser,
    webhook_repo: WebhookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WebhookCreateResponse:
    """Create a new outbound webhook for the current account.

    The `secret` is returned only in this response — store it securely.
    """
    settings = get_settings()

    # Validate URL
    require_https = settings.is_production
    try:
        validate_webhook_url(data.url, require_https=require_https)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

    # Check per-account limit
    count = await webhook_repo.count_by_account(current_user.account_id)
    max_webhooks = getattr(settings, "max_webhooks_per_account", 20)
    if count >= max_webhooks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum number of webhooks per account reached ({max_webhooks})",
        )

    secret = data.secret or generate_webhook_secret()

    webhook = WebhookModel(
        account_id=current_user.account_id,
        url=data.url,
        collection=data.collection,
        events=data.events,
        secret=secret,
        filter=data.filter,
        enabled=data.enabled,
        headers=data.headers,
        created_by=current_user.user_id,
    )
    await webhook_repo.create(webhook)
    await session.commit()

    logger.info(
        "Webhook created",
        webhook_id=webhook.id,
        account_id=webhook.account_id,
        collection=webhook.collection,
    )

    return WebhookCreateResponse(
        id=webhook.id,
        account_id=webhook.account_id,
        url=webhook.url,
        collection=webhook.collection,
        events=webhook.events,
        filter=webhook.filter,
        enabled=webhook.enabled,
        headers=webhook.headers,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        created_by=webhook.created_by,
        secret=secret,
    )


@router.get(
    "",
    response_model=WebhookListResponse,
    summary="List webhooks for the current account",
)
async def list_webhooks(
    current_user: AuthenticatedUser,
    webhook_repo: WebhookRepo,
) -> WebhookListResponse:
    """List all webhooks configured for the current account."""
    webhooks = await webhook_repo.list_by_account(current_user.account_id)
    return WebhookListResponse(
        items=[WebhookResponse.model_validate(w) for w in webhooks],
        total=len(webhooks),
    )


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get webhook details",
)
async def get_webhook(
    webhook_id: str,
    current_user: AuthenticatedUser,
    webhook_repo: WebhookRepo,
) -> WebhookResponse:
    """Get details for a specific webhook."""
    webhook = await webhook_repo.get_by_id_and_account(webhook_id, current_user.account_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return WebhookResponse.model_validate(webhook)


@router.put(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update a webhook",
)
async def update_webhook(
    webhook_id: str,
    data: WebhookUpdateRequest,
    current_user: AuthenticatedUser,
    webhook_repo: WebhookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WebhookResponse:
    """Update a webhook configuration."""
    webhook = await webhook_repo.get_by_id_and_account(webhook_id, current_user.account_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    updates: dict = {k: v for k, v in data.model_dump().items() if v is not None}

    if "url" in updates:
        settings = get_settings()
        try:
            validate_webhook_url(updates["url"], require_https=settings.is_production)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

    if updates:
        await webhook_repo.update(webhook_id, updates)
        await session.commit()

    # Reload after update
    updated = await webhook_repo.get_by_id_and_account(webhook_id, current_user.account_id)
    logger.info("Webhook updated", webhook_id=webhook_id)
    return WebhookResponse.model_validate(updated)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook",
)
async def delete_webhook(
    webhook_id: str,
    current_user: AuthenticatedUser,
    webhook_repo: WebhookRepo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a webhook and all its delivery history."""
    webhook = await webhook_repo.get_by_id_and_account(webhook_id, current_user.account_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    await webhook_repo.delete(webhook_id)
    await session.commit()
    logger.info("Webhook deleted", webhook_id=webhook_id)


@router.get(
    "/{webhook_id}/deliveries",
    response_model=WebhookDeliveryListResponse,
    summary="List delivery history for a webhook",
)
async def list_deliveries(
    webhook_id: str,
    current_user: AuthenticatedUser,
    webhook_repo: WebhookRepo,
    delivery_repo: DeliveryRepo,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> WebhookDeliveryListResponse:
    """List delivery history for a webhook (paginated)."""
    webhook = await webhook_repo.get_by_id_and_account(webhook_id, current_user.account_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    deliveries, total = await delivery_repo.list_by_webhook(webhook_id, limit=limit, offset=offset)
    return WebhookDeliveryListResponse(
        items=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=total,
    )


@router.post(
    "/{webhook_id}/test",
    response_model=WebhookTestResponse,
    summary="Send a test payload to the webhook URL",
)
async def test_webhook_endpoint(
    webhook_id: str,
    current_user: AuthenticatedUser,
    webhook_repo: WebhookRepo,
) -> WebhookTestResponse:
    """Send a test payload to the webhook URL synchronously and return the result."""
    webhook = await webhook_repo.get_by_id_and_account(webhook_id, current_user.account_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    settings = get_settings()
    timeout = getattr(settings, "webhook_timeout_seconds", 30)
    result = await test_webhook(webhook, timeout_seconds=timeout)
    return WebhookTestResponse(**result)
