---
trigger: model_decision
description: FastAPI route conventions - apply when editing API route files
---

# API Route Conventions

## API Structure

```
/api/v1/
├── /auth/                    # Registration, login, refresh, OAuth, SAML
├── /collections/             # Collection management (superadmin)
├── /migrations/              # Migration management
├── /accounts/                # Account management (superadmin)
├── /users/                   # User management (account-scoped)
├── /roles/                   # Role management (global)
├── /{collection}/            # Dynamic collection CRUD
└── /realtime/                # WebSocket/SSE subscriptions
```

## Route Guidelines

1. **Version prefix** - All routes under `/api/v1/`
2. **Account context** - Most routes require account_id in JWT
3. **Superadmin routes** - Explicitly marked and protected
4. **Dynamic routes** - `/{collection}/` handles user-created collections

## Response Format

Use consistent response structures:

- Success: `{"data": ..., "meta": {...}}`
- Error: `{"error": {"code": "...", "message": "..."}}`
- List: `{"data": [...], "meta": {"total": N, "page": N, "per_page": N}}`

## Dependencies

Use FastAPI dependency injection for:

- Authentication (`get_current_user`)
- Account context (`get_current_account`)
- Database sessions (`get_db`)
