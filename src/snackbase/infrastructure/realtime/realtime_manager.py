from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Union
import asyncio
from fastapi import WebSocket
from snackbase.core.logging import get_logger

logger = get_logger(__name__)

@dataclass(frozen=True)
class Subscription:
    """Represents a real-time data subscription."""
    id: str
    collection: str
    account_id: str
    user_id: str
    operations: Set[str] = field(default_factory=lambda: {"create", "update", "delete"})
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class RealtimeConnection:
    """Represents an active real-time connection (WebSocket or SSE)."""
    def __init__(
        self, 
        connection_id: str, 
        user_id: str, 
        account_id: str,
        send_callback: Callable[[Any], asyncio.Task]
    ):
        self.id = connection_id
        self.user_id = user_id
        self.account_id = account_id
        self.subscriptions: Dict[str, Subscription] = {}
        self.last_activity = datetime.now(timezone.utc)
        self.send_callback = send_callback

    def add_subscription(self, subscription: Subscription) -> None:
        self.subscriptions[subscription.id] = subscription
        self.last_activity = datetime.now(timezone.utc)

    def remove_subscription(self, subscription_id: str) -> None:
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
        self.last_activity = datetime.now(timezone.utc)

    async def send(self, data: Any) -> None:
        await self.send_callback(data)
        self.last_activity = datetime.now(timezone.utc)

class ConnectionManager:
    """Manages active real-time connections and their subscriptions."""
    def __init__(self):
        self.active_connections: Dict[str, RealtimeConnection] = {}
        self._lock = asyncio.Lock()

    async def add_connection(self, connection: RealtimeConnection) -> None:
        async with self._lock:
            self.active_connections[connection.id] = connection
            logger.info("Realtime connection added", connection_id=connection.id, user_id=connection.user_id)

    async def remove_connection(self, connection_id: str) -> None:
        async with self._lock:
            if connection_id in self.active_connections:
                conn = self.active_connections.pop(connection_id)
                logger.info("Realtime connection removed", connection_id=connection_id, user_id=conn.user_id)

    async def get_connection(self, connection_id: str) -> Optional[RealtimeConnection]:
        return self.active_connections.get(connection_id)

    async def broadcast_to_account(self, account_id: str, collection: str, operation: str, data: Any) -> None:
        """Broadcast an event to all authorized subscribers in an account."""
        async with self._lock:
            connections = list(self.active_connections.values())

        for conn in connections:
            if conn.account_id != account_id:
                continue

            for sub in conn.subscriptions.values():
                if sub.collection == collection and operation in sub.operations:
                    # TODO: Integrate with permission system for granular field-level checks
                    event = {
                        "type": f"{collection}.{operation}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": data
                    }
                    try:
                        await conn.send(event)
                    except Exception as e:
                        logger.error("Failed to send realtime event", 
                                     connection_id=conn.id, error=str(e))
                        # Connection might be dead, let the cleaner handle it or remove it here if vital
