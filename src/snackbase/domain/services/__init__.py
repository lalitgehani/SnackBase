"""Domain services for SnackBase.

Services contain business logic that doesn't naturally fit within a single entity.
They have no dependencies on infrastructure or external frameworks.
"""

from snackbase.domain.services.account_id_generator import (
    AccountIdExhaustedError,
    AccountIdGenerator,
)

__all__ = [
    "AccountIdExhaustedError",
    "AccountIdGenerator",
]
