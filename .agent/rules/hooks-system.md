---
trigger: model_decision
description: Hook system patterns and stable API contract - apply when implementing hooks or lifecycle events
---

# Hook System Rules

## STABLE API CONTRACT

The hook registry is a **stable API contract**. Changing the registration mechanism would be a breaking change.

## Hook Registration Pattern

```python
# Hook registration (decorator syntax)
@app.hook.on_record_after_create("posts", priority=10)
async def send_post_notification(record, context):
    await notification_service.send(record.created_by, "Post created!")
```

## Built-in Hooks (Cannot Be Unregistered)

Phase 1:

- `timestamp_hook`
- `account_isolation_hook`

Phase 2:

- `permission_check_hook`
- `pii_masking_hook`

Phase 3:

- `audit_log_hook`

## Hook Categories

From REQUIREMENTS.md section 13.1:

- App Lifecycle
- Model Operations
- Record Operations
- Collection Operations
- Auth Operations
- Request Processing
- Realtime
- Mailer

## Rules

1. **Never change the registration API** once implemented
2. **Hooks must be async** for consistency
3. **Priority ordering** - lower numbers run first
4. **Built-in hooks cannot be disabled** by users
