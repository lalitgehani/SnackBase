# SnackBase

> Open-source Backend-as-a-Service (BaaS) - A self-hosted alternative to PocketBase

SnackBase is a Python/FastAPI-based BaaS providing auto-generated REST APIs, multi-tenancy, row-level security, authentication, and GxP-compliant audit logging.

## Status

**Phase 1: Foundation & MVP** (Nearing Completion - 11/13 features complete)

- [x] F1.1: Project Scaffolding & Architecture Setup
- [x] F1.2: Database Schema & Core System Tables
- [x] F1.3: Account Registration
- [x] F1.4: Account Login
- [x] F1.5: JWT Token Management
- [x] F1.6: Dynamic Collection Creation
- [x] F1.7-F1.10: Dynamic Record CRUD
- [x] F1.11: User Invitation System
- [x] F1.12: Hook System Infrastructure
- [x] F1.13: Account ID Generator

**Documentation Status**: ✅ Complete

- [Deployment Guide](docs/deployment.md) - Development and production deployment
- [Hook System](docs/hooks.md) - Extensibility framework and stable API
- [API Examples](docs/api-examples.md) - Practical usage examples

## Features

### Currently Implemented

- **Clean Architecture** - Domain, application, and infrastructure layer separation
- **Configuration Management** - Environment variables and `.env` file support
- **Structured JSON Logging** - Correlation ID tracking for request tracing
- **Database Abstraction** - SQLAlchemy 2.0 async with SQLite and PostgreSQL support
- **Health Check Endpoints** - `/health`, `/ready`, `/live`
- **CLI** - Server management and utility commands

#### Authentication System

- **Account Registration** - Multi-tenant account creation with unique `XX####` ID format
- **User Registration** - Per-account user registration with email/password
- **Login** - Timing-safe password verification with account resolution
- **JWT Token Management** - Access tokens (1 hour) and refresh tokens (7 days) with rotation
- **Password Hashing** - Argon2id (OWASP recommended)
- **Protected Endpoints** - JWT-based authentication with `Authorization: Bearer` header

#### Domain Layer

- **Entities** - Account, User, Role, Group, Collection, Invitation
- **Services** - AccountIdGenerator, PasswordValidator, SlugGenerator

#### Persistence Layer

- **ORM Models** - Account, User, Role, Group, Collection, Invitation, RefreshToken, UsersGroups
- **Repositories** - AccountRepository, UserRepository, RoleRepository, RefreshTokenRepository

### Planned Features

- Auto-generated CRUD APIs for dynamic collections
- Row-level security engine with SQL macros
- User-specific and role-based permissions
- PII masking with field-level access control
- GxP-compliant audit logging
- Real-time subscriptions (WebSocket/SSE)
- OAuth/SAML authentication
- Admin UI for platform management

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd SnackBase

# Install dependencies
uv sync

# Or install with pip
pip install -e .
```

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Deployment Guide](docs/deployment.md)** - Complete guide for development and production deployment

  - Development setup with SQLite
  - Production deployment with PostgreSQL and systemd
  - Nginx reverse proxy configuration
  - Environment variables reference
  - Health checks and monitoring
  - Troubleshooting guide

- **[Hook System](docs/hooks.md)** - Extensibility framework documentation

  - Stable API contract (v1.0)
  - Hook categories and events
  - Built-in hooks (timestamp, account_isolation, created_by)
  - Creating custom hooks
  - Advanced features and best practices

- **[API Examples](docs/api-examples.md)** - Practical API usage examples

  - Authentication flows
  - Collection creation
  - CRUD operations
  - Error handling
  - Best practices

- **[API Reference (Swagger)](http://localhost:8000/docs)** - Interactive API documentation

## Usage

### CLI Commands

```bash
# Start the development server
uv run python -m snackbase serve

# Show configuration information
uv run python -m snackbase info

# Initialize the database (development only)
uv run python -m snackbase init-db

# Interactive Python shell with SnackBase context
uv run python -m snackbase shell
```

### Server Options

```bash
# Custom host and port
uv run python -m snackbase serve --host 127.0.0.1 --port 3000

# Enable auto-reload for development
uv run python -m snackbase serve --reload

# Multiple workers
uv run python -m snackbase serve --workers 4
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application
SNACKBASE_ENVIRONMENT=development
SNACKBASE_DEBUG=false
SNACKBASE_API_PREFIX=/api/v1

# Server
SNACKBASE_HOST=0.0.0.0
SNACKBASE_PORT=8000

# Database
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

## API Endpoints

### Health Checks

- `GET /health` - Basic health check
- `GET /ready` - Readiness check (includes database connectivity)
- `GET /live` - Liveness check

### API Root

- `GET /api/v1` - API information

### Authentication

- `POST /api/v1/auth/register` - Create a new account with admin user

  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{
      "account_name": "My Company",
      "email": "admin@example.com",
      "password": "SecurePass123!"
    }'
  ```

- `POST /api/v1/auth/login` - Login with email, password, and account identifier

  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "email": "admin@example.com",
      "password": "SecurePass123!",
      "account_identifier": "my-company"
    }'
  ```

- `POST /api/v1/auth/refresh` - Refresh access token using refresh token

  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/refresh \
    -H "Content-Type: application/json" \
    -d '{"refresh_token": "..."}'
  ```

- `GET /api/v1/auth/me` - Get current authenticated user info (requires JWT)

## Project Structure

```
SnackBase/
├── src/
│   └── snackbase/
│       ├── __init__.py
│       ├── __main__.py          # Entry point for `python -m snackbase`
│       ├── cli.py               # CLI commands
│       ├── core/
│       │   ├── config.py        # Configuration management
│       │   └── logging.py       # Structured logging
│       ├── domain/              # Business entities (no external deps)
│       │   ├── entities/        # Account, User, Role, Group, Collection, Invitation
│       │   └── services/        # AccountIdGenerator, PasswordValidator, SlugGenerator
│       ├── application/         # Use cases and orchestration
│       │   ├── commands/        # Write operations (TODO)
│       │   └── queries/         # Read operations (TODO)
│       └── infrastructure/      # External dependencies
│           ├── api/
│           │   ├── app.py       # FastAPI application factory
│           │   ├── dependencies.py # Auth dependencies
│           │   ├── routes/
│           │   │   └── auth_router.py # Auth endpoints
│           │   └── schemas/
│           │       └── auth_schemas.py # Pydantic models
│           ├── auth/
│           │   ├── jwt_service.py    # JWT token management
│           │   └── password_hasher.py # Argon2 password hashing
│           ├── persistence/
│           │   ├── database.py  # SQLAlchemy async engine
│           │   ├── models/      # ORM models
│           │   └── repositories/ # Data access layer
│           ├── realtime/        # WebSocket/SSE (TODO)
│           └── storage/         # File storage (TODO)
├── sb_data/                     # Data directory (gitignored)
│   ├── snackbase.db            # SQLite database
│   └── files/                   # File uploads
├── CLAUDE.md                    # Project instructions for AI
├── REQUIREMENTS.md              # Detailed requirements
├── PRD_PHASES.md                # Phase-by-phase development plan
├── pyproject.toml               # Project configuration
└── README.md                    # This file
```

## Architecture

SnackBase follows **Clean Architecture** principles with three layers:

1. **Domain Layer** - Core business logic with zero dependencies on external frameworks
2. **Application Layer** - Use cases and orchestration of domain logic
3. **Infrastructure Layer** - All external dependencies (FastAPI, SQLAlchemy, etc.)

### Multi-Tenancy Model

Accounts represent isolated tenants within a single database. Data segregation uses row-level isolation via `account_id` column. Users can belong to multiple accounts with the same email address, using a `(email, account_id)` identity tuple.

### Account ID Format

Accounts use auto-generated IDs in format `XX####` (2 letters + 4 digits, e.g., `AB1234`):

- `id`: XX#### format (primary key, immutable)
- `slug`: URL-friendly identifier for login (globally unique)
- `name`: Display name (not unique)

### Authentication System

- **Password Hashing**: Argon2id algorithm (OWASP recommended)
- **JWT Tokens**: Access tokens (1 hour) + refresh tokens (7 days) with rotation
- **Timing-Safe Comparison**: Prevents user enumeration attacks
- **Token Storage**: Refresh tokens stored in database with SHA-256 hashing and revocation tracking

### Two-Tier Table Architecture

1. **Core System Tables** - Schema changes via releases (accounts, users, roles, permissions, collections)
2. **User-Created Collections** - Global tables shared by ALL accounts (e.g., `posts`, `products`)

## Development

### Code Quality

```bash
# Run linting
uv run ruff check .

# Format code
uv run ruff format .

# Type checking
uv run mypy src/
```

### Testing (Coming Soon)

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=snackbase
```

## Configuration Reference

| Setting                                 | Default                                      | Description                       |
| --------------------------------------- | -------------------------------------------- | --------------------------------- |
| `SNACKBASE_DATABASE_URL`                | `sqlite+aiosqlite:///./sb_data/snackbase.db` | Database connection URL           |
| `SNACKBASE_SECRET_KEY`                  | `change-me-in-production...`                 | JWT signing key                   |
| `SNACKBASE_ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                                         | Access token expiration (minutes) |
| `SNACKBASE_REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                                          | Refresh token expiration (days)   |
| `SNACKBASE_PORT`                        | `8000`                                       | Server port                       |
| `SNACKBASE_LOG_LEVEL`                   | `INFO`                                       | Logging level                     |
| `SNACKBASE_LOG_FORMAT`                  | `json`                                       | Log format (json/console)         |

## Roadmap

See [PRD_PHASES.md](PRD_PHASES.md) for detailed phase-by-phase specifications.

- **Phase 1**: Foundation & MVP - Multi-tenancy, auth, dynamic collections
- **Phase 2**: Security & Authorization - RLS, PII masking, SQL macros
- **Phase 3**: Admin UI & Operations - Dashboard, migrations, audit logging
- **Phase 4**: Advanced Features - Real-time, PostgreSQL, hooks
- **Phase 5**: Enterprise - OAuth/SAML, rate limiting, monitoring

## Contributing

Contributions are welcome! Please read the requirements documentation before starting work.

## License

[Your License Here]

## Acknowledgments

Inspired by [PocketBase](https://pocketbase.io/), a self-hosted BaaS in Go.
