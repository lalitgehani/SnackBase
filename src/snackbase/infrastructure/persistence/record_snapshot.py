"""Snapshot of a dynamic record for hook processing.

This mimics the SQLAlchemy model interface enough to be used by the
AuditLogService without requiring a real model class.
"""

from typing import Any


class RecordSnapshot:
    """A detached snapshot of a dynamic record's state.
    
    This class mimics enough of the SQLAlchemy model interface to be used
    by the AuditLogService.
    """
    def __init__(self, table_name: str, record_data: dict[str, Any]):
        """Initialize the snapshot.
        
        Args:
            table_name: The physical table name.
            record_data: Dictionary of record data.
        """
        self.__tablename__ = table_name
        self.__is_snapshot__ = True
        self.primary_key_name = "id"
        
        # Capture all values
        for key, value in record_data.items():
            setattr(self, key, value)
