# SnackBase

> Open-source Backend-as-a-Service (BaaS) - A self-hosted alternative to PocketBase

SnackBase is a Python/FastAPI-based BaaS providing auto-generated REST APIs, multi-tenancy, row-level security, authentication, and GxP-compliant audit logging.

## Status

**Phase 1: Foundation & MVP** (In Progress - 1/13 features complete)

- [x] F1.1: Project Scaffolding & Architecture Setup
- [ ] F1.2: Database Schema & Core System Tables
- [ ] F1.3: Account Registration
- [ ] F1.4: Account Login
- [ ] F1.5: JWT Token Management
- [ ] F1.6: Dynamic Collection Creation
- [ ] F1.7-F1.10: Dynamic Record CRUD
- [ ] F1.11: User Invitation System
- [ ] F1.12: Hook System Infrastructure
- [ ] F1.13: Account ID Generator

## Features

### Currently Implemented

- **Clean Architecture** - Domain, application, and infrastructure layer separation
- **Configuration Management** - Environment variables and `.env` file support
- **Structured JSON Logging** - Correlation ID tracking for request tracing
- **Database Abstraction** - SQLAlchemy 2.0 async with SQLite and PostgreSQL support
- **Health Check Endpoints** - `/health`, `/ready`, `/live`
- **CLI** - Server management and utility commands

### Planned Features

- Multi-tenant data isolation
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
│       │   ├── entities/
│       │   └── services/
│       ├── application/         # Use cases and orchestration
│       │   ├── commands/
│       │   └── queries/
│       └── infrastructure/      # External dependencies
│           ├── api/
│           │   └── app.py       # FastAPI application
│           ├── auth/
│           ├── persistence/
│           │   └── database.py  # SQLAlchemy database layer
│           ├── realtime/
│           └── storage/
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

Accounts represent isolated tenants within a single database. Data segregation uses row-level isolation via `account_id` column.

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

| Setting | Default | Description |
|---------|---------|-------------|
| `SNACKBASE_DATABASE_URL` | `sqlite+aiosqlite:///./sb_data/snackbase.db` | Database connection URL |
| `SNACKBASE_SECRET_KEY` | `change-me-in-production...` | JWT signing key |
| `SNACKBASE_PORT` | `8000` | Server port |
| `SNACKBASE_LOG_LEVEL` | `INFO` | Logging level |
| `SNACKBASE_LOG_FORMAT` | `json` | Log format (json/console) |

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
