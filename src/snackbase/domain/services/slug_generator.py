"""Slug generator service.

Generates URL-friendly slugs from text, typically account names.
Handles special characters, normalization, and validation.
"""

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class SlugValidationError:
    """Represents a slug validation error.

    Attributes:
        field: The field name (typically 'account_slug').
        message: Human-readable error message.
        code: Machine-readable error code.
    """

    field: str
    message: str
    code: str


class SlugGenerator:
    """Generate and validate URL-friendly slugs.

    Slug rules:
    - 3-32 characters
    - Alphanumeric + hyphens only
    - Must start with a letter
    - Lowercase
    """

    MIN_LENGTH = 3
    MAX_LENGTH = 32

    # Regex for valid slug format
    VALID_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")

    @classmethod
    def generate(cls, text: str) -> str:
        """Generate a slug from text.

        Args:
            text: The text to convert to a slug (e.g., account name).

        Returns:
            URL-friendly slug.

        Examples:
            >>> SlugGenerator.generate("Acme Corp")
            'acme-corp'
            >>> SlugGenerator.generate("Test & Company, Inc.")
            'test-company-inc'
            >>> SlugGenerator.generate("123 Numbers First")
            'numbers-first'
        """
        # Normalize unicode characters
        normalized = unicodedata.normalize("NFKD", text)
        # Remove non-ASCII characters
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

        # Convert to lowercase
        slug = ascii_text.lower()

        # Replace spaces and special characters with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", slug)

        # Remove leading/trailing hyphens
        slug = slug.strip("-")

        # Remove consecutive hyphens
        slug = re.sub(r"-+", "-", slug)

        # Ensure starts with a letter - remove leading digits
        slug = re.sub(r"^[0-9-]+", "", slug)

        # Truncate to max length
        if len(slug) > cls.MAX_LENGTH:
            slug = slug[: cls.MAX_LENGTH].rstrip("-")

        # If empty or too short, generate a default
        if len(slug) < cls.MIN_LENGTH:
            # This shouldn't happen often, but handle edge cases
            slug = "account"

        return slug

    @classmethod
    def validate(cls, slug: str) -> list[SlugValidationError]:
        """Validate a slug against the rules.

        Args:
            slug: The slug to validate.

        Returns:
            List of validation errors. Empty list if slug is valid.
        """
        errors: list[SlugValidationError] = []

        if len(slug) < cls.MIN_LENGTH:
            errors.append(
                SlugValidationError(
                    field="account_slug",
                    message=f"Slug must be at least {cls.MIN_LENGTH} characters",
                    code="slug_too_short",
                )
            )

        if len(slug) > cls.MAX_LENGTH:
            errors.append(
                SlugValidationError(
                    field="account_slug",
                    message=f"Slug must be at most {cls.MAX_LENGTH} characters",
                    code="slug_too_long",
                )
            )

        if not cls.VALID_SLUG_PATTERN.match(slug):
            if slug and not slug[0].isalpha():
                errors.append(
                    SlugValidationError(
                        field="account_slug",
                        message="Slug must start with a letter",
                        code="slug_invalid_start",
                    )
                )
            else:
                errors.append(
                    SlugValidationError(
                        field="account_slug",
                        message="Slug must contain only lowercase letters, numbers, and hyphens",
                        code="slug_invalid_chars",
                    )
                )

        return errors

    @classmethod
    def is_valid(cls, slug: str) -> bool:
        """Check if a slug is valid.

        Args:
            slug: The slug to validate.

        Returns:
            True if slug meets all requirements, False otherwise.
        """
        return len(cls.validate(slug)) == 0
