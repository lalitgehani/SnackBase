"""Hook event definitions and categories.

This module defines all hook events that SnackBase supports.
Hook categories and events are part of the stable API contract.

IMPORTANT: Adding new events is allowed (non-breaking), but
           removing or renaming events is a breaking change.
"""


class HookCategory:
    """Categories for organizing hooks.

    Hook categories group related events together. They are used
    for documentation and event discovery.
    """

    APP_LIFECYCLE = "app_lifecycle"
    MODEL_OPERATIONS = "model_operations"
    RECORD_OPERATIONS = "record_operations"
    COLLECTION_OPERATIONS = "collection_operations"
    AUTH_OPERATIONS = "auth_operations"
    REQUEST_PROCESSING = "request_processing"
    REALTIME = "realtime"
    MAILER = "mailer"


class HookEvent:
    """Hook event names.

    All available hook events in SnackBase. Each event follows a
    consistent naming pattern:
    - before_* events can modify data or abort the operation
    - after_* events are called after successful completion

    Attributes in format: ON_<CATEGORY>_<TIMING>_<OPERATION>
    """

    # App Lifecycle Events
    ON_BOOTSTRAP = "on_bootstrap"  # App starting, before serving
    ON_SERVE = "on_serve"  # App ready to serve requests
    ON_TERMINATE = "on_terminate"  # App shutting down

    # Model Operations (internal SQLAlchemy models)
    ON_MODEL_BEFORE_CREATE = "on_model_before_create"
    ON_MODEL_AFTER_CREATE = "on_model_after_create"
    ON_MODEL_BEFORE_UPDATE = "on_model_before_update"
    ON_MODEL_AFTER_UPDATE = "on_model_after_update"
    ON_MODEL_BEFORE_DELETE = "on_model_before_delete"
    ON_MODEL_AFTER_DELETE = "on_model_after_delete"

    # Record Operations (dynamic collection tables)
    ON_RECORD_BEFORE_CREATE = "on_record_before_create"
    ON_RECORD_AFTER_CREATE = "on_record_after_create"
    ON_RECORD_BEFORE_UPDATE = "on_record_before_update"
    ON_RECORD_AFTER_UPDATE = "on_record_after_update"
    ON_RECORD_BEFORE_DELETE = "on_record_before_delete"
    ON_RECORD_AFTER_DELETE = "on_record_after_delete"
    ON_RECORD_BEFORE_QUERY = "on_record_before_query"
    ON_RECORD_AFTER_QUERY = "on_record_after_query"

    # Collection Operations (schema changes)
    ON_COLLECTION_BEFORE_CREATE = "on_collection_before_create"
    ON_COLLECTION_AFTER_CREATE = "on_collection_after_create"
    ON_COLLECTION_BEFORE_UPDATE = "on_collection_before_update"
    ON_COLLECTION_AFTER_UPDATE = "on_collection_after_update"
    ON_COLLECTION_BEFORE_DELETE = "on_collection_before_delete"
    ON_COLLECTION_AFTER_DELETE = "on_collection_after_delete"

    # Auth Operations
    ON_AUTH_BEFORE_LOGIN = "on_auth_before_login"
    ON_AUTH_AFTER_LOGIN = "on_auth_after_login"
    ON_AUTH_BEFORE_LOGOUT = "on_auth_before_logout"
    ON_AUTH_AFTER_LOGOUT = "on_auth_after_logout"
    ON_AUTH_BEFORE_REGISTER = "on_auth_before_register"
    ON_AUTH_AFTER_REGISTER = "on_auth_after_register"
    ON_AUTH_BEFORE_PASSWORD_RESET = "on_auth_before_password_reset"
    ON_AUTH_AFTER_PASSWORD_RESET = "on_auth_after_password_reset"

    # Request Processing
    ON_BEFORE_REQUEST = "on_before_request"
    ON_AFTER_REQUEST = "on_after_request"

    # Realtime Events
    ON_REALTIME_CONNECT = "on_realtime_connect"
    ON_REALTIME_DISCONNECT = "on_realtime_disconnect"
    ON_REALTIME_MESSAGE = "on_realtime_message"
    ON_REALTIME_SUBSCRIBE = "on_realtime_subscribe"
    ON_REALTIME_UNSUBSCRIBE = "on_realtime_unsubscribe"

    # Mailer Events
    ON_MAILER_BEFORE_SEND = "on_mailer_before_send"
    ON_MAILER_AFTER_SEND = "on_mailer_after_send"


# Mapping of events to their categories
EVENT_CATEGORIES: dict[str, str] = {
    # App Lifecycle
    HookEvent.ON_BOOTSTRAP: HookCategory.APP_LIFECYCLE,
    HookEvent.ON_SERVE: HookCategory.APP_LIFECYCLE,
    HookEvent.ON_TERMINATE: HookCategory.APP_LIFECYCLE,
    # Model Operations
    HookEvent.ON_MODEL_BEFORE_CREATE: HookCategory.MODEL_OPERATIONS,
    HookEvent.ON_MODEL_AFTER_CREATE: HookCategory.MODEL_OPERATIONS,
    HookEvent.ON_MODEL_BEFORE_UPDATE: HookCategory.MODEL_OPERATIONS,
    HookEvent.ON_MODEL_AFTER_UPDATE: HookCategory.MODEL_OPERATIONS,
    HookEvent.ON_MODEL_BEFORE_DELETE: HookCategory.MODEL_OPERATIONS,
    HookEvent.ON_MODEL_AFTER_DELETE: HookCategory.MODEL_OPERATIONS,
    # Record Operations
    HookEvent.ON_RECORD_BEFORE_CREATE: HookCategory.RECORD_OPERATIONS,
    HookEvent.ON_RECORD_AFTER_CREATE: HookCategory.RECORD_OPERATIONS,
    HookEvent.ON_RECORD_BEFORE_UPDATE: HookCategory.RECORD_OPERATIONS,
    HookEvent.ON_RECORD_AFTER_UPDATE: HookCategory.RECORD_OPERATIONS,
    HookEvent.ON_RECORD_BEFORE_DELETE: HookCategory.RECORD_OPERATIONS,
    HookEvent.ON_RECORD_AFTER_DELETE: HookCategory.RECORD_OPERATIONS,
    HookEvent.ON_RECORD_BEFORE_QUERY: HookCategory.RECORD_OPERATIONS,
    HookEvent.ON_RECORD_AFTER_QUERY: HookCategory.RECORD_OPERATIONS,
    # Collection Operations
    HookEvent.ON_COLLECTION_BEFORE_CREATE: HookCategory.COLLECTION_OPERATIONS,
    HookEvent.ON_COLLECTION_AFTER_CREATE: HookCategory.COLLECTION_OPERATIONS,
    HookEvent.ON_COLLECTION_BEFORE_UPDATE: HookCategory.COLLECTION_OPERATIONS,
    HookEvent.ON_COLLECTION_AFTER_UPDATE: HookCategory.COLLECTION_OPERATIONS,
    HookEvent.ON_COLLECTION_BEFORE_DELETE: HookCategory.COLLECTION_OPERATIONS,
    HookEvent.ON_COLLECTION_AFTER_DELETE: HookCategory.COLLECTION_OPERATIONS,
    # Auth Operations
    HookEvent.ON_AUTH_BEFORE_LOGIN: HookCategory.AUTH_OPERATIONS,
    HookEvent.ON_AUTH_AFTER_LOGIN: HookCategory.AUTH_OPERATIONS,
    HookEvent.ON_AUTH_BEFORE_LOGOUT: HookCategory.AUTH_OPERATIONS,
    HookEvent.ON_AUTH_AFTER_LOGOUT: HookCategory.AUTH_OPERATIONS,
    HookEvent.ON_AUTH_BEFORE_REGISTER: HookCategory.AUTH_OPERATIONS,
    HookEvent.ON_AUTH_AFTER_REGISTER: HookCategory.AUTH_OPERATIONS,
    HookEvent.ON_AUTH_BEFORE_PASSWORD_RESET: HookCategory.AUTH_OPERATIONS,
    HookEvent.ON_AUTH_AFTER_PASSWORD_RESET: HookCategory.AUTH_OPERATIONS,
    # Request Processing
    HookEvent.ON_BEFORE_REQUEST: HookCategory.REQUEST_PROCESSING,
    HookEvent.ON_AFTER_REQUEST: HookCategory.REQUEST_PROCESSING,
    # Realtime
    HookEvent.ON_REALTIME_CONNECT: HookCategory.REALTIME,
    HookEvent.ON_REALTIME_DISCONNECT: HookCategory.REALTIME,
    HookEvent.ON_REALTIME_MESSAGE: HookCategory.REALTIME,
    HookEvent.ON_REALTIME_SUBSCRIBE: HookCategory.REALTIME,
    HookEvent.ON_REALTIME_UNSUBSCRIBE: HookCategory.REALTIME,
    # Mailer
    HookEvent.ON_MAILER_BEFORE_SEND: HookCategory.MAILER,
    HookEvent.ON_MAILER_AFTER_SEND: HookCategory.MAILER,
}


def get_all_events() -> list[str]:
    """Get all available hook event names."""
    return [
        value
        for name, value in vars(HookEvent).items()
        if not name.startswith("_") and isinstance(value, str)
    ]


def is_before_event(event: str) -> bool:
    """Check if an event is a 'before' event (can modify data/abort)."""
    return "before" in event.lower()


def is_after_event(event: str) -> bool:
    """Check if an event is an 'after' event."""
    return "after" in event.lower()
