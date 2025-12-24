---
trigger: model_decision
description: Database conventions for SQLAlchemy and async operations - apply when working on persistence layer
---

# Database Conventions

## Database Support

- **Default**: SQLite (aiosqlite driver)
- **Production**: PostgreSQL (asyncpg driver)
- **ORM**: SQLAlchemy 2.0 (async)

## Async Pattern

Always use async database operations:

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(session: AsyncSession, user_id: str):
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
```

## Account ID Generator

- Format: `XX####` (2 letters + 4 digits)
- Example: `AB1234`, `SY0000` (system account)
- Must be unique and immutable

## Model Conventions

1. **Always include `account_id`** on user-created collection tables
2. **Use UUID or generated IDs** for primary keys
3. **Timestamps**: `created_at`, `updated_at` with timezone
4. **Soft delete pattern**: `deleted_at` timestamp

## Performance

- Use eager loading for known relationships
- Prefer `selectinload` over `joinedload` for collections
- Index foreign keys and commonly filtered columns
