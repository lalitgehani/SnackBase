# SnackBase Hook System

**Version**: 1.0 (Stable API)  
**Status**: Production Ready  
**Phase**: 1 - Foundation & MVP

---

## Table of Contents

- [Overview](#overview)
- [Stable API Contract](#stable-api-contract)
- [Architecture](#architecture)
- [Hook Categories](#hook-categories)
- [Hook Events](#hook-events)
- [Usage Guide](#usage-guide)
- [Built-in Hooks](#built-in-hooks)
- [Creating Custom Hooks](#creating-custom-hooks)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)
- [Migration Guide](#migration-guide)

---

## Overview

The SnackBase Hook System is an **extensibility framework** that allows developers to inject custom logic at specific points in the application lifecycle. It provides a stable, event-driven API for extending SnackBase without modifying core code.

### Key Features

- **Event-Driven Architecture**: Subscribe to lifecycle events
- **Priority-Based Execution**: Control hook execution order
- **Tag-Based Filtering**: Target specific collections or resources
- **Before/After Hooks**: Modify data or react to changes
- **Built-in Hooks**: Core functionality (timestamps, account isolation)
- **Abort Capability**: Cancel operations from before hooks
- **Async Support**: Full async/await support
- **Stable API**: Guaranteed backward compatibility

### Use Cases

- **Data Validation**: Custom validation beyond schema rules
- **Data Transformation**: Modify data before save
- **Audit Logging**: Track all changes for compliance
- **Notifications**: Send emails/webhooks on events
- **Access Control**: Custom authorization logic
- **Data Enrichment**: Add computed fields
- **Integration**: Connect to external services
- **Business Logic**: Implement domain-specific rules

---

## Stable API Contract

> **IMPORTANT**: The Hook System API is **stable** and follows semantic versioning. Breaking changes will only occur in major version releases.

### Guaranteed Stability

✅ **Stable (will not change)**:

- `HookRegistry.register()` method signature
- `HookRegistry.trigger()` method signature
- `HookRegistry.unregister()` method signature
- `HookContext` dataclass structure
- `AbortHookException` behavior
- Hook event naming convention
- Priority-based execution order
- Tag-based filtering mechanism
- Built-in hook behavior

✅ **Additive Changes (non-breaking)**:

- New hook events
- New hook categories
- New `HookContext` fields (optional)
- New built-in hooks
- New utility functions

❌ **Breaking Changes (major version only)**:

- Removing hook events
- Renaming hook events
- Changing method signatures
- Removing `HookContext` fields
- Changing execution order logic

### Version Compatibility

| SnackBase Version | Hook API Version | Status    |
| ----------------- | ---------------- | --------- |
| 1.x.x             | 1.0              | ✅ Stable |
| 2.x.x             | 2.0              | 🔮 Future |

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │   Routes   │  │  Services  │  │ Middleware │            │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘            │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│                          ▼                                   │
│              ┌───────────────────────┐                      │
│              │    HookRegistry       │                      │
│              │  (Central Registry)   │                      │
│              └───────────┬───────────┘                      │
│                          │                                   │
│         ┌────────────────┼────────────────┐                 │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Built-in │    │  User    │    │  Plugin  │             │
│  │  Hooks   │    │  Hooks   │    │  Hooks   │             │
│  └──────────┘    └──────────┘    └──────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### Hook Lifecycle

```
1. Event Triggered
   ↓
2. HookRegistry.trigger(event, data, context, filters)
   ↓
3. Filter hooks by event and tags
   ↓
4. Sort hooks by priority (higher = earlier)
   ↓
5. Execute hooks in order
   ↓
6. Handle AbortHookException (if raised)
   ↓
7. Return modified data
```

### Data Flow

```
Before Hooks:
  Input Data → Hook 1 → Hook 2 → Hook 3 → Modified Data

After Hooks:
  Event Occurred → Hook 1 → Hook 2 → Hook 3 → Side Effects
```

---

## Hook Categories

Hooks are organized into **8 categories** for better organization and discovery:

| Category                  | Description                  | Examples                                                    |
| ------------------------- | ---------------------------- | ----------------------------------------------------------- |
| **App Lifecycle**         | Application startup/shutdown | `on_bootstrap`, `on_serve`, `on_terminate`                  |
| **Model Operations**      | Internal SQLAlchemy models   | `on_model_before_create`, `on_model_after_update`           |
| **Record Operations**     | Dynamic collection records   | `on_record_before_create`, `on_record_after_delete`         |
| **Collection Operations** | Schema changes               | `on_collection_before_create`, `on_collection_after_update` |
| **Auth Operations**       | Authentication events        | `on_auth_after_login`, `on_auth_before_register`            |
| **Request Processing**    | HTTP request lifecycle       | `on_before_request`, `on_after_request`                     |
| **Realtime**              | WebSocket/SSE events         | `on_realtime_connect`, `on_realtime_message`                |
| **Mailer**                | Email sending                | `on_mailer_before_send`, `on_mailer_after_send`             |

---

## Hook Events

### Naming Convention

All hook events follow a consistent pattern:

```
on_<category>_<timing>_<operation>

Examples:
- on_record_before_create
- on_auth_after_login
- on_collection_before_delete
```

**Timing**:

- `before_*`: Called before operation (can modify data or abort)
- `after_*`: Called after successful operation (read-only, side effects)

### Complete Event List

#### App Lifecycle

| Event          | Timing   | Description                           |
| -------------- | -------- | ------------------------------------- |
| `on_bootstrap` | Startup  | App starting, before serving requests |
| `on_serve`     | Startup  | App ready to serve requests           |
| `on_terminate` | Shutdown | App shutting down                     |

#### Record Operations (Dynamic Collections)

| Event                     | Timing | Can Modify | Can Abort |
| ------------------------- | ------ | ---------- | --------- |
| `on_record_before_create` | Before | ✅ Yes     | ✅ Yes    |
| `on_record_after_create`  | After  | ❌ No      | ❌ No     |
| `on_record_before_update` | Before | ✅ Yes     | ✅ Yes    |
| `on_record_after_update`  | After  | ❌ No      | ❌ No     |
| `on_record_before_delete` | Before | ❌ No      | ✅ Yes    |
| `on_record_after_delete`  | After  | ❌ No      | ❌ No     |
| `on_record_before_query`  | Before | ✅ Yes     | ✅ Yes    |
| `on_record_after_query`   | After  | ✅ Yes     | ❌ No     |

#### Auth Operations

| Event                           | Timing | Can Modify | Can Abort |
| ------------------------------- | ------ | ---------- | --------- |
| `on_auth_before_login`          | Before | ✅ Yes     | ✅ Yes    |
| `on_auth_after_login`           | After  | ❌ No      | ❌ No     |
| `on_auth_before_register`       | Before | ✅ Yes     | ✅ Yes    |
| `on_auth_after_register`        | After  | ❌ No      | ❌ No     |
| `on_auth_before_logout`         | Before | ❌ No      | ✅ Yes    |
| `on_auth_after_logout`          | After  | ❌ No      | ❌ No     |
| `on_auth_before_password_reset` | Before | ✅ Yes     | ✅ Yes    |
| `on_auth_after_password_reset`  | After  | ❌ No      | ❌ No     |

#### Collection Operations

| Event                         | Timing | Can Modify | Can Abort |
| ----------------------------- | ------ | ---------- | --------- |
| `on_collection_before_create` | Before | ✅ Yes     | ✅ Yes    |
| `on_collection_after_create`  | After  | ❌ No      | ❌ No     |
| `on_collection_before_update` | Before | ✅ Yes     | ✅ Yes    |
| `on_collection_after_update`  | After  | ❌ No      | ❌ No     |
| `on_collection_before_delete` | Before | ❌ No      | ✅ Yes    |
| `on_collection_after_delete`  | After  | ❌ No      | ❌ No     |

> **Note**: Model Operations, Request Processing, Realtime, and Mailer events are defined but not yet triggered in Phase 1. They will be activated in future phases.

---

## Usage Guide

### Accessing the Hook System

The hook registry is available via `app.state.hook_registry`:

```python
from fastapi import FastAPI
from snackbase.core.hooks import HookRegistry

app = FastAPI()

# Access the registry
registry: HookRegistry = app.state.hook_registry
```

### Registering a Hook

#### Method 1: Direct Registration

```python
from snackbase.core.hooks import HookEvent, HookRegistry
from snackbase.domain.entities.hook_context import HookContext

async def my_hook(
    event: str,
    data: dict | None,
    context: HookContext | None
) -> dict | None:
    """Custom hook function."""
    if data:
        data["custom_field"] = "custom_value"
    return data

# Register the hook
registry = app.state.hook_registry
hook_id = registry.register(
    event=HookEvent.ON_RECORD_BEFORE_CREATE,
    callback=my_hook,
    priority=100,  # Higher = runs earlier
    filters={"collection": "posts"},  # Only for 'posts' collection
)
```

#### Method 2: Decorator (Recommended)

```python
from snackbase.core.hooks import HookEvent

@app.state.hook.on(HookEvent.ON_RECORD_BEFORE_CREATE, priority=100)
async def my_hook(event, data, context):
    """Custom hook using decorator."""
    if data:
        data["custom_field"] = "custom_value"
    return data
```

#### Method 3: Collection-Specific Decorator

```python
# Only trigger for 'posts' collection
@app.state.hook.on_record_before_create("posts", priority=100)
async def validate_post(event, data, context):
    """Validate post before creation."""
    if data and len(data.get("title", "")) < 5:
        from snackbase.domain.entities.hook_context import AbortHookException
        raise AbortHookException("Title must be at least 5 characters")
    return data
```

#### Available Decorator Methods

The `HookDecoratorProxy` provides convenient decorator methods for common hook events:

**Record Operations:**

- `on_record_before_create(collection, priority=0)`
- `on_record_after_create(collection, priority=0)`
- `on_record_before_update(collection, priority=0)`
- `on_record_after_update(collection, priority=0)`
- `on_record_before_delete(collection, priority=0)`
- `on_record_after_delete(collection, priority=0)`
- `on_record_before_query(collection, priority=0)`
- `on_record_after_query(collection, priority=0)`

**Collection Operations:**

- `on_collection_before_create(priority=0)`
- `on_collection_after_create(priority=0)`
- `on_collection_before_update(priority=0)`
- `on_collection_after_update(priority=0)`
- `on_collection_before_delete(priority=0)`
- `on_collection_after_delete(priority=0)`

**Auth Operations:**

- `on_auth_before_login(priority=0)`
- `on_auth_after_login(priority=0)`
- `on_auth_before_register(priority=0)`
- `on_auth_after_register(priority=0)`

**Note**: For auth events without dedicated decorator methods (`logout`, `password_reset`), use the generic `on()` method:

```python
@app.state.hook.on(HookEvent.ON_AUTH_BEFORE_LOGOUT, priority=50)
async def before_logout(event, data, context):
    """Handle logout event."""
    return data
```

### Hook Function Signature

All hook functions must follow this signature:

```python
async def hook_function(
    event: str,                      # Event name
    data: dict[str, Any] | None,     # Data being processed
    context: HookContext | None      # Execution context
) -> dict[str, Any] | None:          # Modified data (or None)
    """Hook function."""
    # Your logic here
    return data
```

### HookContext Structure

The `HookContext` provides information about the execution environment:

```python
@dataclass
class HookContext:
    """Context passed to hooks."""

    app: Any                      # FastAPI app instance
    user: Optional["User"]        # Current authenticated user
    account_id: Optional[str]     # Current account ID
    request_id: str               # Request correlation ID (auto-generated)
    request: Optional["Request"]  # FastAPI/Starlette Request object
    ip_address: Optional[str]     # Client IP address (for audit logging)
    user_agent: Optional[str]     # Client user agent (for audit logging)
    user_name: Optional[str]      # User display name (for audit logging)
```

### Aborting Operations

Use `AbortHookException` to cancel an operation from a `before_*` hook:

```python
from snackbase.domain.entities.hook_context import AbortHookException

@app.state.hook.on_record_before_create("posts")
async def validate_post(event, data, context):
    """Prevent spam posts."""
    if data and "spam" in data.get("content", "").lower():
        raise AbortHookException("Spam content detected")
    return data
```

### HookResult Structure

When using `HookRegistry.trigger()` directly (not via decorator), it returns a `HookResult` object containing information about the hook execution:

```python
@dataclass
class HookResult:
    """Result of a hook trigger operation."""

    success: bool                      # Whether all hooks executed successfully
    aborted: bool                      # Whether the operation was aborted by a hook
    abort_message: Optional[str]       # Message from AbortHookException if aborted
    abort_status_code: int             # Status code from AbortHookException (default: 400)
    errors: list[str]                  # List of error messages from hooks that failed
    data: Optional[dict[str, Any]]     # Modified data from the hook chain
```

### Unregistering Hooks

```python
# Save hook ID when registering
hook_id = registry.register(...)

# Later, unregister
success = registry.unregister(hook_id)
```

> **Note**: Built-in hooks cannot be unregistered.

---

## Built-in Hooks

SnackBase includes **4 built-in hooks** that provide core functionality. These hooks are **always active** and cannot be disabled.

### 1. Timestamp Hook

**Purpose**: Automatically set `created_at` and `updated_at` timestamps.

**Events**:

- `on_record_before_create`
- `on_record_before_update`

**Priority**: `-100` (runs early)

**Behavior**:

```python
# On create
data["created_at"] = "2025-12-24T22:00:00Z"
data["updated_at"] = "2025-12-24T22:00:00Z"

# On update
data["updated_at"] = "2025-12-24T22:05:00Z"
```

### 2. Account Isolation Hook

**Purpose**: Enforce multi-tenancy by setting `account_id` from context.

**Events**:

- `on_record_before_create`

**Priority**: `-200` (runs very early)

**Behavior**:

```python
# Automatically set account_id from authenticated user
data["account_id"] = context.account_id
```

### 3. Created By Hook

**Purpose**: Track which user created/updated records.

**Events**:

- `on_record_before_create`
- `on_record_before_update`

**Priority**: `-150` (runs between account isolation and timestamp)

**Behavior**:

```python
# On create
data["created_by"] = context.user.id
data["updated_by"] = context.user.id

# On update
data["updated_by"] = context.user.id
```

### 4. Audit Capture Hook

**Purpose**: Automatically capture audit log entries for record operations.

**Events**:

- `on_record_after_create`
- `on_record_after_update`
- `on_record_after_delete`

**Priority**: `100` (runs after all user hooks)

**Behavior**:

```python
# Captures audit entries with column-level granularity
# Includes user context (user_id, user_email, user_name)
# Includes request context (ip_address, user_agent, request_id)
# Captures old_values for updates
# Handles account_id isolation
# Respects `SNACKBASE_AUDIT_LOGGING_ENABLED` configuration
```

**Notes**:

- Only runs when user context is available (authenticated requests)
- Requires a database session to be passed in the hook data
- Errors are logged but don't fail the main operation
- For model (ORM) events, audit is captured synchronously via SQLAlchemy event listeners
- For record (dynamic collection) events, audit is captured via this async hook

### Built-in Hook Execution Order

```
Priority -200: account_isolation_hook  (set account_id)
    ↓
Priority -150: created_by_hook         (set created_by/updated_by)
    ↓
Priority -100: timestamp_hook          (set timestamps)
    ↓
Priority 0+:   User hooks              (custom logic)
    ↓
Priority 100:  audit_capture_hook      (capture audit logs)
```

---

## Creating Custom Hooks

### Example 1: Data Validation

```python
from snackbase.core.hooks import HookEvent
from snackbase.domain.entities.hook_context import AbortHookException

@app.state.hook.on_record_before_create("products", priority=50)
async def validate_product_price(event, data, context):
    """Ensure product price is positive."""
    if data and data.get("price", 0) <= 0:
        raise AbortHookException("Price must be greater than 0")
    return data
```

### Example 2: Data Transformation

```python
@app.state.hook.on_record_before_create("users", priority=50)
async def normalize_email(event, data, context):
    """Normalize email to lowercase."""
    if data and "email" in data:
        data["email"] = data["email"].lower().strip()
    return data
```

### Example 3: Computed Fields

```python
@app.state.hook.on_record_before_create("orders", priority=50)
async def calculate_total(event, data, context):
    """Calculate order total from line items."""
    if data and "items" in data:
        total = sum(item["price"] * item["quantity"] for item in data["items"])
        data["total"] = total
    return data
```

### Example 4: Audit Logging

```python
import logging

logger = logging.getLogger(__name__)

@app.state.hook.on_record_after_create(priority=50)
async def audit_log_create(event, data, context):
    """Log all record creations for audit."""
    logger.info(
        "Record created",
        collection=context.metadata.get("collection"),
        record_id=data.get("id") if data else None,
        user_id=context.user.id if context.user else None,
        account_id=context.account_id,
    )
    return data
```

### Example 5: Notifications

```python
@app.state.hook.on_record_after_create("orders", priority=50)
async def send_order_notification(event, data, context):
    """Send email notification when order is created."""
    if data:
        # Send email (pseudo-code)
        await send_email(
            to=context.user.email,
            subject="Order Confirmation",
            body=f"Your order {data['id']} has been created."
        )
    return data
```

### Example 6: External Integration

```python
import httpx

@app.state.hook.on_record_after_create("leads", priority=50)
async def sync_to_crm(event, data, context):
    """Sync new leads to external CRM."""
    if data:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://crm.example.com/api/leads",
                json=data,
                headers={"Authorization": f"Bearer {CRM_API_KEY}"}
            )
    return data
```

---

## Advanced Features

### Priority-Based Execution

Hooks execute in **priority order** (higher priority = earlier execution):

```python
# Priority 200 - runs first
@app.state.hook.on_record_before_create("posts", priority=200)
async def hook_1(event, data, context):
    data["step"] = "1"
    return data

# Priority 100 - runs second
@app.state.hook.on_record_before_create("posts", priority=100)
async def hook_2(event, data, context):
    data["step"] = "2"
    return data

# Priority 0 (default) - runs last
@app.state.hook.on_record_before_create("posts")
async def hook_3(event, data, context):
    data["step"] = "3"
    return data
```

**Registration Order**: When multiple hooks have the same priority, they execute in FIFO (first-in-first-out) registration order. The first hook registered with a given priority will execute first among hooks with that priority.

### SQLAlchemy Event Listeners

For model operations (ORM models), hooks are triggered through global SQLAlchemy event listeners registered in `event_listeners.py`. These listeners:

1. **Capture Model State**: Use `ModelSnapshot` to safely capture model state in async contexts without triggering lazy loads
2. **Bridge ORM to Hooks**: Convert SQLAlchemy events into hook registry calls
3. **Handle Async**: Execute async hooks from synchronous SQLAlchemy event listeners using background tasks
4. **Synchronous Audit**: For audit logging, model events are handled synchronously to prevent database lock issues with SQLite

Example of how this works:

```python
# In event_listeners.py
@event.listens_for(ModelClass, "after_update")
def after_update(mapper, connection, target):
    """Called by SQLAlchemy after model update."""
    # Create snapshot for async processing
    snapshot = ModelSnapshot(target)

    # Trigger async hook in background
    task = asyncio.create_task(
        hook_registry.trigger(
            HookEvent.ON_MODEL_AFTER_UPDATE,
            data={"model": snapshot, "old_values": old_values},
            context=get_current_context()
        )
    )
```

### Tag-Based Filtering

Target specific collections or resources:

```python
# Only for 'posts' collection
registry.register(
    event=HookEvent.ON_RECORD_BEFORE_CREATE,
    callback=my_hook,
    filters={"collection": "posts"}
)

# Trigger with matching filter
await registry.trigger(
    event=HookEvent.ON_RECORD_BEFORE_CREATE,
    data=record_data,
    context=hook_context,
    filters={"collection": "posts"}  # Only hooks with this filter will run
)
```

### Error Handling

Hooks can fail without crashing the system:

```python
# Default: errors are logged but don't stop execution
registry.register(
    event=HookEvent.ON_RECORD_AFTER_CREATE,
    callback=my_hook,
    stop_on_error=False  # Default
)

# Optional: stop execution on error
registry.register(
    event=HookEvent.ON_RECORD_BEFORE_CREATE,
    callback=critical_validation,
    stop_on_error=True  # Raise exception if hook fails
)
```

### Conditional Execution

```python
@app.state.hook.on_record_before_create("posts")
async def conditional_hook(event, data, context):
    """Only run for specific users."""
    if context.user and context.user.role == "admin":
        data["admin_approved"] = True
    return data
```

### Chaining Hooks

Hooks can modify data sequentially:

```python
# Hook 1: Normalize
@app.state.hook.on_record_before_create("posts", priority=100)
async def normalize(event, data, context):
    if data:
        data["title"] = data["title"].strip()
    return data

# Hook 2: Validate (runs after normalize)
@app.state.hook.on_record_before_create("posts", priority=50)
async def validate(event, data, context):
    if data and len(data["title"]) < 5:
        raise AbortHookException("Title too short")
    return data

# Hook 3: Enrich (runs after validate)
@app.state.hook.on_record_before_create("posts", priority=25)
async def enrich(event, data, context):
    if data:
        data["slug"] = data["title"].lower().replace(" ", "-")
    return data
```

---

## Best Practices

### 1. Use Descriptive Names

```python
# ❌ Bad
async def hook1(event, data, context):
    pass

# ✅ Good
async def validate_email_format(event, data, context):
    pass
```

### 2. Keep Hooks Focused

```python
# ❌ Bad - does too much
async def mega_hook(event, data, context):
    validate_data(data)
    send_email(data)
    update_cache(data)
    log_to_analytics(data)
    return data

# ✅ Good - single responsibility
async def validate_data_hook(event, data, context):
    validate_data(data)
    return data

async def send_email_hook(event, data, context):
    send_email(data)
    return data
```

### 3. Use Appropriate Priorities

```python
# Validation: High priority (runs early)
@app.state.hook.on_record_before_create("posts", priority=100)
async def validate(event, data, context):
    pass

# Enrichment: Medium priority
@app.state.hook.on_record_before_create("posts", priority=50)
async def enrich(event, data, context):
    pass

# Side effects: Low priority (runs late)
@app.state.hook.on_record_after_create("posts", priority=10)
async def notify(event, data, context):
    pass
```

### 4. Handle Errors Gracefully

```python
@app.state.hook.on_record_after_create("posts")
async def send_notification(event, data, context):
    """Send notification, but don't fail if it errors."""
    try:
        await send_email(data)
    except Exception as e:
        logger.error("Failed to send notification", error=str(e))
    return data
```

### 5. Use Type Hints

```python
from typing import Any, Optional
from snackbase.domain.entities.hook_context import HookContext

@app.state.hook.on_record_before_create("posts")
async def my_hook(
    event: str,
    data: Optional[dict[str, Any]],
    context: Optional[HookContext]
) -> Optional[dict[str, Any]]:
    """Well-typed hook function."""
    return data
```

### 6. Document Your Hooks

```python
@app.state.hook.on_record_before_create("posts", priority=100)
async def validate_post_content(event, data, context):
    """Validate post content before creation.

    Checks:
    - Title length (min 5 chars)
    - Content length (min 10 chars)
    - No spam keywords

    Raises:
        AbortHookException: If validation fails
    """
    # Implementation
    pass
```

### 7. Test Your Hooks

```python
import pytest
from snackbase.domain.entities.hook_context import HookContext

@pytest.mark.asyncio
async def test_validate_post_content():
    """Test post validation hook."""
    # Arrange
    data = {"title": "Hi", "content": "Short"}
    context = HookContext()

    # Act & Assert
    with pytest.raises(AbortHookException):
        await validate_post_content("on_record_before_create", data, context)
```

---

## Migration Guide

### Future Compatibility

When upgrading to future versions of SnackBase:

1. **Check changelog** for new hook events
2. **Review deprecation warnings** in logs
3. **Test hooks** in staging environment
4. **Update hook priorities** if new built-in hooks are added

### Adding New Events (Future)

New hook events will be added in future phases. Your existing hooks will continue to work unchanged.

Example future events:

- `on_file_before_upload`
- `on_webhook_before_send`
- `on_permission_check`

### Versioning Policy

- **Minor versions** (1.1, 1.2): New events, new features (backward compatible)
- **Major versions** (2.0, 3.0): Breaking changes (rare)

---

## API Reference

### HookRegistry

```python
class HookRegistry:
    def register(
        self,
        event: str,
        callback: Callable,
        filters: Optional[dict[str, Any]] = None,
        priority: int = 0,
        stop_on_error: bool = False,
        is_builtin: bool = False,
    ) -> str:
        """Register a hook."""

    async def trigger(
        self,
        event: str,
        data: Optional[dict[str, Any]] = None,
        context: Optional[HookContext] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute all hooks for an event."""

    def unregister(self, hook_id: str) -> bool:
        """Remove a registered hook."""

    def get_hooks_for_event(self, event: str) -> list[RegisteredHook]:
        """Get all hooks for an event."""
```

### HookContext

```python
@dataclass
class HookContext:
    """Context passed to all hook callbacks."""
    app: Any
    user: Optional["User"] = None
    account_id: Optional[str] = None
    request_id: str = ""
    request: Optional["Request"] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    user_name: Optional[str] = None
```

### HookResult

```python
@dataclass
class HookResult:
    """Result of a hook trigger operation."""
    success: bool = True
    aborted: bool = False
    abort_message: Optional[str] = None
    abort_status_code: int = 400
    errors: list[str] = field(default_factory=list)
    data: Optional[dict[str, Any]] = None
```

### AbortHookException

```python
class AbortHookException(Exception):
    """Raise to abort an operation from a before hook."""
    pass
```

---

## Support

For questions and issues:

- **Documentation**: [repository]/docs/hooks.md
- **Examples**: [repository]/examples/hooks/
- **GitHub Issues**: [repository]/issues
- **Community**: [community-link]

---

## Changelog

### Version 1.0 (Phase 1)

- ✅ Initial stable release
- ✅ HookRegistry with register/trigger/unregister
- ✅ 8 hook categories defined
- ✅ 40+ hook events defined
- ✅ Priority-based execution
- ✅ Tag-based filtering
- ✅ Built-in hooks (timestamp, account_isolation, created_by, audit_capture)
- ✅ AbortHookException for canceling operations
- ✅ Decorator-based registration
- ✅ Full async support
- ✅ SQLAlchemy event listeners for model operations
- ✅ HookContext with IP address, user agent, and user name fields
- ✅ HookResult class for trigger operation results

### Future Versions

- 🔮 Hook middleware for request processing
- 🔮 Hook metrics and monitoring
- 🔮 Hook debugging tools
- 🔮 Visual hook flow diagram in admin UI
