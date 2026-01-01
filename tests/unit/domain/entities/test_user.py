"""Unit tests for the User domain entity."""
import pytest
from datetime import datetime
from snackbase.domain.entities.user import User

def test_user_entity_creation():
    """Test creating a User entity with default values."""
    user = User(
        id="usr_123",
        account_id="acc_123",
        email="test@example.com",
        password_hash="hash",
        role_id=1
    )
    
    assert user.id == "usr_123"
    assert user.auth_provider == "password"
    assert user.auth_provider_name is None
    assert user.external_id is None
    assert user.external_email is None
    assert user.profile_data is None

def test_user_entity_oauth():
    """Test creating a User entity with OAuth details."""
    user = User(
        id="usr_123",
        account_id="acc_123",
        email="test@example.com",
        password_hash="hash",
        role_id=1,
        auth_provider="oauth",
        auth_provider_name="google",
        external_id="google_123",
        external_email="google@example.com",
        profile_data={"name": "Google User"}
    )
    
    assert user.auth_provider == "oauth"
    assert user.auth_provider_name == "google"
    assert user.external_id == "google_123"
    assert user.external_email == "google@example.com"
    assert user.profile_data == {"name": "Google User"}

def test_user_entity_invalid_provider():
    """Test that invalid auth_provider raises ValueError."""
    with pytest.raises(ValueError, match="Invalid auth_provider"):
        User(
            id="usr_123",
            account_id="acc_123",
            email="test@example.com",
            password_hash="hash",
            role_id=1,
            auth_provider="invalid_provider"
        )

def test_user_entity_missing_fields():
    """Test that missing required fields raises ValueError."""
    with pytest.raises(ValueError, match="User ID is required"):
        User(id="", account_id="acc", email="e", password_hash="p", role_id=1)
        
    with pytest.raises(ValueError, match="Account ID is required"):
        User(id="i", account_id="", email="e", password_hash="p", role_id=1)
        
    with pytest.raises(ValueError, match="Email is required"):
        User(id="i", account_id="a", email="", password_hash="p", role_id=1)
        
    with pytest.raises(ValueError, match="Password hash is required"):
        User(id="i", account_id="a", email="e", password_hash="", role_id=1)
