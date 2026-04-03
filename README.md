<img width="2816" height="1536" alt="SnackBase" src="https://github.com/user-attachments/assets/71d1b9b7-1b31-44c7-8520-eb748f788190" />

# SnackBase

> Open-source Backend-as-a-Service (BaaS) - A self-hosted alternative to Supabase

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-cyan.svg)](https://react.dev/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

SnackBase is a Python/FastAPI-based BaaS providing auto-generated REST APIs, multi-tenancy, row-level security, authentication, enterprise OAuth/SAML, and comprehensive admin UI.

## Deployment

| Setup Type                | Link                                                                                                                                                                          |
| :------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SnackBase with SQLite     | [![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/duQK4B?referralCode=W3p73R&utm_medium=integration&utm_source=template&utm_campaign=generic) |
| SnackBase with PostgreSQL | [![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/Ob4NPC?referralCode=W3p73R&utm_medium=integration&utm_source=template&utm_campaign=generic) |

## Project Statistics

| Category          | Count      | Lines    |
| ----------------- | ---------- | -------- |
| **Backend Code**  | ~248 files | ~130,000 |
| **Frontend Code** | ~268 files | ~60,000  |
| **Tests**         | 191 files  | ~30,000  |
| **Documentation** | 31+ files  | ~20,000  |
| **Total**         | ~525 files | ~195,000 |

---

## Status

**Phase 1: Foundation & MVP** (100% Complete)

- [x] F1.1: Project Scaffolding & Architecture Setup
- [x] F1.2: Database Schema & Core System Tables
- [x] F1.3: Account Registration
- [x] F1.4: Account Login
- [x] F1.5: JWT Token Management
- [x] F1.6: Dynamic Collection Creation
- [x] F1.7-F1.10: Dynamic Record CRUD
- [x] F1.11: User Invitation System
- [x] F1.12: Hook System Infrastructure (STABLE API v1.0)
- [x] F1.13: Account ID Generator
- [x] Full React Admin UI with Dashboard
- [x] Rule Engine & Permission System
- [x] Group Management
- [x] User Management UI
- [x] GxP-compliant audit logging
- [x] Real-time subscriptions (WebSocket/SSE)

**Phase 2: Security & Authorization** (100% Complete)

- [x] F2.1-F2.5: Permission System V2 (SQL-native RLS)
- [x] F2.6-F2.7: SQL Macros & Group-Based Permissions
- [x] F2.8: Authorization Middleware & Repository Integration
- [x] F2.10: Collection-centric Rule Management
- [x] F2.11-F2.13: Field-Level Access Control
- [x] F2.14: GxP-compliant Audit Logging for Permissions

**Phase 3: Operations** (100% Complete)

- [x] F3.1-F3.5: Dashboard & Management UIs (Dashboard, Accounts, Collections, Roles, Rules)
- [x] F3.6-F3.8: Audit Log Storage, Capture & Query API
- [x] F3.9-F3.12: Alembic Infrastructure & Migration Management UI

**Phase 4: Advanced Features** (60% Complete)

- [x] F4.1-F4.2: Real-time Subscriptions (WebSocket/SSE)
- [x] F4.3: PostgreSQL Support (SQLite + PostgreSQL with dialect-aware queries)
- [x] F4.5: File Storage Engine (Local filesystem with account-scoped storage)
- [x] F4.6: Basic Query Filters (Pagination, sorting, equality filters)
- [ ] F4.7: Advanced Query Filters (LIKE, IN, range queries, complex boolean logic)
- [~] Cloud Storage Providers (Local + Amazon S3 implemented, Azure Blob/GCS planned)

**Phase 5: Enterprise Features** (40% Complete)

- [x] Rate Limiting (IP-based and user-based, configurable per endpoint)
- [x] Security Headers (HSTS, CSP, Permissions-Policy)
- [ ] Advanced Monitoring (Prometheus metrics, distributed tracing)
- [ ] APM Integration (DataDog, New Relic)

**Phase 6: Data Layer Competitiveness** (100% Complete)

- [x] F6.1: Advanced Filtering Operators (comparison `>`, `<`, `>=`, `<=`, `!=`, `IN`/`NOT IN`, `IS NULL`/`IS NOT NULL`, `~` LIKE; reuses rule engine grammar; type-safe comparisons)
- [x] F6.2: Reference Expansion (populate reference fields inline via `?expand=field`; deep/nested expansion; batch-loaded to avoid N+1)
- [x] F6.3: Anonymous / Public Access (public collections accessible without authentication; per-operation public toggle; public badge in UI)
- [x] F6.4: Bulk Operations (batch create, batch update, batch delete; JSON import/export for records; filter-aware export)
- [x] F6.5: Aggregation Queries (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX` with `GROUP BY` and `HAVING`; Analytics page with group-by builder)
- [x] F6.6: Full-Text Search (skipped)
- [x] F6.7: Cursor-Based Pagination (efficient pagination for large datasets; `cursor`/`cursor_before` params; page vs scroll mode in UI)

**Phase 7: Background Processing** (100% Complete)

- [x] F7.2: Background Job Queue (async workers, retry logic, job monitoring UI)
- [x] F7.3: Scheduled Tasks (cron-based scheduling, scheduler admin UI)
- [x] F7.4: Computed/Virtual Fields (expression compiler, SQL injection at query time, filter/sort support)

**Phase 8: Extensibility & Automation** (100% Complete)

- [x] F8.1: API-Defined Hooks (unified automation: event/schedule/manual triggers, action executor, execution log, hot-reload)
- [x] F8.2: Custom Endpoints (serverless functions: DB-stored HTTP endpoints dispatched via `/api/v1/x/{slug}/{path}`, 30s timeout, path params, template vars)
- [x] F8.3: Workflow Engine (multi-step automation: directed-graph steps, event/schedule/manual/webhook triggers, job-backed wait_delay)

---

## Quick Start

**New to SnackBase?** Start with the [5-minute Quick Start Tutorial](docs/quick-start.md) with screenshots and step-by-step instructions.

```bash
# Clone and install
git clone https://github.com/yourusername/snackbase.git
cd SnackBase
uv sync

# Initialize database and create superadmin
uv run python -m snackbase init-db
uv run python -m snackbase create-superadmin

# Start server
uv run python -m snackbase serve

# Access the UI
open http://localhost:8000
```

---

## Features

### Core Platform

- **Clean Architecture** - Domain, application, and infrastructure layer separation (~120K LOC)
- **Multi-Tenancy** - Row-level isolation with account-scoped data
- **Single-Tenant Mode** - Support for dedicated instances where all users join a pre-configured account (optional account identifier for login/registration)
- **Configuration Management** - Environment variables and `.env` file support
- **Structured JSON Logging** - Correlation ID tracking for request tracing
- **Health Checks** - `/health`, `/ready`, `/live` endpoints

### Authentication System

- **Account Registration** - Multi-tenant account creation with unique `XX####` ID format
- **User Registration** - Per-account user registration with email/password
- **Login** - Timing-safe password verification with account resolution
- **JWT Token Management** - Access tokens (1 hour) and refresh tokens (7 days) with rotation
- **Password Hashing** - Argon2id (OWASP recommended)
- **Multi-Account Support** - Users can belong to multiple accounts
- **OAuth 2.0** - Google, GitHub, Microsoft, Apple
- **SAML 2.0** - Okta, Azure AD, Generic SAML

### Dynamic Collections & Records

- **Collection Management** - Create, read, update, delete collections with custom schemas
- **Auto-Generated CRUD APIs** - RESTful endpoints for any collection
- **Field Types** - Text, number, boolean, datetime, email, url, json, reference, file
- **Schema Builder UI** - Visual interface for designing collection schemas
- **Batch Operations** - Bulk create, update, delete with filtering
- **Advanced Query Filters** - Complex boolean expressions (`AND`, `OR`, `NOT`), comparison (`=`, `!=`, `<`, `>`, `~` LIKE), `IN`/`NOT IN`, `IS NULL`, grouping with parentheses
- **Aggregation Queries** - `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` with `GROUP BY` and `HAVING` support
- **Cursor-Based Pagination** - Efficient pagination for large datasets alongside offset pagination
- **Reference Field Expansion** - Populate reference fields inline via `?expand=field` (supports deep/nested expansion)
- **Public Collections** - Anonymous read access for public data without authentication
- **Reference Fields** - Foreign keys to other collections with cascade options

### Authorization & Security

- **Database-Centric RLS** - SQL-native row-level security inspired by Supabase/PocketBase
- **5-Operation Model** - Granular control for `list`, `view`, `create`, `update`, and `delete`
- **Collection-Centric Rules** - Define rules per collection instead of per role
- **SQL-Native Rule Engine** - Rules compile directly to efficient SQL WHERE clauses
- **Field-Level Access Control** - Operation-specific field visibility (show/hide fields per operation)
- **PII Masking** - 6 mask types (email, ssn, phone, name, full, custom) with group-based access
- **SQL Macros** - Reusable expression fragments (e.g., `@owns_record`, `@has_role`)

### Extensibility & Automation

- **Hook System (Stable API v1.0)** - Event-driven extensibility
  - 40+ hook events across 8 categories
  - Built-in hooks: timestamp, account_isolation, created_by, audit_capture
  - Custom hooks with priority-based execution
- **API-Defined Hooks (F8.1)** - Create and manage hooks via API or Admin UI
  - Trigger types: event (data events), schedule (cron), manual (explicit API call)
  - Action executor pipeline with execution log and hot-reload
- **Custom Endpoints (F8.2)** - Serverless functions stored in the database
  - Define HTTP endpoints with custom path, method, and action pipeline
  - Dispatched via `/api/v1/x/{slug}/{path}` with 30-second timeout
  - Path parameters, template variables, and execution history tracking
- **Workflow Engine (F8.3)** - Multi-step automation with directed-graph steps
  - Trigger types: event, schedule, manual, webhook
  - Job-backed `wait_delay` for asynchronous step execution
  - Workflow instances with step-by-step logging, cancel/resume, status tracking
- **Outbound Webhooks** - HTTP webhook delivery with retry logic and delivery logs
- **SQL Macros** - Reusable SQL snippets with safe execution
  - Built-in permission macros: `@has_role()`, `@has_group()`, `@owns_record()`, `@in_time_range()`, `@has_permission()`
  - Timeout protection (5 seconds) and test mode with rollback
- **Group Management** - User groups for easier permission assignment

### Admin UI

- **React 19 + TypeScript** - Modern admin interface with 28+ pages
- **Dashboard** - Platform statistics and metrics with auto-refresh
- **Account Management** - Create and manage accounts (superadmin)
- **User Management** - Full CRUD for users across accounts (superadmin)
- **Role Management** - Create roles and assign permissions
- **Permission Management** - Matrix view and bulk operations
- **Collection Builder** - Visual schema designer
- **Records Browser** - Data grid with filtering and editing
- **Group Management** - Organize users into groups
- **Macros Management** - SQL macro editor with test execution
- **Migrations Viewer** - Alembic revision history and status
- **Audit Logs** - Filterable, exportable audit trail with PII masking
- **Configuration Dashboard** - System/account-level provider configs (OAuth, SAML, Email, Storage)
- **Email Templates** - Customizable email template management
- **API Keys** - Create, list, and revoke service API keys
- **Hooks** - Create and manage user-defined hooks (event/schedule/manual)
- **Custom Endpoints** - Build and test serverless function endpoints
- **Workflows** - Design multi-step workflows and track execution instances
- **Webhooks** - Configure outbound webhooks and view delivery history
- **Background Jobs** - Monitor job queue status, retries, and history
- **Scheduled Tasks** - Manage cron-scheduled tasks
- **Analytics** - Platform usage analytics dashboard

### Additional Features

- **API Key Authentication** - Service-to-service authentication with `sb_sk_` prefixed keys, SHA-256 hashing, optional expiration, and revocation support
- **Collection Export/Import** - Export collections with all records to JSON and import to migrate or backup data
- **Security Headers** - Configurable HSTS, CSP, and Permissions-Policy headers for enhanced security
- **Two-Phase Collection Deletion** - Safe deletion with confirmation to prevent accidental data loss
- **Rate Limiting** - IP-based and user-based rate limiting, configurable per endpoint, superadmin bypass
- **File Storage** - Configurable system-level storage provider with local filesystem (default) or Amazon S3, account-scoped paths, UUID-based filenames, size validation (10MB default), and MIME type validation
- **Real-time Updates** - WebSocket and SSE endpoints for live data updates on CRUD operations
- **Background Job Queue** - Async job workers with retry logic, status tracking, and monitoring UI
- **Scheduled Tasks** - Cron-based scheduled task management with an admin UI
- **Computed/Virtual Fields** - Expression-based virtual fields compiled to SQL at query time with filter/sort support
- **Outbound Webhooks** - Configurable HTTP webhook delivery with automatic retry and delivery history

### Storage Providers

- **System-level only** - Storage provider selection is managed at system scope from the Configuration Dashboard
- **Built-in providers** - `local` (default) and `s3` (Amazon S3)
- **Hybrid file paths**:
  - Local files: `account_id/uuid_filename`
  - S3 files: `s3/account_id/uuid_filename`
- **Compatibility** - Existing local file paths remain valid after switching the system default provider

### API & Testing

- **28 API Routers** - Comprehensive REST API coverage with 150+ endpoints
- **Interactive Docs** - Swagger/OpenAPI at `/docs`
- **Comprehensive Tests** - 1,161 tests (unit, integration, security)
  - 705+ unit tests
  - 317+ integration tests
  - 50+ security tests with HTML reporting
- **Test Coverage** - ~30,000 lines of test code

---

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/snackbase.git
cd SnackBase

# Install dependencies
uv sync

# Create environment file
cp .env.example .env
# Edit .env with your configuration
```

---

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

### Core Documentation

- **[Quick Start Tutorial](docs/quick-start.md)** - Get up and running in 5 minutes
- **[Architecture](docs/architecture.md)** - Complete system architecture with diagrams
- **[Deployment Guide](docs/deployment.md)** - Development and production deployment

### Conceptual Guides

- **[Multi-Tenancy](docs/concepts/multi-tenancy.md)** - Shared database, row-level isolation model
- **[Collections](docs/concepts/collections.md)** - Dynamic schemas and field types
- **[Authentication](docs/concepts/authentication.md)** - Authentication concepts
- **[Security](docs/concepts/security.md)** - Security model

### Developer Guides

- **[Testing](docs/guides/testing.md)** - pytest with async testing patterns
- **[Creating Custom Hooks](docs/guides/creating-custom-hooks.md)** - Hook system extension
- **[Writing Permission Rules](docs/guides/writing-rules.md)** - Rule engine syntax
- **[Adding API Endpoints](docs/guides/adding-api-endpoints.md)** - API development
- **[Frontend Development](docs/frontend.md)** - React UI development

### Reference Documentation

- **[Hook System](docs/hooks.md)** - Extensibility framework (Stable API v1.0)
- **[Permission System](docs/permissions.md)** - Authorization and rules
- **[Macros](docs/macros.md)** - Built-in and SQL macros
- **[API Examples](docs/api-examples.md)** - Practical usage examples (3,700+ lines)
- **[API Reference (Swagger)](http://localhost:8000/docs)** - Interactive API documentation

---

## CLI Commands

```bash
# Server management
uv run python -m snackbase serve          # Start server (0.0.0.0:8000)
uv run python -m snackbase serve --reload # Dev mode with auto-reload
uv run python -m snackbase info           # Show configuration

# Database
uv run python -m snackbase init-db        # Initialize database (dev only)
uv run python -m snackbase create-superadmin  # Create superadmin user

# Migrations
uv run python -m snackbase migrate upgrade    # Apply migrations
uv run python -m snackbase migrate downgrade  # Rollback
uv run python -m snackbase migrate history    # Show history

# Interactive shell
uv run python -m snackbase shell          # IPython REPL with pre-loaded context
```

---

## Environment Variables

Create a `.env` file in the project root:

```bash
# Application
SNACKBASE_ENVIRONMENT=development
SNACKBASE_DEBUG=false
SNACKBASE_API_PREFIX=/api/v1

# Server
SNACKBASE_HOST=0.0.0.0
SNACKBASE_PORT=8000

# Database (default: SQLite)
SNACKBASE_DATABASE_URL=sqlite+aiosqlite:///./sb_data/snackbase.db
# For PostgreSQL:
# SNACKBASE_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Security
SNACKBASE_SECRET_KEY=your-secret-key-here
SNACKBASE_ENCRYPTION_KEY=your-encryption-key

# CORS
SNACKBASE_CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
SNACKBASE_LOG_LEVEL=INFO
SNACKBASE_LOG_FORMAT=json
SNACKBASE_AUDIT_LOGGING_ENABLED=true

# Single-Tenant Mode
SNACKBASE_SINGLE_TENANT_MODE=false
SNACKBASE_SINGLE_TENANT_ACCOUNT=my-app
SNACKBASE_SINGLE_TENANT_ACCOUNT_NAME=My Application
```

---

## Deployment

### One-Click Deployment (Railway)

SnackBase is ready for one-click deployment on Railway with a managed PostgreSQL database.

1. Fork this repository.
2. Click the **Deploy on Railway** button above.
3. Railway will prompt you for the required environment variables:
   - `SNACKBASE_SECRET_KEY`
   - `SNACKBASE_ENCRYPTION_KEY`
4. The database will be provisioned automatically.

See the [Deployment Guide](docs/deployment.md) for other platforms.

---

## API Structure

```
/health, /ready, /live          # Health checks (no prefix)
/api/v1/
├── /auth/                      # Register, login, refresh, me, password reset
├── /oauth/                     # OAuth 2.0 flow (Google, GitHub, Microsoft, Apple)
├── /saml/                      # SAML 2.0 SSO (Okta, Azure AD, Generic)
├── /collections/               # Collection CRUD (superadmin)
├── /accounts/                  # Account management (superadmin)
├── /users/                     # User management (superadmin)
├── /roles/                     # Role management
├── /permissions/               # Permission management
├── /collection-rules/          # Collection-level access rules
├── /macros/                    # SQL macro management
├── /groups/                    # Group management
├── /invitations/               # User invitations
├── /api-keys/                  # API key management (create, list, revoke)
├── /dashboard/                 # Dashboard statistics
├── /audit-logs/                # Audit log retrieval and export
├── /migrations/                # Alembic migration status
├── /files/                     # File upload/download
├── /realtime/                  # WebSocket (/ws) & SSE (/events) real-time subscriptions
├── /webhooks/                  # Outbound webhook management
├── /jobs/                      # Background job queue management
├── /hooks/                     # User-defined hook management (event/schedule/manual)
├── /endpoints/                 # Custom serverless endpoint management
├── /workflows/                 # Workflow engine (steps, triggers, instances)
├── /email-templates/           # Email template management
├── /admin/                     # System/configuration management
├── /x/{slug}/{path}            # Custom endpoint dispatcher (serverless functions)
└── /{collection}/              # Dynamic collection CRUD (registered last)
```

---

## Project Structure

```
SnackBase/
├── src/snackbase/
│   ├── core/                         # Cross-cutting concerns (~3,000 LOC)
│   │   ├── config.py                 # Pydantic Settings
│   │   ├── logging.py                # Structured logging
│   │   ├── context.py                # ContextVar-based global state
│   │   ├── hooks/                    # Hook registry (STABLE API v1.0)
│   │   │   ├── hook_registry.py      # Registration and execution
│   │   │   ├── hook_decorator.py     # Decorator API
│   │   │   └── hook_events.py        # 40+ event definitions
│   │   ├── macros/                   # SQL macro execution engine
│   │   │   └── engine.py             # Built-in macros, SQL execution
│   │   ├── rules/                    # Rule engine (lexer, parser, AST)
│   │   │   ├── lexer.py              # Tokenization
│   │   │   ├── parser.py             # Recursive descent parser
│   │   │   ├── ast.py                # AST nodes
│   │   │   └── evaluator.py          # Safe evaluation
│   │   └── configuration/            # Configuration registry
│   │       └── config_registry.py    # Hierarchical config resolution
│   ├── domain/                       # Core business logic (~6,000 LOC)
│   │   ├── entities/                 # Business entities (dataclasses)
│   │   │   ├── account.py            # Account entity
│   │   │   ├── user.py               # User entity
│   │   │   ├── role.py               # Role entity
│   │   │   ├── permission.py         # Permission entity
│   │   │   ├── group.py              # Group entity
│   │   │   ├── collection.py         # Collection entity
│   │   │   ├── hook_context.py       # Hook context, abort exception
│   │   │   └── ...                   # 17 entities total
│   │   └── services/                 # Business logic
│   │       ├── permission_resolver.py    # Permission evaluation
│   │       ├── permission_cache.py        # 5-min TTL cache
│   │       ├── audit_log_service.py       # GxP audit logging
│   │       ├── pii_masking_service.py     # PII masking (6 types)
│   │       ├── account_code_generator.py  # XX#### format
│   │       └── ...                       # 20+ services
│   ├── application/                  # Use cases (minimal)
│   │   ├── commands/                 # Write operations
│   │   ├── queries/                  # Read operations
│   │   └── services/                 # Migration query service
│   └── infrastructure/               # External dependencies (~110,000 LOC)
│       ├── api/
│       │   ├── app.py                # FastAPI app factory
│       │   ├── dependencies.py       # FastAPI dependencies
│       │   ├── routes/               # 28 API routers
│       │   │   ├── auth_router.py              # Authentication
│       │   │   ├── oauth_router.py             # OAuth flow
│       │   │   ├── saml_router.py              # SAML SSO
│       │   │   ├── collections_router.py       # Collection CRUD
│       │   │   ├── records_router.py           # Dynamic records (registered last)
│       │   │   ├── accounts_router.py          # Account mgmt
│       │   │   ├── users_router.py             # User mgmt
│       │   │   ├── roles_router.py             # Role mgmt
│       │   │   ├── permissions_router.py       # Permission mgmt
│       │   │   ├── collection_rules_router.py  # Collection-level rules
│       │   │   ├── groups_router.py            # Group mgmt
│       │   │   ├── invitations_router.py       # Invitations
│       │   │   ├── api_keys_router.py          # API key auth
│       │   │   ├── audit_log_router.py         # Audit logs
│       │   │   ├── dashboard_router.py         # Statistics
│       │   │   ├── macros_router.py            # SQL macros
│       │   │   ├── migrations_router.py        # Alembic status
│       │   │   ├── files_router.py             # File upload
│       │   │   ├── realtime_router.py          # WebSocket/SSE
│       │   │   ├── webhooks_router.py          # Outbound webhooks
│       │   │   ├── jobs_router.py              # Background job queue
│       │   │   ├── hooks_router.py             # User-defined hooks
│       │   │   ├── endpoints_router.py         # Custom endpoints
│       │   │   ├── custom_endpoint_dispatcher.py # Serverless dispatch (/x/)
│       │   │   ├── workflows_router.py         # Workflow engine
│       │   │   ├── email_templates_router.py   # Email templates
│       │   │   └── admin_router.py             # System config
│       │   ├── schemas/              # Pydantic models
│       │   └── middleware/           # Authorization, context, logging
│       ├── persistence/
│       │   ├── database.py           # SQLAlchemy 2.0 async
│       │   ├── models/               # ORM models (31 models)
│       │   ├── repositories/         # Repository pattern (20+ repos)
│       │   ├── table_builder.py      # Dynamic table creation
│       │   ├── migration_service.py  # Dynamic migrations
│       │   └── event_listeners.py    # SQLAlchemy event hooks
│       ├── configuration/
│       │   └── providers/            # Provider implementations
│       │       ├── auth/             # Email/password
│       │       ├── oauth/            # Google, GitHub, Microsoft, Apple
│       │       ├── saml/             # Okta, Azure AD, Generic
│       │       └── email/            # SMTP, AWS SES, Resend
│       ├── auth/                     # JWT, password hasher
│       ├── security/                 # Encryption service
│       ├── hooks/                    # Built-in hooks implementation
│       ├── workflows/                # Workflow engine & executor
│       ├── endpoints/                # Custom endpoint executor
│       └── services/                 # Token, email, scheduler, job queue
├── ui/                               # React Admin UI (~60,000 LOC)
│   ├── src/
│   │   ├── pages/                    # 28+ pages
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── AccountsPage.tsx
│   │   │   ├── UsersPage.tsx
│   │   │   ├── CollectionsPage.tsx
│   │   │   ├── RecordsPage.tsx
│   │   │   ├── RolesPage.tsx
│   │   │   ├── GroupsPage.tsx
│   │   │   ├── InvitationsPage.tsx
│   │   │   ├── AuditLogsPage.tsx
│   │   │   ├── MigrationsPage.tsx
│   │   │   ├── MacrosPage.tsx
│   │   │   ├── ConfigurationDashboardPage.tsx
│   │   │   ├── ApiKeys/              # API key management
│   │   │   ├── Hooks/                # User-defined hooks
│   │   │   ├── Endpoints/            # Custom serverless endpoints
│   │   │   ├── Workflows/            # Workflow designer & instances
│   │   │   ├── Webhooks/             # Outbound webhooks
│   │   │   ├── Jobs/                 # Background job monitoring
│   │   │   ├── ScheduledTasks/       # Scheduled task management
│   │   │   └── AnalyticsPage.tsx     # Analytics dashboard
│   │   ├── components/               # React components
│   │   │   ├── ui/                   # 35+ ShadCN components
│   │   │   ├── accounts/             # Account-specific components
│   │   │   ├── audit-logs/           # Audit log components
│   │   │   ├── collections/          # Schema builder, CRUD dialogs
│   │   │   ├── common/               # Reusable components
│   │   │   ├── groups/               # Group management
│   │   │   ├── invitations/          # Invitation components
│   │   │   ├── macros/               # SQL macro editor
│   │   │   ├── migrations/           # Migration status
│   │   │   ├── records/              # Dynamic record CRUD
│   │   │   └── roles/                # Permission matrix, rule editor
│   │   ├── services/                 # API clients (20+ services)
│   │   │   ├── auth.service.ts
│   │   │   ├── accounts.service.ts
│   │   │   ├── collections.service.ts
│   │   │   ├── records.service.ts
│   │   │   └── ...                   # + 16 more
│   │   ├── stores/                   # Zustand state
│   │   │   └── auth.store.ts         # Authentication state
│   │   └── lib/                      # Utilities, axios config
├── tests/                            # Test suite (~29,600 LOC)
│   ├── unit/                         # 705 unit tests
│   ├── integration/                  # 317 integration tests
│   ├── security/                     # 50+ security tests
│   ├── verification/                 # 8 verification scripts
│   └── conftest.py                   # Pytest fixtures
├── docs/                             # Documentation (~20,000 LOC)
│   ├── quick-start.md                # 5-minute tutorial
│   ├── architecture.md               # System architecture
│   ├── deployment.md                 # Deployment guide
│   ├── frontend.md                   # Frontend development
│   ├── hooks.md                      # Hook system (v1.0)
│   ├── permissions.md                # Permission system
│   ├── macros.md                     # Macro documentation
│   ├── api-examples.md               # API examples (3,700+ lines)
│   ├── concepts/                     # Conceptual guides
│   └── guides/                       # Developer guides
├── sb_data/                          # Data directory (gitignored)
├── alembic/                          # Database migrations
├── CLAUDE.md                         # AI assistant instructions
├── pyproject.toml                    # Project configuration
└── README.md                         # This file
```

---

## Development

### Backend

```bash
# Code quality
uv run ruff check .                        # Lint
uv run ruff format .                       # Format
uv run mypy src/                           # Type check

# Testing
uv run pytest                              # Run all tests (1,022 tests)
uv run pytest tests/unit/                  # Unit tests only (705)
uv run pytest tests/integration/           # Integration tests only (317)
uv run pytest tests/security/              # Security tests only (50+)
uv run pytest --cov=snackbase              # With coverage
uv run pytest -k "test_name"               # Run specific test
uv run pytest -m enable_audit_hooks        # Run with audit hooks
```

### Frontend

**Tech Stack**: React 19 + React Router v7 + Vite 7 + TailwindCSS 4 + Radix UI + TanStack Query v5 + Zustand v5 + Zod

```bash
cd ui
npm run dev        # Start dev server (Vite)
npm run build      # Production build
npm run lint       # ESLint
npm run preview    # Preview production build
npx shadcn@latest add {component}  # Install ShadCN components
```

---

## Architecture

### Clean Architecture

SnackBase follows **Clean Architecture** with three layers:

1. **Core Layer** - Cross-cutting concerns with ZERO external dependencies
   - Configuration (Pydantic Settings)
   - Structured logging (structlog)
   - Hook registry (STABLE API v1.0)
   - Rule engine (lexer, parser, AST, evaluator)
   - Macro execution engine

2. **Domain Layer** - Core business logic with zero external dependencies
   - Entities (dataclasses)
   - Services (validators, resolvers)

3. **Infrastructure Layer** - All external dependencies
   - FastAPI (web framework)
   - SQLAlchemy 2.0 (ORM)
   - Configuration providers (OAuth, SAML, Email)

### Multi-Tenancy Model

Accounts represent isolated tenants using row-level isolation via `account_id`:

- **Account ID Format**: `XX####` (2 letters + 4 digits, e.g., `AB1234`)
- **User Identity**: `(email, account_id)` tuple
- **Password Scope**: Per-account (same email = different passwords per account)
- **System Account**: `00000000-0000-0000-0000-000000000000` for system-level configs

### Two-Tier Table Architecture

1. **Core System Tables** - Schema changes via releases (17 ORM models)
2. **User-Created Collections** - Single global tables shared by ALL accounts

**Critical**: User collections are ONE physical table (`col_*`) where all accounts store data together, isolated by `account_id`. The `collections` table stores schema definitions only.

### Hook System (Stable API v1.0)

The hook registry is a **STABLE API contract**:

```python
@app.hook.on_record_after_create("posts", priority=10)
async def send_post_notification(record, context):
    await notification_service.send(record.created_by, "Post created!")
```

**40+ Hook Events** across 8 categories:

- App Lifecycle: `on_bootstrap`, `on_serve`, `on_terminate`
- Model Operations: `on_model_before/after_create/update/delete`
- Record Operations: `on_record_before/after_create/update/delete/query`
- Collection Operations: `on_collection_before/after_create/update/delete`
- Auth Operations: `on_auth_before/after_login/register/logout`
- Request Processing: `on_before_request`, `on_after_request`
- Realtime: `on_realtime_connect/disconnect/message`
- Mailer: `on_mailer_before/after_send`

**Built-in hooks** (cannot be unregistered):

- `timestamp_hook` (-100 priority): Auto-sets created_at/updated_at
- `account_isolation_hook` (-200 priority): Enforces account_id filtering
- `created_by_hook` (-150 priority): Sets created_by/updated_by user
- `audit_capture_hook` (100 priority): Captures GxP-compliant audit entries

### Rule Engine (V2)

SnackBase V2 uses a database-centric rule engine that compiles simple expressions into SQL WHERE clauses for performance and scalability.

```python
# Owner-only access (compiles to SQL WHERE created_by = :auth_id)
created_by = @request.auth.id

# Admin or owner access
@request.auth.role = "admin" || created_by = @request.auth.id

# Status-based filtering
status = "published" && (category = "news" || category = "updates")

# Macro usage (expanded before compilation)
@owns_record() && status = "draft"
```

**Supported operators**: `=`, `!=`, `<`, `>`, `<=`, `>=`, `~` (LIKE), `&&`, `||`, `!`

**Common Variables**:

- `@request.auth.*` - id, email, role, account_id
- `@request.data.*` - Request body fields (for create/update validation)
- `fieldname` - Direct access to record fields

**Built-in macros**:

- `@has_role(role_name)` - Check user role
- `@has_group(group_name)` - Check group membership
- `@owns_record()` / `@is_creator()` - Check record ownership
- `@in_time_range(start, end)` - Time-based access
- `@has_permission(action, collection)` - Permission check

### Configuration Hierarchy

**Two-level hierarchy** for provider configurations:

1. **System-level** (`00000000-0000-0000-0000-000000000000`)
   - Default configs for all accounts
   - Managed by superadmins

2. **Account-level**
   - Per-account overrides
   - Takes precedence over system defaults

**Providers**:

- **Auth**: Email/password, OAuth (Google, GitHub, Microsoft, Apple), SAML (Okta, Azure AD, Generic)
- **Email**: SMTP, AWS SES, Resend

---

## Roadmap

See [PRD_PHASES.md](PRD_PHASES.md) for detailed specifications.

- [x] **Phase 1**: Foundation & MVP - Multi-tenancy, auth, dynamic collections, UI (100% complete)
- [x] **Phase 2**: Security & Authorization - RBAC, permissions, rule engine, groups, PII masking (100% complete)
- [x] **Phase 3**: Operations - GxP audit logging, migrations, dashboard UI (100% complete)
- [~] **Phase 4**: Advanced Features - Real-time (WebSocket/SSE), file storage, PostgreSQL support (60% complete)
- [~] **Phase 5**: Enterprise - Rate limiting, monitoring (40% complete)
- [x] **Phase 6**: Data Layer Competitiveness - Advanced filters, reference expansion, public access, bulk ops, aggregations, cursor pagination (100% complete)
- [x] **Phase 7**: Background Processing - Job queue, scheduled tasks, computed/virtual fields (100% complete)
- [x] **Phase 8**: Extensibility & Automation - API-defined hooks, custom endpoints, workflow engine (100% complete)

---

## Contributing

Contributions are welcome! Please read [CLAUDE.md](CLAUDE.md) for development guidelines.

---

## License

GNU Affero General Public License v3.0 (AGPLv3) - See LICENSE file for details

### When can you use SnackBase?

**You CAN use SnackBase for:**

- **Internal tools** - Build internal dashboards, admin panels, and business tools
- **Side projects** - Personal projects, hobbies, and learning
- **Commercial applications** - Build and sell SaaS products, mobile apps, and web applications
- **Client work** - Use it in projects for clients without sharing your application code
- **Modifications** - Modify SnackBase for your own internal use

**AGPL obligations ONLY apply when:**

- You modify SnackBase's **source code** AND
- You make it available to users as a **network service** (hosted BaaS)

In this case, you must provide the source code of your modified SnackBase to users of the service.

**What does NOT trigger AGPL:**

- Using SnackBase unmodified as a backend for your application
- Hosting your own application that uses SnackBase
- Selling your application (your code remains yours)
- Building closed-source applications on top of SnackBase

**Summary**: AGPL is designed to prevent companies from taking SnackBase, modifying it, and selling it as a competing BaaS service without contributing back. For most users (SaaS founders, agencies, internal teams), SnackBase works like any other open-source backend.

---

## Acknowledgments

Inspired by modern BaaS platforms like Supabase and Firebase, bringing enterprise-grade features to self-hosted infrastructure.
