"""Realtime authentication helpers.

Token extraction reads ``?token=`` for WebSocket connections and the
``Authorization`` header for SSE, unchanged from the original design.

Authentication is delegated to ``Authenticator`` so HTTP and realtime accept
every token type on identical terms.

**Platform token expiry** is evaluated at connection establishment only. An open
socket is not re-validated against ``exp``, because minted platform tokens are
short-lived while subscriptions may last for hours. Exposure is bounded instead
by ``SNACKBASE_PLATFORM_SOCKET_MAX_LIFETIME_SECONDS``, after which the server
closes the connection and the client reconnects with a freshly minted token.
"""

from typing import Any

from fastapi import HTTPException, Request, WebSocket, status

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import CurrentUser
from snackbase.infrastructure.auth.authenticator import Authenticator
from snackbase.infrastructure.auth.token_codec import AuthenticationError

logger = get_logger(__name__)


async def get_token_from_request(
    request: Request | None = None,
    websocket: WebSocket | None = None,
) -> str | None:
    """Extract token from query parameters or headers."""
    token = None

    if websocket:
        token = websocket.query_params.get("token")
    elif request:
        token = request.query_params.get("token")

    if token:
        return token

    if websocket:
        protocol = websocket.headers.get("Sec-WebSocket-Protocol")
        if protocol:
            token = protocol
    elif request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:]

    return token


async def authenticate_realtime(
    token: str,
    session: Any | None = None,
) -> CurrentUser:
    """Validate token through the shared Authenticator and return the current user."""
    authenticator = Authenticator()
    headers = {"Authorization": f"Bearer {token}"}

    try:
        if session is None:
            from snackbase.infrastructure.persistence.database import get_db_manager

            db_manager = get_db_manager()
            async with db_manager.session_factory() as db_session:
                auth_user = await authenticator.authenticate(headers, db_session)
        else:
            auth_user = await authenticator.authenticate(headers, session)
    except AuthenticationError as exc:
        logger.info("Realtime authentication failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    return CurrentUser(
        user_id=auth_user.user_id,
        account_id=auth_user.account_id,
        email=auth_user.email,
        role=auth_user.role,
        token_type=auth_user.token_type,
        groups=auth_user.groups,
        scopes=auth_user.scopes,
        api_key_id=auth_user.api_key_id,
    )
