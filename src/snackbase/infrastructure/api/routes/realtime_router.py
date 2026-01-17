import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from sse_starlette.sse import EventSourceResponse

from snackbase.core.logging import get_logger
from snackbase.infrastructure.realtime.realtime_auth import authenticate_realtime, get_token_from_request
from snackbase.infrastructure.realtime.realtime_manager import ConnectionManager, RealtimeConnection, Subscription

logger = get_logger(__name__)

router = APIRouter()

def get_manager_from_request(request: Request) -> ConnectionManager:
    """Dependency to get connection manager from request app state."""
    return request.app.state.connection_manager

def get_manager_from_websocket(websocket: WebSocket) -> ConnectionManager:
    """Dependency to get connection manager from websocket app state."""
    return websocket.app.state.connection_manager

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    manager: ConnectionManager = Depends(get_manager_from_websocket)
):
    """WebSocket endpoint for real-time subscriptions."""
    await websocket.accept()
    
    # Authenticate
    token = await get_token_from_request(websocket=websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return
        
    try:
        current_user = await authenticate_realtime(token)
    except Exception as e:
        logger.error("Realtime authentication failed", error=str(e))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return

    connection_id = str(uuid.uuid4())
    
    async def send_callback(data: Any):
        await websocket.send_json(data)

    connection = RealtimeConnection(
        connection_id=connection_id,
        user_id=current_user.user_id,
        account_id=current_user.account_id,
        send_callback=send_callback
    )
    
    await manager.add_connection(connection)
    
    heartbeat_task = None
    
    try:
        # Start heartbeat task
        async def heartbeat():
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception:
                    break
        
        heartbeat_task = asyncio.create_task(heartbeat())
        
        # Main loop for receiving messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    collection = message.get("collection")
                    if not collection:
                        await websocket.send_json({"error": "Missing collection"})
                        continue
                        
                    # Check max subscriptions
                    if len(connection.subscriptions) >= 100:
                        await websocket.send_json({"error": "Max subscriptions reached (100)"})
                        continue
                        
                    sub_id = f"{collection}:{connection_id}"
                    subscription = Subscription(
                        id=sub_id,
                        collection=collection,
                        account_id=current_user.account_id,
                        user_id=current_user.user_id,
                        operations=set(message.get("operations", ["create", "update", "delete"]))
                    )
                    connection.add_subscription(subscription)
                    await websocket.send_json({"status": "subscribed", "collection": collection})
                    
                elif action == "unsubscribe":
                    collection = message.get("collection")
                    sub_id = f"{collection}:{connection_id}"
                    connection.remove_subscription(sub_id)
                    await websocket.send_json({"status": "unsubscribed", "collection": collection})
                
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", connection_id=connection_id)
    except Exception as e:
        logger.error("WebSocket error", connection_id=connection_id, error=str(e))
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
        await manager.remove_connection(connection_id)

@router.get("/subscribe")
async def sse_endpoint(
    request: Request,
    manager: ConnectionManager = Depends(get_manager_from_request)
):
    """SSE endpoint for real-time subscriptions."""
    token = await get_token_from_request(request=request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
        
    try:
        current_user = await authenticate_realtime(token)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid token")

    connection_id = str(uuid.uuid4())
    event_queue = asyncio.Queue()

    async def send_callback(data: Any):
        await event_queue.put(data)

    connection = RealtimeConnection(
        connection_id=connection_id,
        user_id=current_user.user_id,
        account_id=current_user.account_id,
        send_callback=send_callback
    )
    
    await manager.add_connection(connection)

    # Initial subscriptions from query params or simple protocol
    # For SSE, we usually subscribe to everything or specific collections via query params
    collections = request.query_params.getlist("collection")
    for col in collections:
        sub_id = f"{col}:{connection_id}"
        subscription = Subscription(
            id=sub_id,
            collection=col,
            account_id=current_user.account_id,
            user_id=current_user.user_id
        )
        connection.add_subscription(subscription)

    async def event_generator():
        try:
            while True:
                # Check for disconnection
                if await request.is_disconnected():
                    break
                
                try:
                    # Wait for an event with a timeout for heartbeat
                    data = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                    yield {
                        "event": "message",
                        "data": json.dumps(data)
                    }
                except asyncio.TimeoutError:
                    # Heartbeat
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": datetime.now(timezone.utc).isoformat()})
                    }
        finally:
            await manager.remove_connection(connection_id)

    return EventSourceResponse(event_generator())
