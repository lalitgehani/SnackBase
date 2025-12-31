<img width="2816" height="1536" alt="Gemini_Generated_Image_2g6dru2g6dru2g6d" src="https://github.com/user-attachments/assets/71d1b9b7-1b31-44c7-8520-eb748f788190" />

# SnackBase

> Open-source Backend-as-a-Service (BaaS) - A self-hosted alternative to PocketBase

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-cyan.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SnackBase is a Python/FastAPI-based BaaS providing auto-generated REST APIs, multi-tenancy, row-level security, authentication, and comprehensive admin UI.

## Status

**Phase 1: Foundation & MVP** (92% Complete - 12/13 features)

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
- [ ] Real-time subscriptions (WebSocket/SSE)

**Phase 2: Security & Authorization** (90% Complete)

- [x] F2.1-F2.5: Permission Data Model & Rule Engine
- [x] F2.6-F2.7: SQL Macros & Group-Based Permissions
- [x] F2.8: Permission Caching (5-minute TTL)
- [x] F2.9: Authorization Middleware
- [x] F2.10: User-Specific Rules
- [x] F2.11-F2.13: PII Field Tagging, Masking & Field-Level Access Control
- [x] F2.14: Group-Based Permission Macros

**Phase 3: Operations** (70% Complete)

- [x] F3.1-F3.5: Dashboard & Management UIs (Dashboard, Accounts, Collections, Roles, Permissions)
- [x] F3.6-F3.8: Audit Log Storage, Capture & Query API
- [x] F3.9-F3.12: Alembic Infrastructure & Migration Management UI

**Phase 4: Advanced Features** (0% Complete)

- [ ] F4.1-F4.4: Real-time Subscriptions (WebSocket/SSE) & PostgreSQL Support
- [ ] F4.5-F4.7: File Storage Engine & Advanced Query Filters

**Phase 5: Enterprise Features** (Not Started)

- [ ] OAuth/SAML, Rate Limiting, Advanced Monitoring

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

## Features

### Core Platform

- **Clean Architecture** - Domain, application, and infrastructure layer separation
- **Multi-Tenancy** - Row-level isolation with account-scoped data
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

### Dynamic Collections & Records

- **Collection Management** - Create, read, update, delete collections with custom schemas
- **Auto-Generated CRUD APIs** - RESTful endpoints for any collection
- **Field Types** - Text, number, email, boolean, date, JSON, select, relation
- **Schema Builder UI** - Visual interface for designing collection schemas
- **Bulk Operations** - Bulk create, update, delete with filtering

### Authorization & Security

- **Role-Based Access Control (RBAC)** - Flexible roles and permissions system
- **Permission System** - Granular CRUD permissions per collection
- **Rule Engine** - Custom DSL for permission expressions (`@has_role()`, `@owns_record()`)
- **Wildcard Collection Support** - `*` for all collections
- **Field-Level Access Control** - Show/hide specific fields
- **Permission Caching** - 5-minute TTL with invalidation
- **PII Masking** - 6 mask types (email, ssn, phone, name, full, custom) with group-based access control

### Extensibility

- **Hook System (Stable API v1.0)** - Event-driven extensibility
  - App Lifecycle, Model Operations, Record Operations, Collection Operations
  - Built-in hooks: timestamp, account_isolation, created_by, audit_capture
  - Custom hooks with priority-based execution
- **SQL Macros** - Reusable SQL snippets with safe execution
  - Built-in permission macros: `@has_role()`, `@has_group()`, `@owns_record()`, `@in_time_range()`
  - Timeout protection (5 seconds) and test mode with rollback
- **Group Management** - User groups for easier permission assignment

### Admin UI

- **React + TypeScript** - Modern admin interface
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

### API & Testing

- **13 API Routers** - Comprehensive REST API coverage
- **Interactive Docs** - Swagger/OpenAPI at `/docs`
- **Comprehensive Tests** - Unit, integration, and security tests with pytest (680+ tests)
- **Test Coverage** - High coverage across core functionality

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

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Quick Start Tutorial](docs/quick-start.md)** - Get up and running in 5 minutes
- **[Conceptual Guides](docs/concepts/)** - Deep dives into multi-tenancy, collections, authentication, and security
- **[Developer Guides](docs/guides/)** - Practical tutorials for API endpoints, hooks, rules, and testing
- **[Deployment Guide](docs/deployment.md)** - Development and production deployment
- **[Frontend Guide](docs/frontend.md)** - React admin UI development
- **[Hook System](docs/hooks.md)** - Extensibility framework and stable API
- **[API Examples](docs/api-examples.md)** - Practical usage examples
- **[API Reference (Swagger)](http://localhost:8000/docs)** - Interactive API documentation

## CLI Commands

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
```

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

# CORS
SNACKBASE_CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
SNACKBASE_LOG_LEVEL=INFO
SNACKBASE_LOG_FORMAT=json
```

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
├── /dashboard/                 # Dashboard statistics
├── /audit-logs/                # Audit log retrieval and export
├── /migrations/                # Alembic migration status
└── /records/{collection}/      # Dynamic collection CRUD
```

## Project Structure

```
SnackBase/
├── src/snackbase/
│   ├── core/                         # Cross-cutting concerns
│   │   ├── config.py                 # Pydantic Settings
│   │   ├── logging.py                # Structured logging
│   │   ├── hooks/                    # Hook registry (STABLE API v1.0)
│   │   ├── macros/                   # SQL macro execution engine
│   │   └── rules/                    # Rule engine (lexer, parser, AST)
│   ├── domain/                       # Core business logic
│   │   ├── entities/                 # Business entities (Account, User, Role, etc.)
│   │   └── services/                 # Business logic (validators, resolvers)
│   ├── application/                  # Use cases
│   │   ├── commands/                 # Write operations (placeholder)
│   │   ├── queries/                  # Read operations (placeholder)
│   │   └── services/                 # Migration query service
│   └── infrastructure/               # External dependencies
│       ├── api/
│       │   ├── app.py                # FastAPI app factory
│       │   ├── dependencies.py       # FastAPI dependencies
│       │   ├── routes/               # 13 API routers
│       │   ├── schemas/              # Pydantic models
│       │   └── middleware/           # Authorization, context, logging
│       ├── persistence/
│       │   ├── database.py           # SQLAlchemy 2.0 async
│       │   ├── models/               # ORM models (11 models)
│       │   ├── repositories/         # Repository pattern (11 repositories)
│       │   └── table_builder.py      # Dynamic table creation
│       ├── auth/                     # JWT, password hasher
│       ├── hooks/                    # Built-in hooks implementation
│       ├── services/                 # Token, email services
│       ├── realtime/                 # WebSocket/SSE (TODO)
│       └── storage/                  # File storage (TODO)
├── ui/                               # React Admin UI
│   ├── src/
│   │   ├── pages/                    # Dashboard, Accounts, Collections, etc. (11 pages)
│   │   ├── components/               # React components (Radix + Tailwind)
│   │   ├── services/                 # API clients (11 services)
│   │   ├── stores/                   # Zustand state
│   │   └── lib/                      # Utilities
├── tests/                            # Unit, integration, security tests
│   ├── unit/                         # 40+ test files
│   ├── integration/                  # 29+ test files
│   ├── security/                     # 8+ test files with HTML reporter
│   └── conftest.py                   # Pytest fixtures
├── sb_data/                          # Data directory (gitignored)
├── CLAUDE.md                         # AI assistant instructions
├── pyproject.toml                    # Project configuration
└── README.md                         # This file
```

## Development

### Backend

```bash
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

### Frontend

**Tech Stack**: React 19 + React Router v7 + Vite 7 + TailwindCSS 4 + Radix UI + TanStack Query + Zustand + Zod

```bash
cd ui
npm run dev        # Start dev server (Vite)
npm run build      # Production build
npm run lint       # ESLint
npm run preview    # Preview production build
npx shadcn@latest add {component}  # Install ShadCN components
```

## Architecture

### Clean Architecture

SnackBase follows **Clean Architecture** with three layers:

1. **Domain Layer** - Core business logic with zero external dependencies
2. **Application Layer** - Use cases and orchestration
3. **Infrastructure Layer** - All external dependencies (FastAPI, SQLAlchemy)

### Multi-Tenancy Model

Accounts represent isolated tenants using row-level isolation via `account_id`:

- **Account ID Format**: `XX####` (2 letters + 4 digits, e.g., `AB1234`)
- **User Identity**: `(email, account_id)` tuple
- **Password Scope**: Per-account (same email = different passwords per account)

### Two-Tier Table Architecture

1. **Core System Tables** - Schema changes via releases (accounts, users, roles, permissions, collections, macros, migrations)
2. **User-Created Collections** - Single global tables shared by ALL accounts

**Critical**: User collections are ONE physical table where all accounts store data together, isolated by `account_id`. The `collections` table stores schema definitions only.

### Hook System (Stable API v1.0)

The hook registry is a **STABLE API contract**:

```python
@app.hook.on_record_after_create("posts", priority=10)
async def send_post_notification(record, context):
    await notification_service.send(record.created_by, "Post created!")
```

Built-in hooks (cannot be unregistered):
- `timestamp_hook` - Auto-sets created_at/updated_at
- `account_isolation_hook` - Enforces account_id filtering
- `created_by_hook` - Sets created_by/updated_by user
- `audit_capture_hook` - Captures GxP-compliant audit entries for CREATE/UPDATE/DELETE

### Rule Engine

Custom DSL for permission expressions:

```python
user.id == "user_abc123"
@has_role("admin") and @owns_record()
status in ["draft", "published"]
```

## Roadmap

See [PRD_PHASES.md](PRD_PHASES.md) for detailed specifications.

- [x] **Phase 1**: Foundation & MVP - Multi-tenancy, auth, dynamic collections, UI (92% complete)
- [x] **Phase 2**: Security & Authorization - RBAC, permissions, rule engine, groups, PII masking (90% complete)
- [ ] **Phase 3**: Operations - GxP audit logging (done), migrations (done), dashboard UI (done)
- [ ] **Phase 4**: Advanced Features - Real-time (WebSocket/SSE), file storage, PostgreSQL support
- [ ] **Phase 5**: Enterprise - OAuth/SAML, rate limiting, monitoring

## Contributing

Contributions are welcome! Please read [CLAUDE.md](CLAUDE.md) for development guidelines.

## License

MIT License - See LICENSE file for details

## Acknowledgments

Inspired by [PocketBase](https://pocketbase.io/), a self-hosted BaaS in Go.
