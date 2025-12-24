"""Password validation service.

Validates password strength according to configurable rules:
- Minimum length
- Uppercase letter requirement
- Lowercase letter requirement
- Digit requirement
- Special character requirement
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordValidationError:
    """Represents a password validation error.

    Attributes:
        field: The field name (always 'password').
        message: Human-readable error message.
        code: Machine-readable error code.
    """

    field: str
    message: str
    code: str


class PasswordValidator:
    """Validates password strength.

    Default policy:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """

    # Default special characters
    SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~"

    def __init__(
        self,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
    ) -> None:
        """Initialize the password validator.

        Args:
            min_length: Minimum password length (default 12).
            require_uppercase: Require at least one uppercase letter.
            require_lowercase: Require at least one lowercase letter.
            require_digit: Require at least one digit.
            require_special: Require at least one special character.
        """
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special

    def validate(self, password: str) -> list[PasswordValidationError]:
        """Validate a password against the policy.

        Args:
            password: The password to validate.

        Returns:
            List of validation errors. Empty list if password is valid.
        """
        errors: list[PasswordValidationError] = []

        if len(password) < self.min_length:
            errors.append(
                PasswordValidationError(
                    field="password",
                    message=f"Password must be at least {self.min_length} characters",
                    code="password_too_short",
                )
            )

        if self.require_uppercase and not re.search(r"[A-Z]", password):
            errors.append(
                PasswordValidationError(
                    field="password",
                    message="Password must contain at least one uppercase letter",
                    code="password_no_uppercase",
                )
            )

        if self.require_lowercase and not re.search(r"[a-z]", password):
            errors.append(
                PasswordValidationError(
                    field="password",
                    message="Password must contain at least one lowercase letter",
                    code="password_no_lowercase",
                )
            )

        if self.require_digit and not re.search(r"\d", password):
            errors.append(
                PasswordValidationError(
                    field="password",
                    message="Password must contain at least one digit",
                    code="password_no_digit",
                )
            )

        if self.require_special and not re.search(f"[{self.SPECIAL_CHARS}]", password):
            errors.append(
                PasswordValidationError(
                    field="password",
                    message="Password must contain at least one special character",
                    code="password_no_special",
                )
            )

        return errors

    def is_valid(self, password: str) -> bool:
        """Check if a password is valid.

        Args:
            password: The password to validate.

        Returns:
            True if password meets all requirements, False otherwise.
        """
        return len(self.validate(password)) == 0


# Default validator instance
default_password_validator = PasswordValidator()
