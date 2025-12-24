---
trigger: model_decision
description: Row-level security and permission rules - apply when working on access control or authorization
---

# Permissions & Row-Level Security Rules

## Permission Evaluation

Rules are evaluated per-record for row-level security.

## SQL Macros

User-defined SQL queries can be referenced in permission rules:

```
@macro_name()
```

### Built-in Macros

- `@has_group()` - Check user group membership
- `@has_role()` - Check user role assignment
- `@owns_record()` - Check record ownership
- And more from REQUIREMENTS.md

## User-Specific Rules

Grant elevated permissions to specific users:

```
user.id == "user_abc123"
```

## Key Principles

1. **Macros are global** - Defined once, shared by all accounts
2. **Migrations are global** - Affect ALL accounts (collections are global tables)
3. **Default deny** - No access unless explicitly granted
4. **Evaluate at query time** - Don't cache permission decisions

## Permission Contexts

Always include in permission evaluation:

- `user.id`
- `user.account_id`
- `user.role`
- `user.groups[]`
- `record.*` (current record fields)
