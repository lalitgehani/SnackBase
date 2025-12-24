"""Password hashing utility using Argon2.

Provides secure password hashing and verification using the Argon2id algorithm,
which is the winner of the Password Hashing Competition and recommended by OWASP.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Create a password hasher with secure defaults
# Argon2id is recommended for password hashing
_hasher = PasswordHasher()


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
