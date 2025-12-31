# Testing Guide

This guide explains how to write and run tests for SnackBase, covering unit tests, integration tests, and best practices.

---

## Table of Contents

- [Overview](#overview)
- [Testing Philosophy](#testing-philosophy)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Unit Tests](#writing-unit-tests)
- [Writing Integration Tests](#writing-integration-tests)
- [Test Fixtures](#test-fixtures)
- [Async Testing](#async-testing)
- [Best Practices](#best-practices)

---

## Overview

SnackBase uses **pytest** as its testing framework with comprehensive support for async operations and database testing.

### Test Stack

| Component | Purpose |
|-----------|---------|
| **pytest** | Test framework and runner |
| **pytest-asyncio** | Async test support |
| **httpx** | Async HTTP client for testing |
| **ASGITransport** | Test FastAPI without network |
| **pytest-cov** | Code coverage reporting |

> **Screenshot Placeholder 1**
>
> **Description**: A table showing the testing stack with pytest, plugins, and their purposes.

### Test Coverage Goals

| Area | Target Coverage |
|------|-----------------|
| **Core Logic** (domain/) | 90%+ |
| **Repositories** (infrastructure/persistence/) | 85%+ |
| **API Routes** (infrastructure/api/routes/) | 80%+ |
| **Services** (infrastructure/services/) | 85%+ |
| **Hooks** (infrastructure/hooks/) | 75%+ |
| **Overall** | 85%+ |

> **Screenshot Placeholder 2**
>
> **Description**: A table or bar chart showing coverage targets for different code areas.

---

## Testing Philosophy

### Test Pyramid

```
        /\
       /  \
      / E2E \        ← Few (manual/expensive)
     /--------\
    /Integration \    ← More (API/database)
   /--------------\
  /    Unit Tests   \  ← Most (fast/isolated)
 /------------------\
```

> **Screenshot Placeholder 3**
>
> **Description**: A test pyramid diagram showing many unit tests at the base, fewer integration tests in the middle, and fewest E2E tests at the top.

### Testing Principles

| Principle | Description |
|-----------|-------------|
| **Fast** | Tests should run quickly (unit tests < 1 second each) |
| **Isolated** | Tests shouldn't depend on each other |
| **Deterministic** | Same input should always produce same output |
| **Readable** | Test names should describe what they test |
| **Maintainable** | Tests should be easy to update when code changes |

> **Screenshot Placeholder 4**
>
> **Description**: A table showing testing principles with descriptions and visual icons.

---

## Test Structure

### Directory Layout

```
tests/
├── unit/                          # Unit tests (isolated)
│   ├── test_config.py            # Configuration tests
│   ├── test_id_generator.py      # ID generation tests
│   ├── test_rules_lexer.py       # Rule lexer tests
│   ├── test_rules_parser.py      # Rule parser tests
│   └── test_password_hasher.py   # Password hasher tests
│
├── integration/                   # Integration tests (API + DB)
│   ├── test_auth_endpoints.py    # Authentication API tests
│   ├── test_collections.py       # Collection CRUD tests
│   ├── test_records.py           # Record CRUD tests
│   ├── test_permissions.py       # Permission tests
│   └── test_hooks.py             # Hook integration tests
│
├── security/                      # Security-specific tests
│   ├── test_authentication.py    # Auth security tests
│   ├── test_authorization.py     # Permission security tests
│   └── test_injection.py         # SQL injection tests
│
├── conftest.py                    # Shared fixtures and configuration
└── pytest.ini                     # Pytest configuration
```

> **Screenshot Placeholder 5**
>
> **Description**: File explorer showing the tests directory structure with expanded folders and example test files.

### Test Naming Convention

Use descriptive test names that explain what is being tested:

```python
# ❌ BAD: Vague
def test_create():
    pass

def test_update():
    pass

# ✅ GOOD: Descriptive
def test_create_post_returns_201_with_valid_data():
    pass

def test_update_post_fails_with_invalid_id():
    pass

def test_update_post_requires_authentication():
    pass
```

> **Screenshot Placeholder 6**
>
> **Description**: Code comparison showing bad (vague) vs good (descriptive) test names.

---

## Running Tests

### Basic Commands

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit/

# Run integration tests only
uv run pytest tests/integration/

# Run specific test file
uv run pytest tests/unit/test_id_generator.py

# Run specific test
uv run pytest tests/unit/test_id_generator.py::test_generate_id_format

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=snackbase --cov-report=html
```

> **Screenshot Placeholder 7**
>
> **Description**: Terminal showing various pytest commands with their outputs.

### Coverage Report

```bash
# Generate HTML coverage report
uv run pytest --cov=snackbase --cov-report=html

# Open report
open htmlcov/index.html
```

> **Screenshot Placeholder 8**
>
> **Description**: Browser showing the HTML coverage report with code highlighting and percentage indicators.

### Test Discovery

Pytest automatically discovers tests:

```
Tests are discovered in files matching:
- test_*.py
- *_test.py

Test functions must:
- Start with "test_"
- Be in a discovered file

Test classes must:
- Start with "Test"
- Have methods starting with "test_"
```

> **Screenshot Placeholder 9**
>
> **Description**: A diagram showing pytest test discovery rules with file and function patterns.

---

## Writing Unit Tests

### What to Unit Test

Unit tests should cover:
- **Business logic** (domain layer)
- **Pure functions** (no side effects)
- **Data transformations**
- **Validation logic**

### Example: Testing ID Generator

```python
# tests/unit/test_id_generator.py
import pytest
from src.snackbase.core.id_generator import generate_id

class TestIDGenerator:
    """Test ID generation functionality."""

    def test_generate_id_format(self):
        """Generated ID should match XX#### format."""
        id = generate_id("test")

        assert isinstance(id, str)
        assert len(id) == 9  # XX + ####
        assert id[:2].isalpha()
        assert id[2:].isdigit()
        assert id[2:].isnumeric()

    def test_generate_id_prefix(self):
        """Generated ID should use correct prefix."""
        id = generate_id("user")

        assert id.startswith("user_")
        assert len(id) == 14  # user_ + XX####

    def test_generate_ids_are_unique(self):
        """Each generated ID should be unique."""
        ids = [generate_id("test") for _ in range(100)]

        assert len(set(ids)) == 100  # All unique

    def test_generate_id_deterministic_prefix(self):
        """Prefix should be consistent."""
        id1 = generate_id("test")
        id2 = generate_id("test")

        assert id1.startswith("test_")
        assert id2.startswith("test_")
```

> **Screenshot Placeholder 10**
>
> **Description**: Code showing a complete unit test class with multiple test methods and assertions.

### Example: Testing Rule Parser

```python
# tests/unit/test_rules_parser.py
import pytest
from src.snackbase.core.rules.parser import Parser
from src.snackbase.core.rules.ast import *

class TestRuleParser:
    """Test rule parsing functionality."""

    def test_parse_simple_comparison(self):
        """Parser should handle simple comparisons."""
        parser = Parser()

        ast = parser.parse("user.id == 'user_123'")

        assert isinstance(ast, BinaryOpNode)
        assert ast.operator == "=="
        assert isinstance(ast.left, FieldAccessNode)
        assert ast.left.field == "user.id"

    def test_parse_logical_and(self):
        """Parser should handle AND operations."""
        parser = Parser()

        ast = parser.parse("@has_role('admin') and @owns_record()")

        assert isinstance(ast, BinaryOpNode)
        assert ast.operator == "and"
        assert isinstance(ast.left, FunctionCallNode)

    def test_parse_grouping(self):
        """Parser should handle parentheses grouping."""
        parser = Parser()

        ast = parser.parse("(@has_role('a') or @has_role('b')) and status == 'draft'")

        assert isinstance(ast, BinaryOpNode)
        assert ast.operator == "and"
        assert isinstance(ast.left, BinaryOpNode)  # (a or b)
```

> **Screenshot Placeholder 11**
>
> **Description**: Code showing unit tests for the rule parser with various expression types.

---

## Writing Integration Tests

### What to Integration Test

Integration tests should cover:
- **API endpoints** (request/response)
- **Database operations** (CRUD)
- **Authentication flows**
- **Permission enforcement**
- **Hook execution**

### Example: Testing POST Endpoint

```python
# tests/integration/test_posts.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.snackbase.infrastructure.api.app import app
from src.snackbase.infrastructure.persistence.models.post import Post
from src.snackbase.core.id_generator import generate_id

@pytest.mark.asyncio
class TestPostsAPI:
    """Test posts API endpoints."""

    async def test_create_post_success(
        self,
        client: AsyncClient,
        superadmin_token: str
    ):
        """Creating a post with valid data should return 201."""
        response = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "title": "Test Post",
                "content": "This is test content",
                "status": "draft"
            }
        )

        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "Test Post"
        assert data["content"] == "This is test content"
        assert data["status"] == "draft"
        assert "id" in data
        assert "created_at" in data

    async def test_create_post_requires_auth(
        self,
        client: AsyncClient
    ):
        """Creating a post without auth should return 401."""
        response = await client.post(
            "/api/v1/posts",
            json={"title": "Test Post"}
        )

        assert response.status_code == 401

    async def test_create_post_validates_required_fields(
        self,
        client: AsyncClient,
        superadmin_token: str
    ):
        """Creating a post without required fields should return 422."""
        response = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={}  # Missing required fields
        )

        assert response.status_code == 422

        data = response.json()
        assert "detail" in data
```

> **Screenshot Placeholder 12**
>
> **Description**: Code showing integration tests for POST endpoint with success, auth, and validation cases.

### Example: Testing Permissions

```python
# tests/integration/test_permissions.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestPermissions:
    """Test permission enforcement."""

    async def test_viewer_cannot_delete_posts(
        self,
        client: AsyncClient,
        viewer_token: str,
        test_post: dict
    ):
        """Viewer role should not be able to delete posts."""
        response = await client.delete(
            f"/api/v1/posts/{test_post['id']}",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )

        assert response.status_code == 403

    async def test_editor_can_update_own_drafts(
        self,
        client: AsyncClient,
        editor_token: str,
        test_post: dict
    ):
        """Editor should be able to update their own draft posts."""
        response = await client.put(
            f"/api/v1/posts/{test_post['id']}",
            headers={"Authorization": f"Bearer {editor_token}"},
            json={"title": "Updated Title"}
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
```

> **Screenshot Placeholder 13**
>
> **Description**: Code showing permission tests for different roles and operations.

---

## Test Fixtures

Fixtures provide reusable test setup.

### Available Fixtures

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

from src.snackbase.infrastructure.api.app import app
from src.snackbase.infrastructure.persistence.database import get_db
from src.snackbase.core.config import settings

# Test database (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()

@pytest.fixture
async def db_session(engine):
    """Create test database session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    """Create test HTTP client."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
async def superadmin_token(client: AsyncClient):
    """Create and return superadmin auth token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "account": "system",
            "email": "superadmin@example.com",
            "password": "SuperAdmin123!"
        }
    )
    return response.json()["access_token"]
```

> **Screenshot Placeholder 14**
>
> **Description**: Code showing conftest.py with fixture definitions for database, client, and authentication.

### Using Fixtures

```python
@pytest.mark.asyncio
async def test_with_fixtures(
    client: AsyncClient,      # HTTP client fixture
    db_session: AsyncSession,  # Database session fixture
    superadmin_token: str      # Auth token fixture
):
    """Test using fixtures."""
    # Use client for API calls
    response = await client.get(
        "/api/v1/posts",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )

    # Use db_session for direct database access
    result = await db_session.execute(select(Post).limit(1))
    post = result.scalar_one_or_none()

    assert response.status_code == 200
    assert post is not None
```

> **Screenshot Placeholder 15**
>
> **Description**: Code showing how to use fixtures in a test with annotations.

---

## Async Testing

### Marking Async Tests

Use `@pytest.mark.asyncio` for async test functions:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Async test function."""
    result = await async_function()
    assert result is not None
```

> **Screenshot Placeholder 16**
>
> **Description**: Code showing an async test with the pytest.mark.asyncio decorator.

### Async Test Classes

```python
@pytest.mark.asyncio
class TestAsyncOperations:
    """Class containing async tests."""

    async def setup_method(self):
        """Run before each test method."""
        self.data = await load_test_data()

    async def test_async_operation(self):
        """Test async operation."""
        result = await async_operation(self.data)
        assert result.success

    async def teardown_method(self):
        """Run after each test method."""
        await cleanup(self.data)
```

> **Screenshot Placeholder 17**
>
> **Description**: Code showing an async test class with setup and teardown methods.

---

## Best Practices

### 1. Arrange-Act-Assert Pattern

Structure tests clearly:

```python
def test_user_can_login():
    # Arrange: Set up test data
    user = create_test_user(email="test@example.com", password="password123")

    # Act: Execute the function being tested
    result = auth_service.login("test@example.com", "password123")

    # Assert: Verify the result
    assert result.success is True
    assert result.token is not None
```

> **Screenshot Placeholder 18**
>
> **Description**: Code showing the Arrange-Act-Assert pattern with color-coded sections.

### 2. Use Descriptive Assertions

```python
# ❌ BAD: Generic assertion
assert result is not None

# ✅ GOOD: Descriptive assertion
assert result.id == "user_123"
assert result.email == "test@example.com"
assert result.is_active is True
```

> **Screenshot Placeholder 19**
>
> **Description**: Code comparison showing generic vs descriptive assertions.

### 3. Test Edge Cases

```python
@pytest.mark.parametrize("input,expected", [
    ("", False),           # Empty string
    ("a", True),           # Single character
    ("a" * 1000, True),    # Long string
    ("   spaces   ", True), # Whitespace
    (None, False),         # None value
])
def test_validate_email(input, expected):
    """Test email validation with various inputs."""
    result = validate_email(input)
    assert result == expected
```

> **Screenshot Placeholder 20**
>
> **Description**: Code showing parametrized tests for edge cases with a table of inputs and expected outputs.

### 4. Mock External Dependencies

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_send_notification():
    """Test notification sending with mocked external API."""
    # Mock the external service
    with patch("src.snackbase.services.notification_service.send_email") as mock_send:
        mock_send.return_value = AsyncMock(return_value=True)

        # Call the function
        await send_user_notification("user_123", "Test message")

        # Verify the mock was called
        mock_send.assert_called_once_with(
            email="user@example.com",
            subject="Notification",
            body="Test message"
        )
```

> **Screenshot Placeholder 21**
>
> **Description**: Code showing mocking of external dependencies with unittest.mock.

### 5. Use Factory Boy for Test Data

```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory

from src.snackbase.infrastructure.persistence.models.user import User
from src.snackbase.infrastructure.persistence.models.post import Post

class UserFactory(SQLAlchemyModelFactory):
    """Factory for creating test users."""
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(lambda: generate_id("user"))
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    account_id = "AB1001"
    password_hash = "$argon2id$v=19$m=65536,t=3,p=4$test"

class PostFactory(SQLAlchemyModelFactory):
    """Factory for creating test posts."""
    class Meta:
        model = Post
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(lambda: generate_id("post"))
    account_id = "AB1001"
    title = factory.Faker("sentence")
    content = factory.Faker("paragraph")
    status = "draft"

# Use in tests
@pytest.mark.asyncio
async def test_with_factory(db_session: AsyncSession):
    """Test using factory for test data."""
    post = await PostFactory.create_async(
        title="Custom Title",
        status="published"
    )

    assert post.title == "Custom Title"
    assert post.status == "published"
```

> **Screenshot Placeholder 22**
>
> **Description**: Code showing factory boy usage for creating test data.

### 6. Run Tests Frequently

```bash
# Run tests on file save (using pytest-watch)
uv pip install pytest-watch
ptw

# Or use pytest-xdist for parallel runs
uv run pytest -n auto
```

> **Screenshot Placeholder 23**
>
> **Description**: Terminal showing pytest-watch running tests automatically on file changes.

---

## Summary

| Concept | Key Takeaway |
|---------|--------------|
| **Test Framework** | pytest with pytest-asyncio for async tests |
| **Test Structure** | tests/unit/, tests/integration/, tests/security/ |
| **Unit Tests** | Test business logic, pure functions, validation |
| **Integration Tests** | Test API endpoints, database operations, permissions |
| **Fixtures** | Reusable test setup (db_session, client, tokens) |
| **Async Testing** | Use @pytest.mark.asyncio decorator |
| **Best Practices** | Arrange-Act-Assert, descriptive assertions, edge cases, mocks |

---

## Related Documentation

- [Adding API Endpoints](./adding-api-endpoints.md) - Testing new endpoints
- [Creating Custom Hooks](./creating-custom-hooks.md) - Testing hooks
- [Writing Rules](./writing-rules.md) - Testing permission rules

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
