"""Structured JSON logging with correlation IDs.

This module configures structlog for structured JSON logging with
correlation ID tracking for request tracing.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from snackbase.core.config import get_settings


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID to log entry if present in context.

    Args:
        logger: Logger instance (unused).
        method_name: Method name (unused).
        event_dict: Event dictionary to modify.

    Returns:
        EventDict: Modified event dictionary with correlation_id.
    """
    # Correlation ID should be added to context via middleware
    # If not present, generate a temporary one for this log entry
    if "correlation_id" not in event_dict:
        # Only generate if not already set by context
        import uuid

        event_dict["correlation_id"] = f"cid_{uuid.uuid4().hex[:12]}"
    return event_dict


def add_logger_name(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add logger name to log entry.

    Args:
        logger: Logger instance.
        method_name: Method name (unused).
        event_dict: Event dictionary to modify.

    Returns:
        EventDict: Modified event dictionary with logger name.
    """
    event_dict["logger"] = logger.name if hasattr(logger, "name") else "snackbase"
    return event_dict


def rename_message_field(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Rename 'event' field to 'message' for compatibility.

    Args:
        logger: Logger instance (unused).
        method_name: Method name (unused).
        event_dict: Event dictionary to modify.

    Returns:
        EventDict: Modified event dictionary with message field.
    """
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def configure_logging(settings: Any | None = None) -> None:
    """Configure structured logging for the application.

    Sets up structlog with JSON formatting for production and
    console formatting for development.

    Args:
        settings: Optional settings instance. If not provided, will load from environment.
    """
    if settings is None:
        settings = get_settings()

    # Shared processors for all logging
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        # Note: structlog.stdlib.add_logger_name doesn't work with PrintLogger
        # We use add_logger_name which has a fallback
        add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_correlation_id,
        rename_message_field,
    ]

    # Development mode: console output with colors
    if settings.is_development or settings.log_format == "console":
        # Configure structlog for console output
        structlog.configure(
            processors=shared_processors
            + [
                structlog.dev.ConsoleRenderer(
                    colors=True,
                    exception_formatter=structlog.dev.plain_traceback,
                ),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.log_level)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=False,
        )

        # Configure standard logging for third-party libraries
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, settings.log_level),
        )

    # Production mode: JSON output
    else:
        # Configure structlog for JSON output
        structlog.configure(
            processors=shared_processors
            + [
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.log_level)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure standard logging for third-party libraries
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, settings.log_level),
            handlers=[logging.StreamHandler(sys.stdout)],
        )

        # Configure uvicorn logging to use structlog
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            logging.getLogger(logger_name).setLevel(getattr(logging, settings.log_level))


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Optional logger name. If not provided, uses 'snackbase'.

    Returns:
        BoundLogger: Configured structured logger instance.
    """
    return structlog.get_logger(name or "snackbase")


class LoggingContext:
    """Context manager for adding logging context.

    This is useful for adding request-specific context to all log entries
    within a scope (e.g., a request handler).

    Example:
        with LoggingContext(correlation_id="abc123", user_id="user456"):
            logger.info("Processing request")  # Will include correlation_id and user_id
    """

    def __init__(self, **kwargs: str) -> None:
        """Initialize logging context with key-value pairs.

        Args:
            **kwargs: Key-value pairs to add to logging context.
        """
        self.context = kwargs
        self.token: structlog.contextvars._ContextToken | None = None

    def __enter__(self) -> "LoggingContext":
        """Enter the context and add context variables."""
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the context and clear context variables."""
        if self.token is not None:
            structlog.contextvars.unbind_contextvars(*self.context.keys())


def bind_correlation_id(correlation_id: str) -> None:
    """Bind a correlation ID to the current logging context.

    This is typically called by request middleware to add the correlation
    ID from the request headers or generate a new one.

    Args:
        correlation_id: The correlation ID to bind to the context.
    """
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def clear_context() -> None:
    """Clear all context variables from the current logging context.

    This is typically called at the end of a request to ensure
    context doesn't leak between requests.
    """
    structlog.contextvars.clear_contextvars()
