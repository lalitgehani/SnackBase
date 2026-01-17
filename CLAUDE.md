# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SnackBase** is a Python/FastAPI-based Backend-as-a-Service (BaaS) designed as an open-source, self-hosted alternative to PocketBase. It provides auto-generated REST APIs, multi-tenancy, row-level security, authentication, and GxP-compliant audit logging.

**Current State**: Phase 1 nearly complete (11/13 features). Full-stack implementation with React admin UI, comprehensive testing, and 11 API routers.

## Package Management

This project uses **uv** (not pip, poetry, or pdm) for package management:

```bash
uv sync                    # Install dependencies
uv add <package>           # Add a dependency
uv run python -m snackbase <command>  # Run CLI commands
```

## Development Commands

### Backend (Python/FastAPI)

```bash
# Server management
uv run python -m snackbase serve          # Start server (0.0.0.0:8000)
uv run python -m snackbase serve --reload # Dev mode with auto-reload
uv run python -m snackbase info           # Show configuration

# Database
uv run python -m snackbase init-db        # Initialize database (dev only)
uv run python -m snackbase create-superadmin  # Create superadmin user

# Interactive shell
uv run python -m snackbase shell          # IPython REPL with pre-loaded context

# Code quality
uv run ruff check .                        # Lint
uv run ruff format .                       # Format
uv run mypy src/                           # Type check

# Testing
uv run pytest                              # Run all tests
uv run pytest tests/unit/                  # Unit tests only
uv run pytest tests/integration/           # Integration tests only
uv run pytest --cov=snackbase              # With coverage
uv run pytest -k "test_name"               # Run specific test
```

### Frontend (React/TypeScript)

```bash
cd ui
npm run dev        # Start dev server (Vite)
npm run build      # Production build
npm run lint       # ESLint
npm run preview    # Preview production build
```

## Python Version

Python 3.12+ is required. The project uses `.python-version` for version specification.

## Architecture

The project follows **Clean Architecture** with three layers:

```
src/snackbase/
├── core/                         # Cross-cutting concerns (no external deps)
│   ├── config.py                 # Pydantic Settings for env-based config
│   ├── logging.py                # Structured logging with structlog
│   ├── configuration/            # Configuration registry (provider system)
│   ├── hooks/                    # Hook registry, decorator, events (STABLE API)
│   ├── macros/                   # SQL macro execution engine
│   └── rules/                    # Rule engine (lexer, parser, AST, evaluator)
├── domain/                       # Core business logic (no external dependencies)
│   ├── entities/                 # Business entities (dataclasses)
│   └── services/                 # Business logic interfaces
├── application/                  # Use cases and orchestration
│   ├── commands/                 # Write operations (placeholder)
│   └── queries/                  # Read operations (placeholder)
└── infrastructure/               # External concerns
    ├── api/
    │   ├── app.py                # FastAPI app factory, lifespan, middleware
    │   ├── dependencies.py       # FastAPI dependencies (auth, session, API key auth)
    │   ├── routes/               # 14+ API routers
    │   ├── schemas/              # Pydantic request/response models
    │   └── middleware/           # Authorization middleware
    ├── persistence/
    │   ├── database.py           # SQLAlchemy 2.0 async engine
    │   ├── models/               # ORM models (Account, User, Role, Configuration, ApiKey, etc.)
    │   ├── repositories/         # Repository pattern (12+ repositories)
    │   └── table_builder.py      # Dynamic table creation
    ├── auth/                     # JWT service, password hasher (Argon2), API key service
    ├── configuration/            # Provider handlers (OAuth, SAML, email)
    │   └── providers/            # Provider implementations
    ├── hooks/                    # Built-in hooks implementation
    ├── security/                 # Encryption service
    ├── services/                 # Token service, email service
    ├── realtime/                 # Empty (WebSocket/SSE TODO)
    └── storage/                  # Empty (file storage TODO)

ui/                               # React + TypeScript Admin UI
├── src/
│   ├── pages/                    # Dashboard, Accounts, Collections, Roles, ApiKeys, etc.
│   ├── components/               # React components (Radix UI + TailwindCSS)
│   ├── services/                 # API clients (axios)
│   ├── stores/                   # Zustand state management
│   └── lib/                      # Utilities, axios config
```

**Key Principles**:

- Domain layer has ZERO dependencies on FastAPI or infrastructure
- Infrastructure layer contains ALL external dependencies
- Repository pattern abstracts data access

## Multi-Tenancy Model

Accounts represent isolated tenants within a single database using row-level isolation via `account_id` column.

### Two-Tier Table Architecture

1. **Core System Tables** - Schema changes via releases only (accounts, users, roles, permissions, collections, macros, migrations)
2. **User-Created Collections** - Global tables shared by ALL accounts (e.g., `posts`, `products`)

**Critical**: User-created collections are SINGLE physical tables where all accounts' data is stored together, isolated by `account_id`. The `collections` table stores schema definitions/metadata only.

### Account ID Format

Accounts use auto-generated IDs in format `XX####` (2 letters + 4 digits, e.g., `AB1234`).

- `id`: XX#### format (primary key, immutable)
- `slug`: URL-friendly identifier for login (globally unique)
- `name`: Display name (not unique)

### Superadmin vs Admin

| Aspect  | Superadmin                                | Admin (role)                        |
| ------- | ----------------------------------------- | ----------------------------------- |
| Account | Linked to `system` account (ID: `SY0000`) | Linked to specific account          |
| Access  | All accounts and system operations        | Full CRUD within their account only |

## Authentication

### Enterprise Multi-Account Model

Users can belong to multiple accounts with the same email address. User identity is `(email, account_id)` tuple.

- Passwords are **per-account** - each `(email, account_id)` has its own password
- Login always requires account context (slug/ID from URL or request body)
- JWT with access token (1 hour) and refresh token (7 days) with rotation

### API Key Authentication

Alternative authentication method for service-to-service communication:

- API keys use format: `sb_sk_<account_code>_<random_32_chars>`
- Keys are hashed using SHA-256 before storage (plaintext only shown once at creation)
- Authenticate via `Authorization: Bearer <api_key>` header
- Scoped to account level with optional name/description for identification
- Can be revoked via API or admin UI
- Managed via `/api/v1/api-keys/` endpoint

## Key Technical Decisions

### Database

- **Default**: SQLite (aiosqlite driver)
- **Production**: PostgreSQL (asyncpg driver)
- **ORM**: SQLAlchemy 2.0 (async)
- Account ID generator produces `XX####` format

### Hook System (Stable API v1.0)

**The hook registry is a STABLE API contract.** Changing the registration mechanism is a breaking change.

```python
# Hook registration (decorator syntax via app.hook)
@app.hook.on_record_after_create("posts", priority=10)
async def send_post_notification(record, context):
    await notification_service.send(record.created_by, "Post created!")

# Built-in hooks (cannot be unregistered):
# - timestamp_hook (auto-sets created_at/updated_at)
# - account_isolation_hook (enforces account_id filtering)
# - created_by_hook (sets created_by user)
```

Hook categories: App Lifecycle, Model Operations, Record Operations, Collection Operations, Auth Operations, Request Processing.

### Rule Engine

Custom DSL for permission expressions with full lexer/parser/AST implementation:

```python
# Supported syntax
user.id == "user_abc123"
@has_role("admin") and @owns_record()
status in ["draft", "published"]
```

### Permission Resolution

- Role-based with wildcard collection support (`*`)
- OR logic for multiple permissions
- Field-level access control
- 5-minute TTL cache (invalidated on permission changes)

### Configuration/Provider System

**Hierarchical Configuration Model**: External service provider settings (auth, email, storage) with two levels:

1. **System-level** (account_id: `00000000-0000-0000-0000-000000000000`) - Default configs for all accounts
2. **Account-level** - Per-account overrides that take precedence over system defaults

**Key Components**:
- `ConfigurationRegistry` (src/snackbase/core/configuration/config_registry.py) - Central registry for provider definitions and hierarchical resolution with 5-minute cache
- `ConfigurationModel` - ORM model with encrypted `config` JSON field
- Provider handlers in `src/snackbase/infrastructure/configuration/providers/`:
  - `auth/` - Email/password authentication
  - `oauth/` - OAuth providers (Google, GitHub, Microsoft, Apple)
  - `saml/` - SAML providers (Azure AD, Okta, generic)

**Architecture Pattern**:
- Provider definitions registered via `config_registry.register_provider_definition()`
- Config resolution: account-level config → system-level fallback
- All sensitive config values encrypted at rest
- Built-in providers marked with `is_builtin` flag (cannot be deleted)
- **Verified providers**: Some providers (e.g., Google OAuth) are marked with a verified badge in the UI indicating they have been manually tested

## API Structure

```
/health, /ready, /live          # Health checks (no prefix)
/api/v1/
├── /auth/                      # Register, login, refresh, me
├── /collections/               # Collection CRUD (superadmin)
├── /accounts/                  # Account management (superadmin)
├── /users/                     # User management (superadmin)
├── /roles/                     # Role management
├── /permissions/               # Permission management
├── /macros/                    # SQL macro management
├── /groups/                    # Group management
├── /invitations/               # User invitations
├── /api-keys/                  # API key management (create, list, revoke)
├── /dashboard/                 # Dashboard statistics
├── /audit-logs/                # Audit log retrieval and export
├── /migrations/                # Alembic migration status
├── /admin/                     # Admin API (system/config management)
├── /oauth/                     # OAuth flow endpoints
├── /saml/                      # SAML flow endpoints
└── /{collection}/              # Dynamic collection CRUD (records_router)
```

**Route Registration Order Matters**: `records_router` (dynamic `/api/v1/{collection}`) must be registered last to avoid capturing specific routes like `/invitations`.

## Testing

**Tools**: pytest, pytest-asyncio, httpx AsyncClient with ASGITransport

**Fixtures** (in `tests/conftest.py`):

- `db_session` - In-memory SQLite session
- `client` - Test HTTP client with dependency overrides
- `superadmin_token` - Pre-authenticated superadmin JWT
- `regular_user_token` - Pre-authenticated regular user JWT

**Test Markers**:

- `@pytest.mark.enable_audit_hooks` - Enable audit logging hooks for tests (adds overhead, use only when needed)

## Important Constraints

- **Hook system is stable API** - Cannot change registration mechanism once implemented
- **Macros are global** - Defined once, shared by all accounts
- **Migrations are global** - Affect ALL accounts (collections are global tables)
- **Audit logs are immutable** - Once written, cannot be modified
- **Configuration hierarchy** - System-level configs use `00000000-0000-0000-0000-000000000000` as account_id, not `SY0000`
- **Built-in providers** - Cannot be deleted (is_builtin flag), only disabled

## Environment Variables

Key configuration via `.env` or environment:

```bash
SNACKBASE_DATABASE_URL=sqlite+aiosqlite:///./sb_data/snackbase.db
SNACKBASE_SECRET_KEY=your-secret-key
SNACKBASE_CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Frontend Tech Stack

- React 19 + React Router v7 + Vite 7
- TailwindCSS 4 + Radix UI components
- TanStack Query for data fetching
- Zustand for state management
- Zod for validation
- **ShadCN**: Use existing components in `ui/src/components/ui/`.
- Intall new ShadCN components using npx shadcn@latest add {component name}
- Never create ShadCN component file. Always install using CLI.
