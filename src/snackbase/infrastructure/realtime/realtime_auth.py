from typing import Any, Optional
from fastapi import Request, WebSocket, status, HTTPException
from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import CurrentUser, SYSTEM_ACCOUNT_ID
from snackbase.infrastructure.auth import jwt_service, InvalidTokenError, TokenExpiredError

logger = get_logger(__name__)

async def get_token_from_request(
    request: Optional[Request] = None, 
    websocket: Optional[WebSocket] = None
) -> Optional[str]:
    """Extract token from query parameters or headers."""
    token = None
    
    # Check query parameters (common for WebSockets/SSE)
    if websocket:
        token = websocket.query_params.get("token")
    elif request:
        token = request.query_params.get("token")
        
    if token:
        return token

    # Check headers
    if websocket:
        # Some clients use Sec-WebSocket-Protocol for tokens
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
    session: Optional[Any] = None
) -> CurrentUser:
    """Validate token and return current user."""
    try:
        payload = jwt_service.validate_access_token(token)
        user_id = payload["user_id"]
        
        # In a real implementation, we'd load groups from DB/cache here
        # For simplicity and to avoid circular deps in this file, 
        # we'll assume the payload has what we need or groups is empty for now.
        # The full implementation in dependencies.py handles this better.
        
        return CurrentUser(
            user_id=user_id,
            account_id=payload["account_id"],
            email=payload["email"],
            role=payload["role"],
            groups=payload.get("groups", [])
        )
    except (InvalidTokenError, TokenExpiredError, KeyError) as e:
        logger.info("Realtime authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
