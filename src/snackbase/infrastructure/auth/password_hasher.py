"""Password hashing utility using Argon2.

Provides secure password hashing and verification using the Argon2id algorithm,
which is the winner of the Password Hashing Competition and recommended by OWASP.
"""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Create a password hasher with secure defaults
# Argon2id is recommended for password hashing
_hasher = PasswordHasher()

# Dummy hash for timing-safe comparison when user doesn't exist.
# This is a valid Argon2id hash that will never match any password,
# ensuring consistent response times to prevent user enumeration.
DUMMY_PASSWORD_HASH = _hasher.hash("dummy_password_for_timing_safety")


def hash_password(password: str) -> str:
    """Hash a password using Argon2id.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hashed password string.

    Example:
        >>> hashed = hash_password("SecureP@ss123!")
        >>> hashed.startswith("$argon2id$")
        True
    """
    return _hasher.hash(password)


def generate_random_password() -> str:
    """Generate a cryptographically secure random password for OAuth users.

    This password is unknowable and should only be used for hashing.
    OAuth users cannot authenticate with this password since they don't know it.

    The generated password is at least 32 characters long (typically ~43 characters)
    and uses URL-safe base64 encoding.

    Returns:
        A random URL-safe string of at least 32 characters.

    Example:
        >>> password = generate_random_password()
        >>> len(password) >= 32
        True
        >>> hashed = hash_password(password)
        >>> hashed.startswith("$argon2id$")
        True
    """
    return secrets.token_urlsafe(32)  # Generates ~43 characters


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        password: The plaintext password to verify.
        hashed: The hashed password to verify against.

    Returns:
        True if the password matches, False otherwise.

    Example:
        >>> hashed = hash_password("SecureP@ss123!")
        >>> verify_password("SecureP@ss123!", hashed)
        True
        >>> verify_password("wrong", hashed)
        False
    """
    try:
        _hasher.verify(hashed, password)
        return True
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    """Check if a password hash needs to be rehashed.

    This should be called after successful password verification.
    If True, the password should be rehashed with the current parameters.

    Args:
        hashed: The hashed password to check.

    Returns:
        True if the hash should be updated, False otherwise.
    """
    return _hasher.check_needs_rehash(hashed)
