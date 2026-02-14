"""Token codec for encoding and decoding SnackBase tokens.

Implements a unified token format: <prefix>.<payload>.<signature>
Uses HMAC-SHA256 for integrity and authenticity.
"""

import base64
import hmac
import json
from hashlib import sha256
from typing import Dict

from snackbase.infrastructure.auth.token_types import TokenPayload, TokenType


class AuthenticationError(Exception):
    """Base exception for authentication-related errors."""
    pass


class TokenCodec:
    """Encode and decode SnackBase tokens with prefix-based signing."""

    # Map TokenType to its string prefix
    PREFIX_MAP = {
        TokenType.JWT: "sb_jwt",  # JWT uses sb_jwt prefix in our unified system
        TokenType.API_KEY: "sb_ak",
        TokenType.PERSONAL_TOKEN: "sb_pt",
        TokenType.OAUTH: "sb_ot",
    }

    # Reverse map for decoding
    REVERSE_PREFIX_MAP = {v: k for k, v in PREFIX_MAP.items()}

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Encode bytes to a base64url string without padding."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        """Decode a base64url string, adding padding if necessary."""
        padding = "=" * (4 - (len(data) % 4))
        return base64.urlsafe_b64decode(data + padding)

    @classmethod
    def encode(cls, payload: TokenPayload, secret: str) -> str:
        """Encode a TokenPayload into a token string.

        Format: <prefix>.<payload>.<signature>
        """
        prefix = cls.PREFIX_MAP.get(payload.type)
        if not prefix:
            raise ValueError(f"Unsupported token type: {payload.type}")

        # Serialize and encode payload
        payload_json = payload.model_dump_json()
        encoded_payload = cls._base64url_encode(payload_json.encode("utf-8"))

        # Sign: HMAC-SHA256(secret, prefix + "." + encoded_payload)
        signing_input = f"{prefix}.{encoded_payload}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
        encoded_signature = cls._base64url_encode(signature)

        return f"{prefix}.{encoded_payload}.{encoded_signature}"

    @classmethod
    def decode(cls, token: str, secret: str) -> TokenPayload:
        """Decode a token string back into a TokenPayload.

        Verifies the HMAC-SHA256 signature using constant-time comparison.
        """
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Invalid token format: must have 3 parts")

        prefix, encoded_payload, encoded_signature = parts

        # Verify signature first
        signing_input = f"{prefix}.{encoded_payload}".encode("utf-8")
        expected_signature = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
        
        try:
            actual_signature = cls._base64url_decode(encoded_signature)
        except Exception as e:
            raise AuthenticationError("Invalid signature encoding") from e

        if not hmac.compare_digest(actual_signature, expected_signature):
            raise AuthenticationError("Invalid token signature")

        # Check prefix validity
        token_type = cls.REVERSE_PREFIX_MAP.get(prefix)
        if not token_type:
            raise AuthenticationError(f"Unknown token prefix: {prefix}")

        # Decode and parse payload
        try:
            payload_json = cls._base64url_decode(encoded_payload).decode("utf-8")
            payload_dict = json.loads(payload_json)
            payload = TokenPayload(**payload_dict)
        except Exception as e:
            raise AuthenticationError("Invalid token payload") from e

        if payload.type != token_type:
            raise AuthenticationError("Token type mismatch in payload")

        return payload
