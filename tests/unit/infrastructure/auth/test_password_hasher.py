"""Unit tests for password hashing utilities."""

import pytest

from snackbase.infrastructure.auth.password_hasher import (
    DUMMY_PASSWORD_HASH,
    generate_random_password,
    hash_password,
    needs_rehash,
    verify_password,
)


class TestHashPassword:
    """Tests for hash_password function."""

    def test_hash_password_returns_argon2_hash(self):
        """Test that hash_password returns a valid Argon2 hash."""
        password = "SecureP@ss123!"
        hashed = hash_password(password)
        
        assert hashed.startswith("$argon2id$")
        assert len(hashed) > 50  # Argon2 hashes are long

    def test_hash_password_different_for_same_input(self):
        """Test that hashing the same password twice produces different hashes (due to salt)."""
        password = "SecureP@ss123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different due to random salt

    def test_hash_password_with_special_characters(self):
        """Test hashing passwords with special characters."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = hash_password(password)
        
        assert hashed.startswith("$argon2id$")
        assert verify_password(password, hashed)


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_verify_password_correct(self):
        """Test that correct password verification returns True."""
        password = "SecureP@ss123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password verification returns False."""
        password = "SecureP@ss123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "SecureP@ss123!"
        hashed = hash_password(password)
        
        assert verify_password("securep@ss123!", hashed) is False


class TestGenerateRandomPassword:
    """Tests for generate_random_password function."""

    def test_generate_random_password_length(self):
        """Test that generated password is at least 32 characters."""
        password = generate_random_password()
        
        assert len(password) >= 32

    def test_generate_random_password_uniqueness(self):
        """Test that generated passwords are unique."""
        passwords = [generate_random_password() for _ in range(10)]
        
        # All passwords should be unique
        assert len(set(passwords)) == 10

    def test_generate_random_password_can_be_hashed(self):
        """Test that generated password can be hashed successfully."""
        password = generate_random_password()
        hashed = hash_password(password)
        
        assert hashed.startswith("$argon2id$")
        assert verify_password(password, hashed) is True

    def test_generate_random_password_is_argon2_compatible(self):
        """Test that the hash of a random password is a valid Argon2 hash."""
        password = generate_random_password()
        hashed = hash_password(password)
        
        # Verify it's a proper Argon2id hash
        assert hashed.startswith("$argon2id$")
        assert len(hashed) > 50

    def test_generate_random_password_url_safe(self):
        """Test that generated password is URL-safe (no special chars that need encoding)."""
        password = generate_random_password()
        
        # URL-safe base64 uses only: A-Z, a-z, 0-9, -, _
        import string
        allowed_chars = string.ascii_letters + string.digits + "-_"
        assert all(c in allowed_chars for c in password)


class TestNeedsRehash:
    """Tests for needs_rehash function."""

    def test_needs_rehash_current_hash(self):
        """Test that a freshly created hash doesn't need rehashing."""
        password = "SecureP@ss123!"
        hashed = hash_password(password)
        
        # A fresh hash should not need rehashing
        assert needs_rehash(hashed) is False


class TestDummyPasswordHash:
    """Tests for DUMMY_PASSWORD_HASH constant."""

    def test_dummy_password_hash_is_valid_argon2(self):
        """Test that DUMMY_PASSWORD_HASH is a valid Argon2 hash."""
        assert DUMMY_PASSWORD_HASH.startswith("$argon2id$")

    def test_dummy_password_hash_never_matches(self):
        """Test that DUMMY_PASSWORD_HASH never matches any reasonable password."""
        test_passwords = [
            "password",
            "SecureP@ss123!",
            "admin",
            "dummy_password_for_timing_safety",
            "",
        ]
        
        for password in test_passwords:
            # Only the exact dummy password should match
            if password == "dummy_password_for_timing_safety":
                assert verify_password(password, DUMMY_PASSWORD_HASH) is True
            else:
                assert verify_password(password, DUMMY_PASSWORD_HASH) is False
