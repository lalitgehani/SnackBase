---
activation: always_on
description: Clean Architecture and code organization rules for SnackBase
---

# Architecture Rules

## Clean Architecture Layers

The project follows **Clean Architecture** with three distinct layers:

```
src/snackbase/
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

## Critical Principles

1. **Domain layer has ZERO dependencies** on FastAPI, SQLAlchemy, or any infrastructure code
2. **Application layer orchestrates** domain logic via use cases
3. **Infrastructure layer contains ALL** external dependencies

## Layer Rules

### Domain Layer (`domain/`)
- No imports from `fastapi`, `sqlalchemy`, or `infrastructure/`
- Pure Python business logic only
- Define interfaces/protocols that infrastructure implements

### Application Layer (`application/`)
- May import from `domain/`
- No direct imports from `infrastructure/`
- Use dependency injection for infrastructure access

### Infrastructure Layer (`infrastructure/`)
- May import from both `domain/` and `application/`
- Implements domain interfaces
- Contains all FastAPI routes, SQLAlchemy models, external integrations
