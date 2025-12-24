
import pytest
from datetime import datetime, timedelta, timezone
import jwt # PyJWT

from snackbase.infrastructure.auth.jwt_service import JWTService, JWTError, TokenExpiredError, InvalidTokenError
from snackbase.core.config import get_settings

# Mock settings for testing
settings = get_settings()
SECRET_KEY = settings.secret_key
ALGORITHM = getattr(settings, "algorithm", "HS256")

@pytest.fixture
def jwt_service():
    return JWTService()

class TestJWTService:
    
    def test_create_access_token(self, jwt_service):
        """Test creating an access token with correct claims."""
        data = {"sub": "testuser", "user_id": "user123", "account_id": "acc123", "role": "admin", "email": "test@example.com"}
        # Note: create_access_token signature: user_id, account_id, email, role, expires_delta
        token = jwt_service.create_access_token(
            user_id="user123",
            account_id="acc123",
            email="test@example.com",
            role="admin"
        )
        
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert decoded["sub"] == "user123" # Implementation maps sub to user_id
        assert decoded["user_id"] == "user123"
        assert decoded["role"] == "admin"
        assert "exp" in decoded
        assert "iat" in decoded
        assert decoded["type"] == "access"

    def test_create_access_token_expiration(self, jwt_service):
        """Test access token expiration time."""
        expires_delta = timedelta(minutes=15)
        
        start_time = datetime.now(timezone.utc)
        token = jwt_service.create_access_token(
            user_id="user123",
            account_id="acc123",
            email="test@example.com",
            role="admin",
            expires_delta=expires_delta
        )
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        exp_timestamp = decoded["exp"]
        exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # Allow small window for execution time
        assert start_time + expires_delta - timedelta(seconds=2) <= exp_dt <= start_time + expires_delta + timedelta(seconds=2)

    def test_create_refresh_token(self, jwt_service):
        """Test creating a refresh token with correct claims."""
        token, token_id = jwt_service.create_refresh_token(
            user_id="user123",
            account_id="acc123"
        )
        
        assert token_id is not None
        
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert decoded["sub"] == "user123"
        assert decoded["user_id"] == "user123"
        assert decoded["type"] == "refresh"
        assert decoded["jti"] == token_id
        assert "exp" in decoded

    def test_decode_token_valid(self, jwt_service):
        """Test decoding a valid token."""
        token = jwt_service.create_access_token(
            user_id="user123",
            account_id="acc123",
            email="test@example.com",
            role="admin"
        )
        
        payload = jwt_service.decode_token(token)
        assert payload["sub"] == "user123"

    def test_decode_token_invalid(self, jwt_service):
        """Test decoding an invalid token raises error."""
        with pytest.raises(InvalidTokenError):
            jwt_service.decode_token("invalid_token")

    def test_validate_refresh_token(self, jwt_service):
        """Test verifying token type."""
        # Create a refresh token
        refresh_token, _ = jwt_service.create_refresh_token(
            user_id="user123",
            account_id="acc123"
        )
        
        # Should pass
        payload = jwt_service.validate_refresh_token(refresh_token)
        assert payload["type"] == "refresh"
        
        # Should behave correctly if we pass an access token
        access_token = jwt_service.create_access_token(
            user_id="user123",
            account_id="acc123",
            email="test@example.com",
            role="admin"
        )
        
        with pytest.raises(InvalidTokenError):
             jwt_service.validate_refresh_token(access_token)

    def test_validate_access_token(self, jwt_service):
        """Test verifying access token type."""
        access_token = jwt_service.create_access_token(
            user_id="user123",
            account_id="acc123",
            email="test@example.com",
            role="admin"
        )
        
        # Should pass
        payload = jwt_service.validate_access_token(access_token)
        assert payload["type"] == "access"
        
        # Should fail with refresh token
        refresh_token, _ = jwt_service.create_refresh_token(
            user_id="user123",
            account_id="acc123"
        )
        
        with pytest.raises(InvalidTokenError):
             jwt_service.validate_access_token(refresh_token)

    def test_get_expires_in(self, jwt_service):
        """Test getting remaining expiration time."""
        # Note: the get_expires_in implementation in jwt_service.py actually returns the *duration* in seconds
        # based on the delta passed, OR the default config. It doesn't parse a token.
        # def get_expires_in(self, expires_delta: timedelta | None = None) -> int:
        
        expires_delta = timedelta(hours=1) 
        expires_in = jwt_service.get_expires_in(expires_delta=expires_delta)
        assert expires_in == 3600
