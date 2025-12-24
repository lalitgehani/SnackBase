---
trigger: model_decision
description: Domain layer rules - no external dependencies allowed
---

# Domain Layer Rules

## Absolute Rules

The domain layer must have **ZERO dependencies** on:

- `fastapi`
- `sqlalchemy`
- `pydantic` (except for validation in DTOs)
- Any `infrastructure/` modules
- Any external HTTP clients or databases

## What Belongs Here

### Entities (`domain/entities/`)

```python
# Pure Python classes representing business concepts
class Account:
    id: str  # XX#### format
    slug: str
    name: str
```

### Services (`domain/services/`)

```python
# Business logic interfaces (protocols/ABCs)
from abc import ABC, abstractmethod

class AccountService(ABC):
    @abstractmethod
    async def create_account(self, name: str, slug: str) -> Account:
        pass
```

### Value Objects

```python
# Immutable values with business meaning
@dataclass(frozen=True)
class AccountId:
    value: str  # Validates XX#### format
```

## Testing

Domain code should be testable with pure Python mocks - no database or API fixtures needed.
