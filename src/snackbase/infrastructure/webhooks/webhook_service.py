"""Webhook delivery service.

Handles signing, delivery, retry logic, and filter evaluation for outbound webhooks.

Delivery architecture:
- dispatch_webhook(): creates a delivery record and enqueues a job for delivery
- attempt_webhook_delivery(): performs exactly ONE HTTP attempt (used by job handler)
- test_webhook(): one synchronous attempt on behalf of the admin UI

SSRF containment: validate_webhook_url() refuses any destination that resolves into
internal address space, and every outbound request is issued through a transport
pinned to the address that validation approved, so a DNS answer cannot change
between the check and the connect.
"""

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import socket
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

# Ranges the `ipaddress` special-use properties do not flag but that are still
# internal for our purposes. Everything else (loopback, RFC1918, link-local —
# including the 169.254.169.254 cloud metadata endpoint — unspecified, reserved
# and multicast) is recognised by those properties directly.
_EXTRA_BLOCKED_V4_NETWORKS = (
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT (RFC 6598)
    ipaddress.ip_network("198.18.0.0/15"),  # benchmarking (RFC 2544)
)


def generate_webhook_secret() -> str:
    """Generate a cryptographically secure webhook secret."""
    return secrets.token_hex(32)


def resolve_webhook_signing_secret(stored_secret: str) -> str:
    """Return plaintext signing secret from stored value.

    Stored values are Fernet ciphertext after encryption hardening. Legacy
    plaintext rows (pre-migration) are returned as-is when decryption fails.
    """
    from snackbase.core.config import get_settings
    from snackbase.infrastructure.security.encryption import EncryptionService

    service = EncryptionService(get_settings().encryption_key)
    decrypted = service.try_decrypt(stored_secret)
    return decrypted if decrypted is not None else stored_secret


def sign_payload(secret: str, body: bytes) -> str:
    """Compute HMAC-SHA256 signature for a payload.

    Args:
        secret: The webhook signing secret (plaintext).
        body: Raw JSON bytes to sign.

    Returns:
        Signature string in format "sha256=<hex_digest>".
    """
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _is_blocked_address(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Whether an address belongs to internal space and must not be a webhook target.

    IPv4-mapped IPv6 (``::ffff:169.254.169.254``) is unwrapped first: comparing a
    mapped address against IPv4 ranges otherwise yields ``False`` and lets the
    highest-value SSRF targets through.
    """
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped

    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_unspecified
        or addr.is_reserved
        or addr.is_multicast
    ):
        return True

    if isinstance(addr, ipaddress.IPv4Address):
        return any(addr in network for network in _EXTRA_BLOCKED_V4_NETWORKS)

    return False


def _parse_ip_literal(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Return the address if the hostname is an IP literal, else None."""
    try:
        return ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        return None


def _resolve_hostname(hostname: str) -> list[str]:
    """Resolve a hostname to every A/AAAA address, or an empty list if it does not resolve."""
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError:
        return []

    # Preserve order while de-duplicating; strip any IPv6 scope suffix.
    return list(dict.fromkeys(str(info[4][0]).split("%", 1)[0] for info in infos))


def validate_webhook_url(url: str, require_https: bool = True) -> list[str]:
    """Validate a webhook URL and return the addresses it is allowed to reach.

    A hostname is resolved and *every* returned address is checked, so a name
    pointing at internal space cannot slip past a literal-IP-only check. A
    hostname that does not resolve is accepted — the destination simply will not
    connect — which keeps registration usable offline; the binding gate is the
    pinned transport used at send time.

    Args:
        url: The URL to validate.
        require_https: Whether to require HTTPS (True in production).

    Returns:
        The validated IP addresses, or an empty list if the hostname did not resolve.

    Raises:
        ValueError: If the URL is invalid, insecure, or targets internal address space.
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

    literal = _parse_ip_literal(hostname)
    if literal is not None:
        if _is_blocked_address(literal):
            raise ValueError(
                f"Webhook URL cannot target private/loopback IP address: {hostname}"
            )
        return [str(literal)]

    resolved = _resolve_hostname(hostname)
    for candidate in resolved:
        if _is_blocked_address(ipaddress.ip_address(candidate)):
            raise ValueError(
                f"Webhook URL cannot target private/loopback IP address: "
                f"{hostname} resolves to {candidate}"
            )

    return resolved


class _PinnedIPTransport(httpx.AsyncHTTPTransport):
    """Transport that connects only to a pre-validated address.

    Validation resolves the hostname; without pinning, the connect performs a
    second, independent resolution that an attacker-controlled DNS server is free
    to answer differently (DNS rebinding). Rewriting the URL host to the approved
    address closes that window, while the original ``Host`` header and TLS SNI
    keep the request — and certificate validation — addressed to the real name.
    """

    def __init__(self, hostname: str, ip: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._hostname = hostname
        self._ip = ip

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host_header = request.headers.get("Host")
        request.url = request.url.copy_with(host=self._ip)
        if host_header:
            request.headers["Host"] = host_header
        request.extensions["sni_hostname"] = self._hostname
        return await super().handle_async_request(request)


async def _pinned_transport(url: str) -> httpx.AsyncHTTPTransport | None:
    """Re-validate a webhook destination and return a transport pinned to it.

    Validation runs immediately before every send, not just at registration, so a
    DNS record that has since been repointed inward is caught. Returns ``None``
    when there is nothing to pin (an IP literal, or a name that does not resolve).

    Raises:
        ValueError: If the destination is no longer an acceptable webhook target.
    """
    from snackbase.core.config import get_settings

    resolved = await asyncio.to_thread(
        validate_webhook_url, url, get_settings().is_production
    )

    hostname = urllib.parse.urlparse(url).hostname or ""
    if not resolved or _parse_ip_literal(hostname) is not None:
        return None

    return _PinnedIPTransport(hostname, resolved[0])


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


async def attempt_webhook_delivery(
    delivery_id: str,
    url: str,
    secret: str,
    custom_headers: dict[str, str],
    payload_bytes: bytes,
    timeout_seconds: int = 30,
) -> None:
    """Perform exactly one HTTP delivery attempt for a webhook.

    Called by the job handler (webhook_delivery). A single failure raises
    an exception, which the job worker uses to schedule a retry via the
    exponential backoff mechanism.

    On success, updates the delivery record to "delivered".
    On failure, updates the delivery record to "failed" and raises.

    Args:
        delivery_id: ID of the WebhookDeliveryModel to update.
        url: Destination URL.
        secret: HMAC signing secret (used to re-sign for attempt tracking).
        custom_headers: Extra HTTP headers to include.
        payload_bytes: Raw JSON bytes to POST.
        timeout_seconds: HTTP request timeout.

    Raises:
        RuntimeError: On HTTP error, a destination that no longer validates,
            or a non-2xx response.
    """
    from snackbase.infrastructure.persistence.database import get_db_manager

    signature = sign_payload(secret, payload_bytes)
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-SnackBase-Signature": signature,
    }
    headers.update(custom_headers)

    db_manager = get_db_manager()
    status_code = None
    response_body = None
    success = False

    try:
        transport = await _pinned_transport(url)
        async with httpx.AsyncClient(
            timeout=timeout_seconds, transport=transport, follow_redirects=False
        ) as client:
            response = await client.post(url, content=payload_bytes, headers=headers)
            status_code = response.status_code
            response_body = response.text[:5000]
            success = 200 <= status_code < 300
    except Exception as exc:
        response_body = str(exc)[:5000]
        async with db_manager.session() as session:
            delivery_repo = WebhookDeliveryRepository(session)
            await delivery_repo.update_status(
                delivery_id=delivery_id,
                status="failed",
                response_body=response_body,
            )
            await session.commit()
        raise RuntimeError(f"Webhook HTTP request failed: {exc}") from exc

    async with db_manager.session() as session:
        delivery_repo = WebhookDeliveryRepository(session)
        if success:
            await delivery_repo.update_status(
                delivery_id=delivery_id,
                status="delivered",
                response_status=status_code,
                response_body=response_body,
                delivered_at=datetime.now(UTC),
                next_retry_at=None,
            )
        else:
            await delivery_repo.update_status(
                delivery_id=delivery_id,
                status="failed",
                response_status=status_code,
                response_body=response_body,
            )
        await session.commit()

    if not success:
        raise RuntimeError(
            f"Webhook delivery failed with status {status_code}: {response_body[:200]}"
        )

    logger.info("Webhook delivered", delivery_id=delivery_id, url=url, status_code=status_code)


async def dispatch_webhook(
    webhook: WebhookModel,
    event_type: str,
    record: dict[str, Any],
    previous: dict[str, Any] | None,
    session_factory: Any,
    timeout_seconds: int = 30,
) -> str:
    """Create a delivery record and enqueue a job for reliable delivery.

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

    custom_headers: dict[str, str] = {
        "X-SnackBase-Event": event_type,
        "X-SnackBase-Webhook-Id": webhook.id,
    }
    if webhook.headers:
        custom_headers.update(webhook.headers)

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

    # Enqueue a job for reliable delivery with retry support
    from snackbase.infrastructure.services.job_service import JobService

    plaintext_secret = resolve_webhook_signing_secret(webhook.secret)
    job_service = JobService(session_factory)
    await job_service.enqueue(
        handler="webhook_delivery",
        payload={
            "delivery_id": delivery_id,
            "url": webhook.url,
            "secret": plaintext_secret,
            "custom_headers": custom_headers,
            "payload_b64": base64.b64encode(payload_bytes).decode(),
            "timeout_seconds": timeout_seconds,
        },
        queue="webhooks",
        priority=1,
        max_retries=5,
        retry_delay_seconds=60,
        account_id=webhook.account_id,
    )

    return delivery_id


async def test_webhook(
    webhook: WebhookModel,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Send a test payload to the webhook URL synchronously.

    The destination's response body is deliberately **not** returned. Echoing it
    back to the caller would turn any SSRF that got past validation into a read
    primitive against whatever the server can reach; the status code is enough to
    tell an operator whether their endpoint accepted the payload.

    Args:
        webhook: The webhook configuration.
        timeout_seconds: HTTP timeout in seconds.

    Returns:
        Dict with success, status_code, error keys.
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
    plaintext_secret = resolve_webhook_signing_secret(webhook.secret)
    signature = sign_payload(plaintext_secret, payload_bytes)

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-SnackBase-Signature": signature,
        "X-SnackBase-Event": "test",
        "X-SnackBase-Webhook-Id": webhook.id,
    }
    if webhook.headers:
        headers.update(webhook.headers)

    try:
        transport = await _pinned_transport(webhook.url)
        async with httpx.AsyncClient(
            timeout=timeout_seconds, transport=transport, follow_redirects=False
        ) as client:
            response = await client.post(webhook.url, content=payload_bytes, headers=headers)
            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "error": None,
            }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "error": str(e),
        }
