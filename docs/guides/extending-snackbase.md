# Extending SnackBase

This guide provides an overview of the various ways to extend SnackBase functionality beyond the core features.

---

## Table of Contents

- [Overview](#overview)
- [Extension Methods](#extension-methods)
- [Choosing the Right Approach](#choosing-the-right-approach)
- [Extension Points](#extension-points)
- [Architecture Considerations](#architecture-considerations)
- [Deployment Considerations](#deployment-considerations)
- [Examples](#examples)

---

## Overview

SnackBase is designed to be **extensible** at multiple levels, allowing you to add custom functionality without modifying core code.

### Extension Philosophy

| Principle                         | Description                                             |
| --------------------------------- | ------------------------------------------------------- |
| **Composition over Modification** | Add functionality through composition, not core changes |
| **Stable APIs**                   | Extension points have stable contracts                  |
| **Pluggable**                     | Features can be added/removed without affecting core    |
| **Backward Compatible**           | Extensions survive SnackBase upgrades                   |

> **Screenshot Placeholder 1**
>
> **Description**: A diagram showing the extension philosophy with icons for composition, stability, pluggability, and compatibility.

### What Can Be Extended?

| Area               | Extension Method                |
| ------------------ | ------------------------------- |
| **Business Logic** | Hooks, custom services          |
| **API Endpoints**  | New routers, middleware         |
| **Data Models**    | Custom tables, extended schemas |
| **Authentication** | Custom auth providers, MFA      |
| **Storage**        | Custom storage backends         |
| **Notifications**  | Custom notification channels    |
| **Validation**     | Custom validators, rules        |

> **Screenshot Placeholder 2**
>
> **Description**: A table showing extensibility areas with their extension methods.

---

## Extension Methods

### 1. Hooks (Recommended)

**Best for**: Business logic, event-driven automation, integrations

```python
from src.snackbase.infrastructure.api.app import app

@app.hook.on_record_after_create("posts")
async def custom_logic(record: dict, context: Context):
    """Custom business logic after post creation."""
    # Your code here
    pass
```

**Pros:**

- ✅ Stable API (v1.0 contract)
- ✅ Automatic event triggering
- ✅ Account isolation built-in
- ✅ No core modifications

**Cons:**

- ❌ Limited to defined events
- ❌ Can't add new API endpoints

> **Screenshot Placeholder 3**
>
> **Description**: Code example showing a hook registration with annotations explaining pros and cons.

### 2. Custom API Endpoints

**Best for**: New features, external integrations, custom operations

```python
from fastapi import APIRouter
from src.snackbase.infrastructure.api.app import app

custom_router = APIRouter(prefix="/custom", tags=["custom"])

@custom_router.get("/analytics")
async def get_analytics(context: Context = Depends(get_context)):
    """Custom analytics endpoint."""
    return {"analytics": "data"}

# Register in app.py
app.include_router(custom_router, prefix=API_PREFIX)
```

**Pros:**

- ✅ Full control over endpoint
- ✅ Can access all SnackBase services
- ✅ Leverage existing authentication

**Cons:**

- ❌ Must manually handle permissions
- ❌ Requires more code

> **Screenshot Placeholder 4**
>
> **Description**: Code showing custom router creation and registration.

### 3. Custom Database Tables

**Best for**: Domain-specific data, complex relationships

```python
# Create migration
# alembic/versions/xxx_add_custom_table.py

def upgrade():
    op.create_table(
        "custom_features",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("account_id", sa.String(10), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config", sa.JSON, nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"])
    )
```

**Pros:**

- ✅ Full SQL control
- ✅ Complex relationships
- ✅ Migrations versioned

**Cons:**

- ❌ Requires manual migrations
- ❌ Not auto-integrated with collections

> **Screenshot Placeholder 5**
>
> **Description**: Code showing Alembic migration for custom table.

### 4. Middleware

**Best for**: Request/response processing, logging, custom auth

```python
from src.snackbase.infrastructure.api.app import app

@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    """Custom middleware for all requests."""
    # Pre-processing
    start_time = time.time()

    # Call next middleware/route
    response = await call_next(request)

    # Post-processing
    duration = time.time() - start_time
    response.headers["X-Process-Time"] = str(duration)

    return response
```

**Pros:**

- ✅ Runs on every request
- ✅ Can modify requests/responses
- ✅ Good for cross-cutting concerns

**Cons:**

- ❌ Adds latency to all requests
- ❌ Must be carefully designed

> **Screenshot Placeholder 6**
>
> **Description**: Code showing custom middleware with timing example.

### 5. Custom Services

**Best for**: Reusable business logic, external integrations

```python
# src/snackbase/infrastructure/services/custom_service.py
from typing import Any

class CustomAnalyticsService:
    """Custom analytics service."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def calculate_metrics(self, account_id: str) -> dict[str, Any]:
        """Calculate custom metrics for account."""
        # Your logic here
        return {"metrics": "data"}

# Use in routes
@router.get("/analytics")
async def get_analytics(
    context: Context = Depends(get_context),
    db: AsyncSession = Depends(get_db)
):
    service = CustomAnalyticsService(db)
    return await service.calculate_metrics(context.account_id)
```

**Pros:**

- ✅ Encapsulates logic
- ✅ Reusable across endpoints
- ✅ Testable in isolation

**Cons:**

- ❌ More initial code

> **Screenshot Placeholder 7**
>
> **Description**: Code showing custom service class with usage in a router.

---

## Choosing the Right Approach

### Decision Tree

```
What do you want to do?
│
├── Add business logic to existing operations
│   └── → Use Hooks
│
├── Create new API endpoints
│   └── → Create Custom Router
│
├── Store custom data structures
│   │
│   ├── Simple, per-record metadata
│   │   └── → Use JSON field in existing collection
│   │
│   └── Complex, relational data
│       └── → Create Custom Table
│
├── Modify all requests/responses
│   └── → Use Middleware
│
└── Integrate external services
    └── → Create Custom Service
```

> **Screenshot Placeholder 8**
>
> **Description**: A decision tree flowchart showing how to choose the extension method based on requirements.

### Comparison Matrix

| Method                | Use Case           | Complexity | Survives Updates | Example                     |
| --------------------- | ------------------ | ---------- | ---------------- | --------------------------- |
| **Hooks**             | Event-driven logic | Low        | ✅ Yes           | Send notification on create |
| **Custom Router**     | New endpoints      | Medium     | ✅ Yes           | Custom analytics API        |
| **Custom Table**      | Complex data       | High       | ✅ Yes           | Audit log storage           |
| **Middleware**        | Request/response   | Medium     | ⚠️ Maybe         | Custom logging              |
| **Core Modification** | Framework changes  | Very High  | ❌ No            | Changing auth flow          |

> **Screenshot Placeholder 9**
>
> **Description**: A comparison table showing all extension methods with their characteristics.

---

## Extension Points

### 1. Database Layer

Extend the data layer:

```python
# Custom repository
class CustomRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def custom_query(self, account_id: str) -> list[dict]:
        """Custom database query."""
        result = await self._session.execute(
            select(CustomTable).where(
                CustomTable.account_id == account_id
            )
        )
        return [row.__dict__ for row in result.scalars()]
```

> **Screenshot Placeholder 10**
>
> **Description**: Code showing custom repository pattern.

### 2. Service Layer

Add business logic services:

```python
# src/snackbase/domain/services/analytics_service.py
class AnalyticsService:
    """Analytics business logic."""

    async def generate_report(
        self,
        account_id: str,
        date_range: DateRange
    ) -> Report:
        """Generate analytics report."""
        # Business logic here
        pass
```

> **Screenshot Placeholder 11**
>
> **Description**: Code showing domain service in Clean Architecture style.

### 3. API Layer

Extend the API:

```python
# Custom router with authentication
from src.snackbase.infrastructure.api.dependencies import (
    get_context,
    require_permission
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/report")
async def get_report(
    context: Context = Depends(get_context),
    authorized: bool = Depends(require_permission("analytics", "read"))
):
    """Get analytics report (requires permission)."""
    # Your logic
    pass
```

> **Screenshot Placeholder 12**
>
> **Description**: Code showing custom router using SnackBase dependencies.

### 4. Authentication Layer

Extend authentication:

```python
# Custom auth provider
class CustomAuthProvider:
    async def authenticate(
        self,
        credentials: dict
    ) -> AuthResult:
        """Custom authentication logic."""
        # Integrate with external auth provider
        pass

# Register in auth service
auth_service.register_provider("custom", CustomAuthProvider())
```

> **Screenshot Placeholder 13**
>
> **Description**: Code showing custom authentication provider pattern.

---

## Architecture Considerations

### Clean Architecture Principles

When extending SnackBase, follow Clean Architecture:

```
┌─────────────────────────────────────────────────────┐
│                   API Layer                         │
│  (Routers, Controllers, Middleware)                 │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                 Application Layer                   │
│  (Use Cases, Orchestration, Services)               │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                  Domain Layer                       │
│  (Entities, Business Logic, Interfaces)             │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│              Infrastructure Layer                   │
│  (Database, External APIs, Storage)                 │
└─────────────────────────────────────────────────────┘
```

> **Screenshot Placeholder 14**
>
> **Description**: A Clean Architecture diagram showing layered dependencies.

### Dependency Direction

```
✅ CORRECT: Dependencies point inward
   Router → Service → Repository → Database

❌ INCORRECT: Dependencies point outward
   Repository → Service → Router
```

> **Screenshot Placeholder 15**
>
> **Description**: Arrows showing correct (inward) vs incorrect (outward) dependency directions.

### Separation of Concerns

Keep extensions organized:

```
src/snackbase/
├── extensions/              # Your extensions
│   ├── analytics/          # Analytics feature
│   │   ├── router.py       # API endpoints
│   │   ├── service.py      # Business logic
│   │   └── repository.py   # Data access
│   └── integrations/       # External integrations
│       └── slack.py        # Slack integration
```

> **Screenshot Placeholder 16**
>
> **Description**: File explorer showing extensions folder structure with organized modules.

---

## Deployment Considerations

### Surviving Updates

| Extension Method       | Survives SnackBase Updates   |
| ---------------------- | ---------------------------- |
| **Hooks**              | ✅ Yes (stable API)          |
| **Custom Routers**     | ✅ Yes (separate files)      |
| **Custom Tables**      | ✅ Yes (separate migrations) |
| **Middleware**         | ⚠️ Maybe (if core changes)   |
| **Core Modifications** | ❌ No (will conflict)        |

> **Screenshot Placeholder 17**
>
> **Description**: A table showing extension methods and their compatibility with SnackBase updates.

### Extension Isolation

Keep extensions isolated to avoid conflicts:

```python
# ❌ BAD: Modifying core files
# src/snackbase/infrastructure/api/routes/users_router.py
# (Adding custom logic here will conflict with updates)

# ✅ GOOD: Separate extension file
# src/snackbase/extensions/custom_users.py
# (Separate file survives updates)
```

> **Screenshot Placeholder 18**
>
> **Description**: Code comparison showing bad (core modification) vs good (separate extension) approaches.

### Configuration

Use configuration for extension behavior:

```python
# .env
ENABLE_ANALYTICS_FEATURE=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
CUSTOM_API_KEY=your-key-here

# config.py
from pydantic import Settings

class ExtensionSettings(BaseSettings):
    enable_analytics: bool = False
    slack_webhook_url: str | None = None
    custom_api_key: str | None = None
```

> **Screenshot Placeholder 19**
>
> **Description**: Environment configuration and Pydantic settings for extensions.

---

## Examples

### Example 1: Analytics Dashboard

Add custom analytics:

```python
# 1. Create custom table (migration)
op.create_table(
    "page_views",
    sa.Column("id", sa.String(50), primary_key=True),
    sa.Column("account_id", sa.String(10)),
    sa.Column("path", sa.String(255)),
    sa.Column("views", sa.Integer),
    sa.Column("date", sa.Date)
)

# 2. Create service
class AnalyticsService:
    async def get_page_views(self, account_id: str, days: int = 30):
        """Get page views for last N days."""
        # Query and aggregate
        pass

# 3. Create router
@router.get("/analytics/page-views")
async def page_views(
    days: int = 30,
    context: Context = Depends(get_context)
):
    service = AnalyticsService(db)
    return await service.get_page_views(context.account_id, days)
```

> **Screenshot Placeholder 20**
>
> **Description**: Complete example showing custom table, service, and router for analytics.

### Example 2: Slack Integration

Add Slack notifications:

```python
# 1. Create hook
@app.hook.on_record_after_create("posts")
async def notify_slack(record: dict, context: Context):
    """Send Slack notification on post creation."""
    if record.get("status") == "published":
        await slack_service.send_notification(
            webhook_url=settings.slack_webhook_url,
            message=f"New post: {record['title']}"
        )

# 2. Create service
class SlackService:
    async def send_notification(self, webhook_url: str, message: str):
        """Send notification to Slack."""
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json={"text": message})
```

> **Screenshot Placeholder 21**
>
> **Description**: Complete example showing hook-based Slack integration.

### Example 3: Custom Validation

Add field validation:

```python
# 1. Create hook
@app.hook.on_record_before_create("posts")
async def validate_post_content(record: dict, context: Context):
    """Validate post content before creation."""
    content = record.get("content", "")

    # Custom validation
    if len(content) < 50:
        raise HookAbortException(
            message="Content must be at least 50 characters",
            status_code=400
        )

    # Check for prohibited words
    prohibited = ["spam", "advertisement"]
    if any(word in content.lower() for word in prohibited):
        raise HookAbortException(
            message="Content contains prohibited words",
            status_code=400
        )
```

> **Screenshot Placeholder 22**
>
> **Description**: Complete example showing custom validation hook with error handling.

### Example 4: Custom Endpoint with Permissions

Add protected endpoint:

```python
# Custom router with permissions
router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/sales")
async def sales_report(
    context: Context = Depends(get_context),
    authorized: bool = Depends(require_permission("reports", "read"))
):
    """Generate sales report (requires reports:read permission)."""
    # Generate report
    report = await report_service.generate_sales_report(context.account_id)
    return report

# Register permission
# Via UI or API:
# {
#   "role": "manager",
#   "collection": "reports",
#   "read": true,
#   "create": false,
#   "update": false,
#   "delete": false
# }
```

> **Screenshot Placeholder 23**
>
> **Description**: Complete example showing custom endpoint with permission check.

---

## Summary

| Concept                | Key Takeaway                                          |
| ---------------------- | ----------------------------------------------------- |
| **Extension Methods**  | Hooks, routers, tables, middleware, services          |
| **Choosing Approach**  | Decision tree based on requirements                   |
| **Clean Architecture** | Follow layering, dependency direction                 |
| **Deployment**         | Keep extensions isolated for updates                  |
| **Best Practices**     | Don't modify core, use configuration, test thoroughly |

---

## Related Documentation

- [Hooks Reference](../hooks.md) - Complete hooks guide
- [Adding API Endpoints](./adding-api-endpoints.md) - Custom router guide
- [Creating Custom Hooks](./creating-custom-hooks.md) - Hook development
- [Architecture](../architecture.md) - System architecture overview

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
