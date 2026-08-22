"""Shared helpers for platform (trusted-issuer) authentication tests."""

from __future__ import annotations

import time
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import ECAlgorithm, RSAAlgorithm


def generate_rsa_keypair() -> tuple[Any, Any]:
    """Return (private_key, public_key) for RS256 tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def generate_ec_keypair() -> tuple[Any, Any]:
    """Return (private_key, public_key) for ES256 tests."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


def build_jwks(public_key: Any, *, kid: str = "test-key", alg: str = "RS256") -> dict[str, Any]:
    """Build a JWKS document for the given public key."""
    if alg == "RS256":
        jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    elif alg == "ES256":
        jwk = ECAlgorithm.to_jwk(public_key, as_dict=True)
    else:
        raise ValueError(f"Unsupported alg: {alg}")

    jwk.update({"kid": kid, "use": "sig", "alg": alg})
    return {"keys": [jwk]}


def mint_platform_token(
    private_key: Any,
    *,
    issuer: str = "https://platform.example.com",
    audience: str = "snackbase-instance",
    sub: str = "platform-user-1",
    email: str = "platform@example.com",
    role: str = "admin",
    kid: str = "test-key",
    alg: str = "RS256",
    iat: int | None = None,
    exp: int | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Mint a platform-style JWT for tests."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        "email": email,
        "snackbase_role": role,
        "iat": iat if iat is not None else now,
        "exp": exp if exp is not None else now + 120,
    }
    if extra_claims:
        payload.update(extra_claims)

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, pem, algorithm=alg, headers={"kid": kid})


def platform_settings_env(
    *,
    issuer: str = "https://platform.example.com",
    jwks_url: str = "http://localhost:9999/jwks",
    audience: str = "snackbase-instance",
) -> dict[str, str]:
    """Environment overrides for an instance with platform auth enabled.

    Deliberately does not set ``SNACKBASE_SINGLE_TENANT_*``: platform principals are
    instance operators resolved into the system account, so platform auth is independent
    of instance tenancy. Every test using this helper therefore runs against a
    multi-tenant instance, which is the case that used to be unsupported.
    """
    return {
        "SNACKBASE_PLATFORM_ISSUER": issuer,
        "SNACKBASE_PLATFORM_JWKS_URL": jwks_url,
        "SNACKBASE_PLATFORM_AUDIENCE": audience,
    }
