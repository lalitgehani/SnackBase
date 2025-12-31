# Developer Guides

Practical guides for common development tasks when building with or extending SnackBase.

---

## Available Guides

| Guide | Description | Screenshots |
|-------|-------------|-------------|
| [Adding API Endpoints](./adding-api-endpoints.md) | Create new API endpoints following SnackBase patterns | 26 |
| [Creating Custom Hooks](./creating-custom-hooks.md) | Build event-driven automation with hooks | 26 |
| [Writing Permission Rules](./writing-rules.md) | Define fine-grained access control rules | 33 |
| [Testing Guide](./testing.md) | Write unit and integration tests | 23 |
| [Extending SnackBase](./extending-snackbase.md) | Overview of extension methods and patterns | 23 |

---

## How to Use These Guides

### For Backend Developers

Start here to contribute to SnackBase:

1. **[Adding API Endpoints](./adding-api-endpoints.md)** - Add new features and endpoints
2. **[Creating Custom Hooks](./creating-custom-hooks.md)** - Add business logic automation
3. **[Testing Guide](./testing.md)** - Ensure code quality with tests
4. **[Writing Permission Rules](./writing-rules.md)** - Implement access control

### For Extension Developers

Extend SnackBase for your needs:

1. **[Extending SnackBase](./extending-snackbase.md)** - Overview of extension options
2. **[Creating Custom Hooks](./creating-custom-hooks.md)** - Event-driven extensions
3. **[Adding API Endpoints](./adding-api-endpoints.md)** - Add custom APIs
4. **[Testing Guide](./testing.md)** - Test your extensions

### For Contributors

Follow these guides when contributing:

- **Code Style**: Follow existing patterns in routers, services, repositories
- **Testing**: Write tests for all new code (target 85%+ coverage)
- **Documentation**: Update docs for new features
- **Hooks**: Use hooks for business logic, not core modifications

---

## Quick Reference

### Adding a New Feature

```
1. Define Pydantic schemas (infrastructure/api/schemas/)
2. Create SQLAlchemy model (infrastructure/persistence/models/)
3. Create repository (infrastructure/persistence/repositories/)
4. Create service (domain/services/ or infrastructure/services/)
5. Create API router (infrastructure/api/routes/)
6. Register router (infrastructure/api/app.py)
7. Create migration (Alembic)
8. Write tests (tests/unit/, tests/integration/)
```

> **Screenshot Placeholder 1**
>
> **Description**: A flowchart showing the 8-step process for adding a new feature.

### Creating a Hook

```python
from src.snackbase.infrastructure.api.app import app

@app.hook.on_record_after_create("posts", priority=10)
async def my_hook(record: dict, context: Context):
    """Custom logic after post creation."""
    # Your code here
    pass
```

> **Screenshot Placeholder 2**
>
> **Description**: Code snippet showing minimal hook registration.

### Writing a Permission Rule

```python
# Rule examples
@owns_record() and record.status == "draft"
@has_role("admin") or @owns_record()
not record.locked and @has_any_role(["editor", "publisher"])
```

> **Screenshot Placeholder 3**
>
> **Description**: Code snippets showing common permission rule patterns.

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=snackbase --cov-report=html

# Specific file
uv run pytest tests/unit/test_id_generator.py
```

> **Screenshot Placeholder 4**
>
> **Description**: Terminal showing pytest commands.

---

## Common Tasks

| Task | Guide | Section |
|------|-------|---------|
| Add new API endpoint | [Adding API Endpoints](./adding-api-endpoints.md) | Step-by-Step |
| Send notifications on events | [Creating Custom Hooks](./creating-custom-hooks.md) | Examples |
| Implement access control | [Writing Permission Rules](./writing-rules.md) | Rule Examples |
| Test new functionality | [Testing Guide](./testing.md) | Writing Tests |
| Extend SnackBase | [Extending SnackBase](./extending-snackbase.md) | Extension Methods |

---

## Development Workflow

### 1. Set Up Development Environment

```bash
# Clone and install
git clone <repository-url>
cd SnackBase
uv sync

# Initialize database
uv run python -m snackbase init-db

# Create superadmin
uv run python -m snackbase create-superadmin

# Start dev server
uv run python -m snackbase serve --reload
```

### 2. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 3. Implement and Test

```bash
# Write code
# Write tests
uv run pytest

# Check formatting
uv run ruff format .
uv run ruff check .

# Type check
uv run mypy src/
```

### 4. Commit and Push

```bash
git add .
git commit -m "feat: add your feature"
git push origin feature/your-feature-name
```

---

## Best Practices

### Code Organization

- **Follow Clean Architecture**: Keep dependencies pointing inward
- **Use Repository Pattern**: Abstract database access
- **Service Layer for Logic**: Business logic in services, not routers
- **Separate Concerns**: One responsibility per module

### Testing

- **Test Coverage**: Aim for 85%+ coverage
- **Unit Tests**: Test business logic in isolation
- **Integration Tests**: Test API endpoints with database
- **Async Tests**: Use `@pytest.mark.asyncio`

### Documentation

- **Docstrings**: Document all public functions/classes
- **Type Hints**: Use Python type hints
- **Comments**: Explain why, not what
- **Updates**: Keep docs in sync with code

---

## Contributing

Want to contribute to SnackBase?

1. **Read These Guides**: Understand the patterns
2. **Check Issues**: Find good first issues
3. **Start Small**: Fix bugs, add tests, improve docs
4. **Discuss First**: Open issue for major changes
5. **Follow Standards**: Code style, testing, documentation

---

## Related Documentation

- **[Architecture](../architecture.md)** - Overall system architecture
- **[Conceptual Guides](../concepts/)** - Deep dives into core concepts
- **[API Examples](../api-examples.md)** - API usage examples
- **[Hooks Reference](../hooks.md)** - Complete hooks documentation

---

**Ready to build?** Start with [Adding API Endpoints](./adding-api-endpoints.md).
