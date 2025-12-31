# Creating Custom Hooks

This guide explains how to create custom hooks in SnackBase to extend functionality and automate workflows.

---

## Table of Contents

- [Overview](#overview)
- [Hook System Review](#hook-system-review)
- [Hook Categories](#hook-categories)
- [Step-by-Step Guide](#step-by-step-guide)
- [Hook Context](#hook-context)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

Hooks allow you to **execute custom code** in response to events within SnackBase. They're the primary extension mechanism for adding custom business logic.

### What Can Hooks Do?

| Capability | Example |
|------------|---------|
| **Send Notifications** | Email when record is created |
| **Transform Data** | Auto-generate slugs from titles |
| **Integrate External Services** | Call webhook on record update |
| **Enforce Business Rules** | Prevent deletion of published posts |
| **Audit Changes** | Log all modifications to sensitive fields |
| **Sync Data** | Replicate changes to external systems |

> **Screenshot Placeholder 1**
>
> **Description**: A diagram showing various hook use cases with icons for notifications, transformations, integrations, validations, auditing, and sync.

### Hook System Stability

The hook registration mechanism is a **STABLE API contract** (v1.0). This means:

- ✅ Hook registration syntax won't change in breaking ways
- ✅ Existing hooks will continue to work in future versions
- ✅ New hook types will be additive, not breaking changes

> **Screenshot Placeholder 2**
>
> **Description**: A stability badge or seal showing "Stable API v1.0" with a checkmark.

---

## Hook System Review

### Hook Registration Pattern

Hooks are registered using the `app.hook` decorator:

```python
from src.snackbase.infrastructure.api.app import app

@app.hook.on_record_after_create("posts", priority=10)
async def send_post_notification(record: dict, context: Context):
    """Send notification when post is created."""
    await notification_service.send(
        user_id=record["created_by"],
        message="Your post has been published!"
    )
```

> **Screenshot Placeholder 3**
>
> **Description**: Code showing a hook registration with the decorator syntax and annotations.

### Built-in Hooks

SnackBase includes built-in hooks that **cannot be disabled**:

| Hook | Purpose | Event |
|------|---------|-------|
| `timestamp_hook` | Auto-set `created_at`/`updated_at` | All record operations |
| `account_isolation_hook` | Enforce `account_id` filtering | All record queries |
| `created_by_hook` | Set `created_by` user ID | Record creation |

> **Screenshot Placeholder 4**
>
> **Description**: A table showing built-in hooks with their purposes and trigger events.

---

## Hook Categories

Hooks are organized into **8 categories**:

### 1. App Lifecycle Hooks

| Event | Description | When |
|-------|-------------|------|
| `on_app_startup` | App starts up | Server initialization |
| `on_app_shutdown` | App shuts down | Server shutdown |

### 2. Model Operation Hooks

| Event | Description | When |
|-------|-------------|------|
| `on_model_before_create` | Before model insert | Before database insert |
| `on_model_after_create` | After model insert | After database insert |
| `on_model_before_update` | Before model update | Before database update |
| `on_model_after_update` | After model update | After database update |
| `on_model_before_delete` | Before model delete | Before database delete |
| `on_model_after_delete` | After model delete | After database delete |

### 3. Record Operation Hooks

| Event | Description | When |
|-------|-------------|------|
| `on_record_before_create` | Before record creation | Before inserting dynamic record |
| `on_record_after_create` | After record creation | After inserting dynamic record |
| `on_record_before_update` | Before record update | Before updating dynamic record |
| `on_record_after_update` | After record update | After updating dynamic record |
| `on_record_before_delete` | Before record deletion | Before deleting dynamic record |
| `on_record_after_delete` | After record deletion | After deleting dynamic record |
| `on_record_before_query` | Before querying records | Before executing query |
| `on_record_after_query` | After querying records | After executing query |

### 4. Collection Operation Hooks

| Event | Description | When |
|-------|-------------|------|
| `on_collection_before_create` | Before collection creation | Before creating collection |
| `on_collection_after_create` | After collection creation | After creating collection |
| `on_collection_before_update` | Before collection update | Before updating collection |
| `on_collection_after_update` | After collection update | After updating collection |
| `on_collection_before_delete` | Before collection deletion | Before deleting collection |
| `on_collection_after_delete` | After collection deletion | After deleting collection |

### 5. Auth Operation Hooks

| Event | Description | When |
|-------|-------------|------|
| `on_auth_before_login` | Before login | Before validating credentials |
| `on_auth_after_login` | After login | After successful login |
| `on_auth_before_logout` | Before logout | Before logout processing |
| `on_auth_after_logout` | After logout | After logout processing |
| `on_auth_before_register` | Before registration | Before creating user |
| `on_auth_after_register` | After registration | After creating user |

### 6. User Operation Hooks

| Event | Description | When |
|-------|-------------|------|
| `on_user_before_create` | Before user creation | Before creating user |
| `on_user_after_create` | After user creation | After creating user |
| `on_user_before_update` | Before user update | Before updating user |
| `on_user_after_update` | After user update | After updating user |
| `on_user_before_delete` | Before user deletion | Before deleting user |
| `on_user_after_delete` | After user deletion | After deleting user |

### 7. Request Processing Hooks

| Event | Description | When |
|-------|-------------|------|
| `on_request_before` | Before request processing | At start of request |
| `on_request_after` | After request processing | At end of request |
| `on_request_error` | On request error | When exception occurs |

### 8. Custom Event Hooks

| Event | Description | When |
|-------|-------------|------|
| `on_custom_event` | Custom event | Triggered manually |

> **Screenshot Placeholder 5**
>
> **Description**: A comprehensive table showing all 8 hook categories with their events, descriptions, and timing.

---

## Step-by-Step Guide

Let's create a custom hook that **sends a Slack notification** when a post is published.

### Step 1: Create Hook File

Create hooks in a dedicated file:

```python
# src/snackbase/infrastructure/hooks/custom_hooks.py
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.snackbase.core.context import Context
from src.snackbase.infrastructure.api.app import app
from src.snackbase.core.config import settings

SLACK_WEBHOOK_URL = settings.slack_webhook_url

@app.hook.on_record_after_update("posts", priority=20)
async def notify_slack_on_publish(
    record: dict,
    context: Context,
    old_record: dict | None = None,
    db: AsyncSession = None
):
    """
    Send Slack notification when post status changes to 'published'.

    Trigger: After updating a post record
    Condition: status changed to 'published'
    """
    # Check if status changed to 'published'
    if old_record and record.get("status") == "published":
        if old_record.get("status") != "published":
            await _send_slack_notification(record)

async def _send_slack_notification(post: dict):
    """Send notification to Slack."""
    message = {
        "text": f"New post published: {post.get('title')}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*New Post Published*\n*Title:* {post.get('title')}\n*Author:* <https://example.com|View Post>"
                }
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        await client.post(SLACK_WEBHOOK_URL, json=message)
```

> **Screenshot Placeholder 6**
>
> **Description**: Code showing the complete Slack notification hook with annotations explaining each part.

### Step 2: Import Hooks

Import your hooks file in `app.py` to register them:

```python
# src/snackbase/infrastructure/api/app.py
# ... existing imports

# Import custom hooks (this registers them)
from src.snackbase.infrastructure.hooks.custom_hooks import (
    notify_slack_on_publish,
)

# ... rest of app.py
```

> **Screenshot Placeholder 7**
>
> **Description**: Code showing app.py with the custom hooks import highlighted.

### Step 3: Configure Environment

Add required configuration to `.env`:

```bash
# Slack webhook URL
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

> **Screenshot Placeholder 8**
>
> **Description**: Environment configuration file showing the Slack webhook URL being set.

### Step 4: Test the Hook

```bash
# Update a post to published
curl -X PUT http://localhost:8000/api/v1/posts/post_abc123 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "published"
  }'

# Check Slack for notification
```

> **Screenshot Placeholder 9**
>
> **Description**: Terminal showing curl request and Slack notification appearing in channel.

---

## Hook Context

### Hook Parameters

Hooks receive different parameters based on their type:

```python
@app.hook.on_record_after_create("posts")
async def my_hook(
    record: dict,           # The record being created/updated/deleted
    context: Context,       # Request context (user_id, account_id)
    old_record: dict | None = None,  # Previous state (for updates)
    db: AsyncSession = None,  # Database session (optional)
):
    pass
```

> **Screenshot Placeholder 10**
>
> **Description**: Code showing a hook function with all available parameters and type annotations.

### Context Object

The `context` object provides request information:

```python
class Context:
    user_id: str           # Current user ID
    account_id: str        # Current account ID
    request_id: str        # Correlation ID for tracing
    is_superadmin: bool    # Whether user is superadmin
```

> **Screenshot Placeholder 11**
>
> **Description**: A table showing the Context object fields with descriptions and example values.

---

## Advanced Features

### Priority Control

Hooks execute in priority order (higher priority = earlier execution):

```python
@app.hook.on_record_after_create("posts", priority=100)
async def high_priority_hook(record: dict, context: Context):
    """Executes first."""
    pass

@app.hook.on_record_after_create("posts", priority=10)
async def low_priority_hook(record: dict, context: Context):
    """Executes after high_priority_hook."""
    pass

@app.hook.on_record_after_create("posts", priority=0)
async def default_priority_hook(record: dict, context: Context):
    """Executes last."""
    pass
```

> **Screenshot Placeholder 12**
>
> **Description**: A timeline diagram showing hook execution order based on priority values.

### Conditional Execution

Only execute hooks based on conditions:

```python
@app.hook.on_record_after_update("posts")
async def conditional_hook(
    record: dict,
    context: Context,
    old_record: dict | None = None
):
    """Only execute for specific conditions."""

    # Only if specific field changed
    if old_record and record.get("status") != old_record.get("status"):
        # Status changed
        pass

    # Only for specific account
    if context.account_id == "AB1001":
        # Special handling for this account
        pass

    # Only if specific field value
    if record.get("category") == "urgent":
        # Handle urgent posts
        pass
```

> **Screenshot Placeholder 13**
>
> **Description**: Code showing conditional logic within hooks with different condition examples.

### Error Handling

Handle errors gracefully in hooks:

```python
import logging

logger = logging.getLogger(__name__)

@app.hook.on_record_after_create("posts")
async def safe_hook(record: dict, context: Context):
    """Hook with error handling."""
    try:
        await external_api_call(record)
    except httpx.HTTPError as e:
        # Log error but don't fail the request
        logger.error(f"Hook failed: {e}", exc_info=True)
        # Optionally: send alert
    except Exception as e:
        # Unexpected error
        logger.critical(f"Unexpected hook error: {e}", exc_info=True)
        raise  # Re-raise if critical
```

> **Screenshot Placeholder 14**
>
> **Description**: Code showing error handling in hooks with try/except blocks and logging.

### Aborting Operations

Some `before_*` hooks can abort operations:

```python
from src.snackbase.core.exceptions import HookAbortException

@app.hook.on_record_before_delete("posts")
async def prevent_published_deletion(
    record: dict,
    context: Context
):
    """Prevent deletion of published posts."""
    if record.get("status") == "published":
        raise HookAbortException(
            message="Cannot delete published posts",
            status_code=400
        )
```

> **Screenshot Placeholder 15**
>
> **Description**: Code showing a hook that aborts an operation with a custom error message.

### Async Database Operations

Hooks can perform database operations:

```python
from sqlalchemy import select

@app.hook.on_record_after_create("posts")
async def create_audit_log(
    record: dict,
    context: Context,
    db: AsyncSession
):
    """Create audit log entry."""
    from src.snackbase.infrastructure.persistence.models.audit_log import AuditLog

    log = AuditLog(
        id=generate_id("audit"),
        account_id=context.account_id,
        user_id=context.user_id,
        action="create",
        collection="posts",
        record_id=record["id"],
        changes=record,
        timestamp=datetime.nowUTC()
    )

    db.add(log)
    await db.commit()
```

> **Screenshot Placeholder 16**
>
> **Description**: Code showing a hook performing database operations within the same transaction.

---

## Best Practices

### 1. Keep Hooks Focused

Each hook should do one thing well:

```python
# ❌ BAD: Hook doing too much
@app.hook.on_record_after_create("posts")
async def mega_hook(record: dict, context: Context):
    await send_slack_notification(record)
    await send_email_notification(record)
    await update_search_index(record)
    await create_audit_log(record)
    await invalidate_cache(record)

# ✅ GOOD: Separate, focused hooks
@app.hook.on_record_after_create("posts", priority=50)
async def send_slack_notification(record: dict, context: Context):
    await slack_service.notify(record)

@app.hook.on_record_after_create("posts", priority=40)
async def send_email_notification(record: dict, context: Context):
    await email_service.notify(record)

@app.hook.on_record_after_create("posts", priority=30)
async def update_search_index(record: dict, context: Context):
    await search_service.index(record)
```

> **Screenshot Placeholder 17**
>
> **Description**: Code comparison showing monolithic hook (bad) vs modular hooks (good) with visual indicators.

### 2. Use Priority Wisely

Set appropriate priorities for execution order:

| Priority | Use Case |
|----------|----------|
| 100+ | Critical validation that should run first |
| 50-99 | Core business logic |
| 10-49 | Notifications and integrations |
| 1-9 | Logging and analytics |
| 0 (default) | Cleanup and finalization |

> **Screenshot Placeholder 18**
>
> **Description**: A table showing priority ranges with their recommended use cases.

### 3. Handle Idempotency

Make hooks idempotent when possible:

```python
# ❌ NOT idempotent
@app.hook.on_record_after_create("posts")
async def send_notification(record: dict, context: Context):
    await notification_service.send(record["created_by"], "Post created")
    # Will send duplicate if hook runs twice

# ✅ Idempotent
@app.hook.on_record_after_create("posts")
async def send_notification(record: dict, context: Context):
    await notification_service.send(
        user_id=record["created_by"],
        message=f"Post {record['id']} created",
        deduplication_key=f"post_created:{record['id']}"
    )
```

> **Screenshot Placeholder 19**
>
> **Description**: Code comparison showing non-idempotent (bad) vs idempotent (good) hook patterns.

### 4. Log Hook Execution

Add logging for debugging:

```python
import logging

logger = logging.getLogger(__name__)

@app.hook.on_record_after_create("posts")
async def logged_hook(record: dict, context: Context):
    logger.info(
        "Hook executed",
        extra={
            "hook": "logged_hook",
            "record_id": record.get("id"),
            "user_id": context.user_id,
            "account_id": context.account_id
        }
    )
    # ... hook logic
```

> **Screenshot Placeholder 20**
>
> **Description**: Code showing structured logging in hooks with contextual information.

### 5. Avoid Blocking Operations

Keep hooks fast and non-blocking:

```python
# ❌ BAD: Blocking operation
@app.hook.on_record_after_create("posts")
async def slow_hook(record: dict, context: Context):
    result = await slow_external_api_call(timeout=30)  # Blocks response
    # User waits 30 seconds for response

# ✅ GOOD: Fire and forget
@app.hook.on_record_after_create("posts")
async def fast_hook(record: dict, context: Context):
    # Queue for background processing
    await background_queue.enqueue(
        "slow_operation",
        record_id=record["id"]
    )
    # Returns immediately
```

> **Screenshot Placeholder 21**
>
> **Description**: Code comparison showing blocking (bad) vs non-blocking (good) hook patterns with timing visualization.

### 6. Test Hooks

Write tests for your hooks:

```python
# tests/unit/test_custom_hooks.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_slack_notification_on_publish(db_session, context):
    """Test Slack notification is sent when post is published."""

    # Mock Slack service
    slack_service.send = AsyncMock()

    # Simulate hook execution
    from src.snackbase.infrastructure.hooks.custom_hooks import notify_slack_on_publish

    old_record = {"status": "draft"}
    new_record = {"status": "published", "title": "Test Post"}

    await notify_slack_on_publish(
        record=new_record,
        context=context,
        old_record=old_record,
        db=db_session
    )

    # Verify Slack was called
    slack_service.send.assert_called_once()
```

> **Screenshot Placeholder 22**
>
> **Description**: Code showing a unit test for a hook with mocking and assertions.

---

## Examples

### Example 1: Auto-Generate Slugs

```python
import re

@app.hook.on_record_before_create("posts")
async def generate_slug(
    record: dict,
    context: Context
):
    """Auto-generate slug from title if not provided."""
    if "title" in record and "slug" not in record:
        title = record["title"]
        # Convert to slug
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        record["slug"] = slug
```

> **Screenshot Placeholder 23**
>
> **Description**: Code showing a hook that auto-generates URL slugs from post titles.

### Example 2: Enforce Validation

```python
from src.snackbase.core.exceptions import HookAbortException

@app.hook.on_record_before_create("posts")
async def validate_post_content(
    record: dict,
    context: Context
):
    """Ensure posts have minimum content length."""
    content = record.get("content", "")
    if len(content) < 50:
        raise HookAbortException(
            message="Post content must be at least 50 characters",
            status_code=400
        )
```

> **Screenshot Placeholder 24**
>
> **Description**: Code showing a validation hook that enforces minimum content length.

### Example 3: Sync to External System

```python
import httpx

@app.hook.on_record_after_update("products")
async def sync_to_external_crm(
    record: dict,
    context: Context,
    old_record: dict | None = None
):
    """Sync product changes to external CRM."""
    if old_record:
        # Only sync if fields changed
        changed_fields = [
            k for k in record
            if k in old_record and record[k] != old_record[k]
        ]

        if changed_fields:
            async with httpx.AsyncClient() as client:
                await client.put(
                    f"https://crm.example.com/api/products/{record['id']}",
                    json=record,
                    headers={"Authorization": f"Bearer {settings.crm_api_key}"}
                )
```

> **Screenshot Placeholder 25**
>
> **Description**: Code showing a hook that syncs data changes to an external CRM system.

### Example 4: Track Field Changes

```python
@app.hook.on_record_after_update("users")
async def track_email_changes(
    record: dict,
    context: Context,
    old_record: dict | None = None
):
    """Log when user email changes."""
    if old_record and record.get("email") != old_record.get("email"):
        await audit_service.log(
            user_id=context.user_id,
            action="email_changed",
            details={
                "old_email": old_record.get("email"),
                "new_email": record.get("email")
            }
        )
```

> **Screenshot Placeholder 26**
>
> **Description**: Code showing a hook that tracks and logs changes to a specific field.

---

## Summary

| Concept | Key Takeaway |
|---------|--------------|
| **Hook Categories** | 8 categories: App Lifecycle, Model, Record, Collection, Auth, User, Request, Custom |
| **Registration** | Use `@app.hook.on_event_name()` decorator |
| **Priority** | Higher priority = earlier execution (0-100+) |
| **Context** | Hooks receive record, context, old_record, db parameters |
| **Error Handling** | Log errors, handle gracefully, use HookAbortException to abort |
| **Best Practices** | Keep focused, use priority wisely, ensure idempotency, log execution |

---

## Related Documentation

- [Hooks Reference](../hooks.md) - Complete hook system reference
- [Adding API Endpoints](./adding-api-endpoints.md) - Adding endpoints that trigger hooks
- [Testing Guide](./testing.md) - How to test hooks

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
