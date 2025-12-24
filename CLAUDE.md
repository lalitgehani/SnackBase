# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SnackBase** is a Python/FastAPI-based Backend-as-a-Service (BaaS) designed as an open-source, self-hosted alternative to PocketBase. It provides auto-generated REST APIs, multi-tenancy, row-level security, authentication, and GxP-compliant audit logging.

**Current State**: Pre-implementation - only project scaffolding exists. The project has comprehensive requirements documentation but no actual implementation yet.

## Package Management

This project uses **uv** (not pip, poetry, or pdm) for package management:

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Run the application
uv run python main.py
# or
python -m snackbase serve
```

## Python Version

Python 3.12+ is required. The project uses `.python-version` for version specification.

## Architecture

The project follows **Clean Architecture** with three layers (see REQUIREMENTS.md section 2):

```
src/
├── domain/                    # Core business logic (no external dependencies)
│   ├── entities/              # Business entities (Account, User, Collection, etc.)
│   └── services/              # Business logic interfaces
├── application/               # Use cases and orchestration
│   ├── commands/              # Write operations
│   └── queries/               # Read operations
└── infrastructure/            # External concerns
    ├── persistence/           # Database adapters (SQLite/PostgreSQL)
    ├── api/                   # FastAPI routes, middleware, dependencies
    ├── auth/                  # JWT, OAuth, SAML implementations
    ├── realtime/              # WebSocket/SSE handling
    └── storage/               # File storage (local/S3)
```

**Key Principles**:
- Domain layer has ZERO dependencies on FastAPI or infrastructure
- Application layer orchestrates domain logic
- Infrastructure layer contains ALL external dependencies

## Multi-Tenancy Model

Accounts represent isolated tenants within a single database. Data segregation uses row-level isolation via `account_id` column.

### Two-Tier Table Architecture

1. **Core System Tables** - Schema changes via releases only (accounts, users, roles, permissions, collections, macros, migrations)
2. **User-Created Collections** - Global tables shared by ALL accounts (e.g., `posts`, `products`)

**Critical**: User-created collections like `posts` are SINGLE physical tables where all accounts' data is stored together, isolated by `account_id`. The `collections` table stores schema definitions/metadata, not the actual data.

### Account ID Format

Accounts use auto-generated IDs in format `XX####` (2 letters + 4 digits, e.g., `AB1234`).
- `id`: XX#### format (primary key, immutable)
- `slug`: URL-friendly identifier for login (globally unique)
- `name`: Display name (not unique)

## Authentication

### Enterprise Multi-Account Model

Users can belong to multiple accounts with the same email address. User identity is `(email, account_id)` tuple.

- Passwords are **per-account** - each `(email, account_id)` has its own password
- OAuth identities are stored separately in `oauth_identities` table
- Login always requires account context (slug/ID from URL or request body)

### Superadmin vs Admin

| Aspect | Superadmin | Admin (role) |
|--------|------------|--------------|
| Account | Linked to `system` account (ID: `SY0000`) | Linked to specific account |
| Access | All accounts and system operations | Full CRUD within their account only |

## Key Technical Decisions

### Database

- **Default**: SQLite (aiosqlite driver)
- **Production**: PostgreSQL (asyncpg driver)
- **ORM**: SQLAlchemy 2.0 (async)
- Account ID generator produces `XX####` format

### Authentication

- JWT-based with refresh token rotation
- Access token: 1 hour default
- Refresh token: 7 days default
- Claims: user_id, account_id, email, role

### Permissions

- **Row-Level Security**: Permission rules evaluated per-record
- **SQL Macros**: User-defined SQL queries referenced in rules with `@macro_name()` syntax
- **User-Specific Rules**: `user.id == "user_abc123"` grants elevated permissions
- **Built-in Macros**: `@has_group()`, `@has_role()`, `@owns_record()`, etc.

### Hook System (Design Upfront - Stable API)

The hook registry is **stable API contract**. Changing the registration mechanism later would be a breaking change.

```python
# Hook registration (decorator syntax)
@app.hook.on_record_after_create("posts", priority=10)
async def send_post_notification(record, context):
    await notification_service.send(record.created_by, "Post created!")

# Built-in hooks (cannot be unregistered):
# - timestamp_hook, account_isolation_hook (Phase 1)
# - permission_check_hook, pii_masking_hook (Phase 2)
# - audit_log_hook (Phase 3)
```

Hook categories (from REQUIREMENTS.md section 13.1):
- App Lifecycle, Model Operations, Record Operations, Collection Operations
- Auth Operations, Request Processing, Realtime, Mailer

### Audit Logging

**GxP-compliant** (21 CFR Part 11, EU Annex 11):
- ONE central `audit_log` table for ALL collections
- Column-level granularity (one row per column changed)
- Immutable writes (no UPDATE/DELETE on audit logs)
- Blockchain-style integrity (checksums, previous_hash)

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

## Development Planning

See `PRD_PHASES.md` for detailed phase-by-phase specifications:

1. **Phase 1**: Foundation & MVP - Multi-tenancy, auth, dynamic collections
2. **Phase 2**: Security & Authorization - RLS, PII masking, SQL macros
3. **Phase 3**: Admin UI & Operations - Dashboard, migrations, audit logging
4. **Phase 4**: Advanced Features - Real-time, PostgreSQL, hooks
5. **Phase 5**: Enterprise - OAuth/SAML, rate limiting, monitoring

## Important Constraints

- **No dev dependencies yet** - No testing, linting, or type checking tools configured
- **Hook system is stable API** - Cannot change registration mechanism once implemented
- **Macros are global** - Defined once, shared by all accounts
- **Migrations are global** - Affect ALL accounts (collections are global tables)
- **Audit logs are immutable** - Once written, cannot be modified
