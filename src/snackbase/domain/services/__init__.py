"""Domain services for SnackBase.

Services contain business logic that doesn't naturally fit within a single entity.
They have no dependencies on infrastructure or external frameworks.
"""

from snackbase.domain.services.account_id_generator import (
    AccountIdExhaustedError,
    AccountIdGenerator,
)
from snackbase.domain.services.password_validator import (
    PasswordValidationError,
    PasswordValidator,
    default_password_validator,
)
from snackbase.domain.services.slug_generator import (
    SlugGenerator,
    SlugValidationError,
)

__all__ = [
    "AccountIdExhaustedError",
    "AccountIdGenerator",
    "PasswordValidationError",
    "PasswordValidator",
    "SlugGenerator",
    "SlugValidationError",
    "default_password_validator",
]
