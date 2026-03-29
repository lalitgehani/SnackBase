"""Cursor utilities for cursor-based pagination."""

import base64
import json
from typing import Any


class CursorError(Exception):
    """Raised when cursor is invalid or malformed."""


def encode_cursor(sort_value: Any, record_id: str) -> str:
    """Encode a cursor from sort value and record ID.

    Args:
        sort_value: The value of the sort field for this record
        record_id: The record ID (used as tie-breaker)

    Returns:
        Base64-encoded cursor string
    """
    cursor_data = {
        "sort_value": sort_value,
        "id": record_id,
    }
    json_str = json.dumps(cursor_data, separators=(",", ":"), default=str)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> tuple[Any, str]:
    """Decode a cursor to get sort value and record ID.

    Args:
        cursor: Base64-encoded cursor string

    Returns:
        Tuple of (sort_value, record_id)

    Raises:
        CursorError: If cursor is invalid
    """
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        cursor_data = json.loads(json_str)
        sort_value = cursor_data["sort_value"]
        record_id = cursor_data["id"]
        return sort_value, record_id
    except (ValueError, KeyError, TypeError) as e:
        raise CursorError(f"Invalid cursor format: {e}") from e