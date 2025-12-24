---
activation: always_on
description: General project conventions and guidelines for SnackBase
---

# SnackBase General Guidelines

## Project Overview

SnackBase is a Python/FastAPI-based Backend-as-a-Service (BaaS) - an open-source, self-hosted alternative to PocketBase. It provides auto-generated REST APIs, multi-tenancy, row-level security, authentication, and GxP-compliant audit logging.

## Package Management

**Always use `uv`** for package management (not pip, poetry, or pdm):

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Run the application
uv run python main.py
# or
python -m snackbase serve
```

## Python Version

Python 3.12+ is required. Check `.python-version` for the exact version.

## Code Quality

- **Line length**: 100 characters max
- **Linting**: Use ruff (`ruff check`, `ruff format`)
- **Type checking**: Use mypy with strict mode enabled
- **Imports**: Use absolute imports, ordered by ruff/isort

## Testing

Run tests with:
```bash
uv run pytest
```
