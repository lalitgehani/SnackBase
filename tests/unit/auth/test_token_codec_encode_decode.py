import py
import pytest
import time
import secrets
from snackbase.infrastructure.auth.token_types import TokenPayload, TokenType
from snackbase.infrastructure.auth.token_codec import TokenCodec, AuthenticationError

@pytest.fixture
def secret():
    return "test-secret-key-at-least-256-bits-long-for-security"

@pytest.fixture
def sample_payload():
    return TokenPayload(
        version=1,
        type=TokenType.API_KEY,
        user_id="usr_123",
        email="test@example.com",
        account_id="acc_456",
        role="admin",
        permissions=["read", "write"],
        issued_at=int(time.time()),
        expires_at=int(time.time()) + 3600,
        token_id="tok_789"
    )

def test_encode_decode_roundtrip(sample_payload, secret):
    """Test that encoding and then decoding a payload returns the original payload."""
    token = TokenCodec.encode(sample_payload, secret)
    assert token.startswith("sb_ak.")
    
    decoded_payload = TokenCodec.decode(token, secret)
    assert decoded_payload == sample_payload
    assert decoded_payload.user_id == "usr_123"
    assert decoded_payload.type == TokenType.API_KEY

def test_decode_invalid_signature(sample_payload, secret):
    """Test that decoding fails if the signature is invalid."""
    token = TokenCodec.encode(sample_payload, secret)
    # Tamper with the signature (last part)
    parts = token.split(".")
    parts[2] = parts[2][:-1] + ("0" if parts[2][-1] != "0" else "1")
    tampered_token = ".".join(parts)
    
    with pytest.raises(AuthenticationError, match="Invalid token signature"):
        TokenCodec.decode(tampered_token, secret)
    
    # Also test tampering with the first character of the signature (definitely changes bytes)
    parts[2] = ("B" if parts[2][0] == "A" else "A") + parts[2][1:]
    tampered_token = ".".join(parts)
    with pytest.raises(AuthenticationError, match="Invalid token signature"):
        TokenCodec.decode(tampered_token, secret)

def test_decode_wrong_secret(sample_payload, secret):
    """Test that decoding fails if the wrong secret is used."""
    token = TokenCodec.encode(sample_payload, secret)
    wrong_secret = "completely-different-secret"
    
    with pytest.raises(AuthenticationError, match="Invalid token signature"):
        TokenCodec.decode(token, wrong_secret)

def test_decode_invalid_format(secret):
    """Test that decoding fails for tokens with invalid formats."""
    invalid_tokens = [
        "no-dots",
        "one.dot",
        "four.dots.too.many.parts",
        "sb_ak.invalid_payload.signature"
    ]
    
    for token in invalid_tokens:
        with pytest.raises(AuthenticationError):
            TokenCodec.decode(token, secret)

def test_decode_unknown_prefix(sample_payload, secret):
    """Test that decoding fails for tokens with unknown prefixes."""
    token = TokenCodec.encode(sample_payload, secret)
    parts = token.split(".")
    parts[0] = "unknown_prefix"
    # Re-sign for the unknown prefix to avoid signature error first
    signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
    import hmac
    from hashlib import sha256
    import base64
    signature = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
    parts[2] = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    
    invalid_token = ".".join(parts)
    
    with pytest.raises(AuthenticationError, match="Unknown token prefix"):
        TokenCodec.decode(invalid_token, secret)

def test_token_type_mismatch(sample_payload, secret):
    """Test that decoding fails if the payload type doesn't match the prefix."""
    # Create an API_KEY payload but manually use a JWT prefix
    encoded_payload = TokenCodec._base64url_encode(sample_payload.model_dump_json().encode("utf-8"))
    prefix = TokenCodec.PREFIX_MAP[TokenType.JWT]
    
    signing_input = f"{prefix}.{encoded_payload}".encode("utf-8")
    import hmac
    from hashlib import sha256
    import base64
    signature = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
    encoded_signature = TokenCodec._base64url_encode(signature)
    
    mismatched_token = f"{prefix}.{encoded_payload}.{encoded_signature}"
    
    with pytest.raises(AuthenticationError, match="Token type mismatch in payload"):
        TokenCodec.decode(mismatched_token, secret)

def test_all_token_types(secret):
    """Test all supported token types."""
    for token_type in TokenType:
        payload = TokenPayload(
            version=1,
            type=token_type,
            user_id="usr_test",
            email="test@example.com",
            account_id="acc_test",
            role="role_test",
            permissions=[],
            issued_at=int(time.time()),
            token_id="tok_test"
        )
        token = TokenCodec.encode(payload, secret)
        assert token.startswith(TokenCodec.PREFIX_MAP[token_type])
        
        decoded = TokenCodec.decode(token, secret)
        assert decoded.type == token_type
