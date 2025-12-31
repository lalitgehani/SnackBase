# Adding API Endpoints

This guide explains how to add new API endpoints to SnackBase, following the established patterns and architecture.

---

## Table of Contents

- [Overview](#overview)
- [Architecture Review](#architecture-review)
- [Where to Add Endpoints](#where-to-add-endpoints)
- [Step-by-Step Guide](#step-by-step-guide)
- [Request/Response Patterns](#requestresponse-patterns)
- [Authentication & Authorization](#authentication--authorization)
- [Testing Endpoints](#testing-endpoints)
- [Best Practices](#best-practices)

---

## Overview

SnackBase uses **FastAPI** for REST API endpoints. All endpoints are organized in the `src/snackbase/infrastructure/api/routes/` directory.

### Existing API Routers

| Router | Purpose | Path |
|--------|---------|------|
| `auth_router.py` | Authentication | `/api/v1/auth/*` |
| `accounts_router.py` | Account management | `/api/v1/accounts/*` |
| `users_router.py` | User management | `/api/v1/users/*` |
| `roles_router.py` | Role management | `/api/v1/roles/*` |
| `permissions_router.py` | Permission management | `/api/v1/permissions/*` |
| `collections_router.py` | Collection CRUD | `/api/v1/collections/*` |
| `records_router.py` | Dynamic record CRUD | `/api/v1/{collection}/*` |
| `groups_router.py` | Group management | `/api/v1/groups/*` |
| `invitations_router.py` | User invitations | `/api/v1/invitations/*` |
| `macros_router.py` | SQL macros | `/api/v1/macros/*` |
| `dashboard_router.py` | Dashboard stats | `/api/v1/dashboard/*` |
| `audit_log_router.py` | Audit logs | `/api/v1/audit-logs/*` |
| `migrations_router.py` | DB migrations | `/api/v1/migrations/*` |

> **Screenshot Placeholder 1**
>
> **Description**: File explorer showing the routes folder with all existing router files.

---

## Architecture Review

### Layer Structure

```
Request → API Router → Service → Repository → Database
```

| Layer | Responsibility | Location |
|-------|----------------|----------|
| **API Router** | HTTP handling, validation, responses | `infrastructure/api/routes/` |
| **Service** | Business logic, orchestration | `domain/services/` or `infrastructure/services/` |
| **Repository** | Data access, database queries | `infrastructure/persistence/repositories/` |
| **Database** | Data storage | SQLAlchemy models |

> **Screenshot Placeholder 2**
>
> **Description**: A layered architecture diagram showing the flow from HTTP Request through Router, Service, Repository to Database.

### Clean Architecture Principles

- **Routers** handle HTTP concerns (status codes, headers, parsing)
- **Services** contain business logic
- **Repositories** abstract database access
- **Models** (Pydantic) define request/response schemas

> **Screenshot Placeholder 3**
>
> **Description**: A diagram showing Clean Architecture layers with dependencies pointing inward (Router → Service → Repository).

---

## Where to Add Endpoints

### Decision Tree

```
Does endpoint handle dynamic collections?
│
├── Yes → Modify records_router.py
│
└── No → Does it fit existing router?
          │
          ├── Yes → Add to existing router
          │
          └── No → Create new router
```

> **Screenshot Placeholder 4**
>
> **Description**: A flowchart showing the decision process for determining where to add new endpoints.

### When to Create a New Router

Create a new router when:
- Adding a new major feature area
- Existing routers don't match the domain concept
- The feature has 3+ related endpoints

Examples of when to create new routers:
- `/api/v1/webhooks/*` - Webhook management
- `/api/v1/scheduled-tasks/*` - Task scheduling
- `/api/v1/integrations/*` - Third-party integrations

> **Screenshot Placeholder 5**
>
> **Description**: A table showing scenarios with recommendations: use existing router vs create new router.

---

## Step-by-Step Guide

Let's add a new feature: **Tags** for organizing records.

### Step 1: Define Pydantic Schemas

Create request/response models in `infrastructure/api/schemas/`:

```python
# src/snackbase/infrastructure/api/schemas/tags.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TagBase(BaseModel):
    name: str
    color: str | None = None

class TagCreate(TagBase):
    pass

class TagUpdate(TagBase):
    name: str | None = None
    color: str | None = None

class TagResponse(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
```

> **Screenshot Placeholder 6**
>
> **Description**: Code showing the Tag schemas with annotations explaining each field.

### Step 2: Create Database Model

Add SQLAlchemy model in `infrastructure/persistence/models/`:

```python
# src/snackbase/infrastructure/persistence/models/tag.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.snackbase.infrastructure.persistence.database import Base

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # Hex color
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

> **Screenshot Placeholder 7**
>
> **Description**: Code showing the Tag SQLAlchemy model with field annotations.

### Step 3: Create Repository

Add repository in `infrastructure/persistence/repositories/`:

```python
# src/snackbase/infrastructure/persistence/repositories/tag_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.snackbase.infrastructure.persistence.models.tag import Tag
from src.snackbase.core.context import Context

class TagRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, tag: Tag) -> Tag:
        self._session.add(tag)
        await self._session.flush()
        return tag

    async def get_by_id(self, tag_id: str, context: Context) -> Tag | None:
        result = await self._session.execute(
            select(Tag).where(Tag.id == tag_id, Tag.account_id == context.account_id)
        )
        return result.scalar_one_or_none()

    async def find_all(self, context: Context) -> list[Tag]:
        result = await self._session.execute(
            select(Tag).where(Tag.account_id == context.account_id)
        )
        return list(result.scalars().all())

    async def update(self, tag: Tag) -> Tag:
        await self._session.flush()
        return tag

    async def delete(self, tag: Tag) -> None:
        await self._session.delete(tag)
        await self._session.flush()
```

> **Screenshot Placeholder 8**
>
> **Description**: Code showing the TagRepository with CRUD methods and account filtering.

### Step 4: Create API Router

Create router in `infrastructure/api/routes/`:

```python
# src/snackbase/infrastructure/api/routes/tags_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.snackbase.infrastructure.api.dependencies import (
    get_db,
    get_context,
    require_permission,
)
from src.snackbase.infrastructure.api.schemas.tags import (
    TagCreate,
    TagUpdate,
    TagResponse,
)
from src.snackbase.core.context import Context
from src.snackbase.infrastructure.persistence.repositories.tag_repository import TagRepository
from src.snackbase.infrastructure.persistence.models.tag import Tag
from src.snackbase.core.id_generator import generate_id

router = APIRouter(prefix="/tags", tags=["tags"])

@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag."""
    repo = TagRepository(db)

    tag = Tag(
        id=generate_id("tag"),
        account_id=context.account_id,
        name=tag_data.name,
        color=tag_data.color,
        created_at=datetime.nowUTC(),
        updated_at=datetime.nowUTC(),
        created_by=context.user_id,
    )

    created = await repo.create(tag)
    return TagResponse.model_validate(created)

@router.get("/", response_model=list[TagResponse])
async def list_tags(
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    """List all tags for the current account."""
    repo = TagRepository(db)
    tags = await repo.find_all(context)
    return [TagResponse.model_validate(tag) for tag in tags]

@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: str,
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific tag by ID."""
    repo = TagRepository(db)
    tag = await repo.get_by_id(tag_id, context)

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    return TagResponse.model_validate(tag)

@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    tag_data: TagUpdate,
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    """Update a tag."""
    repo = TagRepository(db)
    tag = await repo.get_by_id(tag_id, context)

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    # Update fields
    if tag_data.name is not None:
        tag.name = tag_data.name
    if tag_data.color is not None:
        tag.color = tag_data.color

    tag.updated_at = datetime.nowUTC()

    updated = await repo.update(tag)
    return TagResponse.model_validate(updated)

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: str,
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    """Delete a tag."""
    repo = TagRepository(db)
    tag = await repo.get_by_id(tag_id, context)

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    await repo.delete(tag)
```

> **Screenshot Placeholder 9**
>
> **Description**: Code showing the complete tags router with all CRUD endpoints, error handling, and dependency injection.

### Step 5: Register Router

Add the router to `app.py`:

```python
# src/snackbase/infrastructure/api/app.py
from src.snackbase.infrastructure.api.routes.tags_router import router as tags_router

# ... existing imports

app = FastAPI(title="SnackBase")

# ... existing middleware

# Register routers
app.include_router(auth_router, prefix=API_PREFIX, tags=["auth"])
app.include_router(accounts_router, prefix=API_PREFIX, tags=["accounts"])
# ... existing routers

# NEW: Add tags router BEFORE records_router
app.include_router(tags_router, prefix=API_PREFIX, tags=["tags"])

# IMPORTANT: records_router must be LAST (catches /{collection})
app.include_router(records_router, prefix=API_PREFIX, tags=["records"])
```

> **Screenshot Placeholder 10**
>
> **Description**: Code showing the app.py file with the new tags router registered, positioned before records_router with a comment explaining why.

### Step 6: Create Migration

Generate and apply database migration:

```bash
# Generate migration
uv run alembic revision --autogenerate -m "Add tags table"

# Apply migration
uv run alembic upgrade head
```

> **Screenshot Placeholder 11**
>
> **Description**: Terminal output showing Alembic migration generation and application with success messages.

### Step 7: Add Permissions (Optional)

If your feature needs authorization, add permissions:

```python
# In roles management UI or via API
{
  "role": "admin",
  "collection": "tags",
  "create": true,
  "read": true,
  "update": true,
  "delete": true
}
```

> **Screenshot Placeholder 12**
>
> **Description**: UI screenshot showing the permissions matrix with tags row added.

---

## Request/Response Patterns

### Request Body Validation

Use Pydantic for automatic validation:

```python
from pydantic import BaseModel, Field, field_validator

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    color: str | None = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('name cannot be empty or whitespace')
        return v.strip()
```

> **Screenshot Placeholder 13**
>
> **Description:** Code showing Pydantic validation with field constraints and custom validators.

### Response Formatting

Use consistent response formats:

```python
# Success response
{
  "id": "tag_abc123",
  "name": "Important",
  "color": "#ff0000",
  "account_id": "AB1001",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}

# Error response
{
  "detail": "Tag not found"
}
```

> **Screenshot Placeholder 14**
>
> **Description**: Example JSON responses showing success and error formats.

### Pagination

For list endpoints, support pagination:

```python
from fastapi import Query
from typing import Optional

@router.get("/", response_model=list[TagResponse])
async def list_tags(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    repo = TagRepository(db)
    tags = await repo.find_all(context, skip=skip, limit=limit)
    return [TagResponse.model_validate(tag) for tag in tags]
```

> **Screenshot Placeholder 15**
>
> **Description:** Code showing pagination with skip and limit query parameters.

---

## Authentication & Authorization

### Require Authentication

All endpoints automatically require authentication via `get_context()`:

```python
from src.snackbase.infrastructure.api.dependencies import get_context
from src.snackbase.core.context import Context

@router.get("/tags")
async def list_tags(
    context: Context = Depends(get_context),  # Ensures valid token
    db: AsyncSession = Depends(get_db),
):
    # context.user_id, context.account_id available
    pass
```

> **Screenshot Placeholder 16**
>
> **Description**: Code showing authentication dependency with context object highlighting user_id and account_id.

### Require Permissions

Use `require_permission()` for authorization:

```python
from src.snackbase.infrastructure.api.dependencies import require_permission

@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: str,
    authorized: bool = Depends(require_permission("tags", "delete")),
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    # Only executes if user has "tags:delete" permission
    pass
```

> **Screenshot Placeholder 17**
>
> **Description**: Code showing permission check dependency with tags:delete permission.

### Superadmin-Only Endpoints

For superadmin-only endpoints:

```python
from src.snackbase.infrastructure.api.dependencies import require_superadmin

@router.post("/accounts")
async def create_account(
    account_data: AccountCreate,
    is_superadmin: bool = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    # Only superadmins can access
    pass
```

> **Screenshot Placeholder 18**
>
> **Description**: Code showing superadmin-only endpoint with dependency.

---

## Testing Endpoints

### Unit Tests

Test router logic:

```python
# tests/unit/test_tags_router.py
import pytest
from fastapi.testclient import TestClient

from src.snackbase.infrastructure.api.app import app

client = TestClient(app)

def test_create_tag_requires_auth():
    response = client.post("/api/v1/tags/", json={"name": "Test"})
    assert response.status_code == 401

def test_create_tag_success(superadmin_token):
    response = client.post(
        "/api/v1/tags/",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": "Test", "color": "#ff0000"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

> **Screenshot Placeholder 19**
>
> **Description**: Code showing unit tests for the tags endpoint with auth and success cases.

### Integration Tests

Test full flow with database:

```python
# tests/integration/test_tags_integration.py
import pytest
from httpx import AsyncClient, ASGITransport

from src.snackbase.infrastructure.api.app import app

@pytest.mark.asyncio
async def test_create_and_retrieve_tag(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Create tag
        create_response = await client.post(
            "/api/v1/tags/",
            json={"name": "Test Tag"}
        )
        assert create_response.status_code == 201

        tag_id = create_response.json()["id"]

        # Retrieve tag
        get_response = await client.get(f"/api/v1/tags/{tag_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Test Tag"
```

> **Screenshot Placeholder 20**
>
> **Description**: Code showing integration test creating and retrieving a tag.

### Manual Testing with Swagger UI

Visit `http://localhost:8000/docs` to test endpoints interactively.

> **Screenshot Placeholder 21**
>
> **Description**: Browser screenshot of Swagger UI showing the new tags endpoints with "Try it out" button.

---

## Best Practices

### 1. Use Appropriate Status Codes

| Code | Usage | Example |
|------|-------|---------|
| 200 | Success (GET, PUT, PATCH) | Tag retrieved successfully |
| 201 | Created (POST) | Tag created successfully |
| 204 | No Content (DELETE) | Tag deleted successfully |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Tag doesn't exist |
| 422 | Unprocessable Entity | Invalid request data |

> **Screenshot Placeholder 22**
>
> **Description**: A table of HTTP status codes with usage guidelines and examples.

### 2. Account Isolation

Always filter by `account_id` in repositories:

```python
# ❌ BAD: No account filtering
async def get_by_id(self, tag_id: str) -> Tag | None:
    result = await self._session.execute(
        select(Tag).where(Tag.id == tag_id)
    )

# ✅ GOOD: Account filtering
async def get_by_id(self, tag_id: str, context: Context) -> Tag | None:
    result = await self._session.execute(
        select(Tag).where(Tag.id == tag_id, Tag.account_id == context.account_id)
    )
```

> **Screenshot Placeholder 23**
>
> **Description**: Code comparison showing bad (no filtering) vs good (account filtering) queries.

### 3. Use Dependency Injection

Inject dependencies via FastAPI's `Depends()`:

```python
# ❌ BAD: Manual dependency handling
@router.get("/tags/{tag_id}")
async def get_tag(tag_id: str, token: str):
    context = decode_token(token)  # Manual
    db = get_db()  # Manual
    ...

# ✅ GOOD: Dependency injection
@router.get("/tags/{tag_id}")
async def get_tag(
    tag_id: str,
    context: Context = Depends(get_context),  # Automatic
    db: AsyncSession = Depends(get_db),  # Automatic
):
    ...
```

> **Screenshot Placeholder 24**
>
> **Description**: Code comparison showing manual vs dependency injection approaches.

### 4. Handle Errors Gracefully

```python
@router.get("/tags/{tag_id}")
async def get_tag(
    tag_id: str,
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    repo = TagRepository(db)
    tag = await repo.get_by_id(tag_id, context)

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag {tag_id} not found"
        )

    return TagResponse.model_validate(tag)
```

> **Screenshot Placeholder 25**
>
> **Description**: Code showing proper 404 error handling with descriptive message.

### 5. Document Endpoints

Use FastAPI's docstring support:

```python
@router.post(
    "/",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tag",
    description="Creates a new tag for the current account. Tags can be used to organize and categorize records.",
    responses={
        201: {"description": "Tag created successfully"},
        400: {"description": "Invalid request data"},
        401: {"description": "Unauthorized"},
    }
)
async def create_tag(
    tag_data: TagCreate,
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag."""
    ...
```

> **Screenshot Placeholder 26**
>
> **Description**: Code showing well-documented endpoint with summary, description, and response codes.

---

## Summary

| Step | Action | Location |
|------|--------|----------|
| 1 | Define Pydantic schemas | `infrastructure/api/schemas/` |
| 2 | Create SQLAlchemy model | `infrastructure/persistence/models/` |
| 3 | Create repository | `infrastructure/persistence/repositories/` |
| 4 | Create API router | `infrastructure/api/routes/` |
| 5 | Register router | `infrastructure/api/app.py` |
| 6 | Create migration | Alembic |
| 7 | Add permissions | Via UI or API |
| 8 | Write tests | `tests/unit/`, `tests/integration/` |

---

## Related Documentation

- [Architecture](../architecture.md) - Overall system architecture
- [Testing Guide](./testing.md) - How to write tests
- [Permissions Reference](../permissions.md) - Permission rule syntax

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
