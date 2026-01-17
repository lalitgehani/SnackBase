from typing import Any, Dict, Optional
import asyncio
from snackbase.core.logging import get_logger
from snackbase.infrastructure.realtime.realtime_manager import ConnectionManager

logger = get_logger(__name__)

class EventBroadcaster:
    """Service for broadcasting data events to subscribers."""
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def publish_event(
        self, 
        account_id: str, 
        collection: str, 
        operation: str, 
        data: Any
    ) -> None:
        """Publish a data event to all authorized subscribers.
        
        Args:
            account_id: The account the event belongs to.
            collection: The collection name.
            operation: The operation (create, update, delete).
            data: The record data.
        """
        try:
            # We don't await this directly to avoid blocking the main request
            # if broadcasting takes time for many subscribers
            asyncio.create_task(
                self.connection_manager.broadcast_to_account(
                    account_id=account_id,
                    collection=collection,
                    operation=operation,
                    data=data
                )
            )
            logger.debug(
                "Event published for broadcast", 
                account_id=account_id, 
                collection=collection, 
                operation=operation
            )
        except Exception as e:
            logger.error(
                "Failed to publish event for broadcast", 
                error=str(e),
                collection=collection,
                operation=operation
            )
