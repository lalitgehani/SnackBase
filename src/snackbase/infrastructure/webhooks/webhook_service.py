"""Webhook delivery service.

Handles signing, delivery, retry logic, and filter evaluation for outbound webhooks.
"""

import asyncio
import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import urllib.parse
from datetime import UTC, datetime
from typing import Any

import httpx

from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.models.webhook import (
    WebhookDeliveryModel,
    WebhookModel,
)
from snackbase.infrastructure.persistence.repositories.webhook_repository import (
    WebhookDeliveryRepository,
)

logger = get_logger(__name__)

# Retry schedule in seconds: 1min, 5min, 30min, 2hr, 12hr
RETRY_SCHEDULE = [60, 300, 1800, 7200, 43200]

# Private/loopback IP ranges to block in production
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def generate_webhook_secret() -> str:
    """Generate a cryptographically secure webhook secret."""
    return secrets.token_hex(32)


def sign_payload(secret: str, body: bytes) -> str:
    """Compute HMAC-SHA256 signature for a payload.

    Args:
        secret: The webhook signing secret.
        body: Raw JSON bytes to sign.

    Returns:
        Signature string in format "sha256=<hex_digest>".
    """
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def validate_webhook_url(url: str, require_https: bool = True) -> None:
    """Validate a webhook URL.

    Args:
        url: The URL to validate.
        require_https: Whether to require HTTPS (True in production).

    Raises:
        ValueError: If the URL is invalid, insecure, or targets a private IP.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL: {e}") from e

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Webhook URL must use http or https scheme")

    if require_https and parsed.scheme != "https":
        raise ValueError("Webhook URL must use HTTPS in production")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Webhook URL must have a valid hostname")

    # Block private/loopback IPs
    try:
        addr = ipaddress.ip_address(hostname)
        for network in _PRIVATE_NETWORKS:
            if addr in network:
                raise ValueError(
                    f"Webhook URL cannot target private/loopback IP address: {hostname}"
                )
    except ValueError as e:
        # Re-raise if it's our validation error
        if "Webhook URL" in str(e):
            raise
        # Otherwise it's not an IP address (it's a hostname) — that's fine


def _evaluate_filter(filter_expr: str, record: dict[str, Any]) -> bool:
    """Evaluate a rule expression filter against a record dict.

    Uses the existing rule engine parser and walks the AST to evaluate
    the expression in Python against the record fields.

    Args:
        filter_expr: Rule expression string (e.g., 'status = "published"').
        record: Record data as a dict.

    Returns:
        True if the record matches the filter, False otherwise.
    """
    try:
        from snackbase.core.rules.ast import (
            BinaryOp,
            InOp,
            IsNullOp,
            Literal,
            Node,
            UnaryOp,
            Variable,
        )
        from snackbase.core.rules.lexer import Lexer
        from snackbase.core.rules.parser import Parser

        lexer = Lexer(filter_expr)
        parser = Parser(lexer)
        ast = parser.parse()

        def eval_node(node: Node) -> Any:
            if isinstance(node, Literal):
                return node.value

            if isinstance(node, Variable):
                # Only support simple field access (no @ context variables)
                name = node.name
                if name.startswith("@"):
                    # Context variables not supported in webhook filters
                    return None
                return record.get(name)

            if isinstance(node, BinaryOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                op = node.operator
                if op in ("=", "=="):
                    return left == right
                if op in ("!=", "<>"):
                    return left != right
                if op == "<":
                    return _safe_compare(left, right) < 0
                if op == ">":
                    return _safe_compare(left, right) > 0
                if op == "<=":
                    return _safe_compare(left, right) <= 0
                if op == ">=":
                    return _safe_compare(left, right) >= 0
                if op == "~":
                    # LIKE operator: % = wildcard
                    if left is None or right is None:
                        return False
                    pattern = re.escape(str(right)).replace(r"\%", ".*").replace(r"\_", ".")
                    return bool(re.search(f"^{pattern}$", str(left), re.IGNORECASE))
                if op in ("&&", "and", "AND"):
                    return bool(left) and bool(right)
                if op in ("||", "or", "OR"):
                    return bool(left) or bool(right)
                return False

            if isinstance(node, UnaryOp):
                operand = eval_node(node.operand)
                if node.operator in ("!", "not", "NOT"):
                    return not bool(operand)
                return operand

            if isinstance(node, InOp):
                operand = eval_node(node.operand)
                values = [eval_node(v) for v in node.values]
                return operand in values

            if isinstance(node, IsNullOp):
                operand = eval_node(node.operand)
                if node.is_null:
                    return operand is None
                return operand is not None

            return False

        return bool(eval_node(ast))

    except Exception as e:
        logger.warning(
            "Webhook filter evaluation failed — delivering anyway",
            filter=filter_expr,
            error=str(e),
        )
        return True


def _safe_compare(a: Any, b: Any) -> int:
    """Compare two values, returning -1, 0, or 1."""
    try:
        if a < b:
            return -1
        if a > b:
            return 1
        return 0
    except TypeError:
        return 0


async def _send_and_retry(
    delivery_id: str,
    webhook: WebhookModel,
    payload_bytes: bytes,
    delivery_headers: dict[str, str],
    session_factory: Any,
    timeout_seconds: int,
) -> None:
    """Background task: attempt delivery and retry on failure.

    This runs in a background asyncio task and does NOT block the calling request.

    Args:
        delivery_id: ID of the WebhookDeliveryModel to update.
        webhook: The webhook configuration.
        payload_bytes: JSON-encoded payload to send.
        delivery_headers: Headers to send with the request.
        session_factory: Async session factory (db_manager.session).
        timeout_seconds: HTTP request timeout in seconds.
    """
    for attempt, delay in enumerate([0] + RETRY_SCHEDULE):
        if delay > 0:
            await asyncio.sleep(delay)

        attempt_number = attempt + 1
        status_code = None
        response_body = None
        success = False

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    webhook.url,
                    content=payload_bytes,
                    headers=delivery_headers,
                )
                status_code = response.status_code
                response_body = response.text[:5000]
                success = 200 <= status_code < 300

        except Exception as e:
            logger.warning(
                "Webhook delivery attempt failed",
                webhook_id=webhook.id,
                delivery_id=delivery_id,
                attempt=attempt_number,
                error=str(e),
            )
            response_body = str(e)[:5000]

        # Persist attempt result
        async with session_factory() as session:
            delivery_repo = WebhookDeliveryRepository(session)
            if success:
                await delivery_repo.update_status(
                    delivery_id=delivery_id,
                    status="delivered",
                    response_status=status_code,
                    response_body=response_body,
                    delivered_at=datetime.now(UTC),
                    next_retry_at=None,
                    attempt_number=attempt_number,
                )
                await session.commit()
                logger.info(
                    "Webhook delivered",
                    webhook_id=webhook.id,
                    delivery_id=delivery_id,
                    status_code=status_code,
                    attempt=attempt_number,
                )
                return
            else:
                # Determine if there are more retries
                is_last = attempt >= len(RETRY_SCHEDULE)
                next_delay = RETRY_SCHEDULE[attempt] if attempt < len(RETRY_SCHEDULE) else None
                next_retry = (
                    datetime.now(UTC).replace(microsecond=0)
                    if not is_last and next_delay
                    else None
                )
                new_status = "failed" if is_last else "retrying"
                await delivery_repo.update_status(
                    delivery_id=delivery_id,
                    status=new_status,
                    response_status=status_code,
                    response_body=response_body,
                    attempt_number=attempt_number,
                    next_retry_at=next_retry,
                )
                await session.commit()

            if success:
                return

    logger.warning(
        "Webhook exhausted all retries",
        webhook_id=webhook.id,
        delivery_id=delivery_id,
    )


async def dispatch_webhook(
    webhook: WebhookModel,
    event_type: str,
    record: dict[str, Any],
    previous: dict[str, Any] | None,
    session_factory: Any,
    timeout_seconds: int = 30,
) -> str:
    """Create a delivery record and fire it as a background task.

    Args:
        webhook: The webhook configuration.
        event_type: Event name (e.g., "records.create").
        record: The record data after the operation.
        previous: The record data before the operation (update/delete only).
        session_factory: Async session factory for DB access.
        timeout_seconds: HTTP timeout in seconds.

    Returns:
        The delivery ID.
    """
    payload = {
        "event": event_type,
        "collection": webhook.collection,
        "record": record,
        "previous": previous,
        "timestamp": datetime.now(UTC).isoformat(),
        "webhook_id": webhook.id,
        "account_id": webhook.account_id,
    }
    payload_bytes = json.dumps(payload, default=str).encode()
    signature = sign_payload(webhook.secret, payload_bytes)

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-SnackBase-Signature": signature,
        "X-SnackBase-Event": event_type,
        "X-SnackBase-Webhook-Id": webhook.id,
    }
    if webhook.headers:
        headers.update(webhook.headers)

    # Create the delivery record
    delivery = WebhookDeliveryModel(
        webhook_id=webhook.id,
        event=event_type,
        payload=payload,
        status="pending",
        attempt_number=1,
    )

    async with session_factory() as session:
        delivery_repo = WebhookDeliveryRepository(session)
        await delivery_repo.create(delivery)
        await session.commit()
        delivery_id = delivery.id

    # Fire background task — does NOT block the caller
    asyncio.create_task(
        _send_and_retry(
            delivery_id=delivery_id,
            webhook=webhook,
            payload_bytes=payload_bytes,
            delivery_headers=headers,
            session_factory=session_factory,
            timeout_seconds=timeout_seconds,
        )
    )

    return delivery_id


async def test_webhook(
    webhook: WebhookModel,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Send a test payload to the webhook URL synchronously.

    Args:
        webhook: The webhook configuration.
        timeout_seconds: HTTP timeout in seconds.

    Returns:
        Dict with success, status_code, response_body, error keys.
    """
    payload = {
        "event": "test",
        "collection": webhook.collection,
        "record": {"id": "test-record", "example": "data"},
        "previous": None,
        "timestamp": datetime.now(UTC).isoformat(),
        "webhook_id": webhook.id,
        "account_id": webhook.account_id,
    }
    payload_bytes = json.dumps(payload, default=str).encode()
    signature = sign_payload(webhook.secret, payload_bytes)

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-SnackBase-Signature": signature,
        "X-SnackBase-Event": "test",
        "X-SnackBase-Webhook-Id": webhook.id,
    }
    if webhook.headers:
        headers.update(webhook.headers)

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(webhook.url, content=payload_bytes, headers=headers)
            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "response_body": response.text[:5000],
                "error": None,
            }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "response_body": None,
            "error": str(e),
        }
