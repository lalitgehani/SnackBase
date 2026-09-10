"""Public projection for the ``user`` field type.

A ``user`` field stores a UUID pointing at the system ``users`` table. Expand
replaces that UUID in place with a redacted object. Password hashes, role ids,
and provider identifiers are never included.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

USER_PUBLIC_KEYS: tuple[str, ...] = (
    "id",
    "email",
    "first_name",
    "last_name",
    "avatar_url",
)

USER_REDACTED_KEYS: tuple[str, ...] = (
    "password_hash",
    "role_id",
    "auth_provider",
    "external_id",
)


def project_user_public(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return the five-key public user projection.

    ``first_name``, ``last_name``, and ``avatar_url`` are read from
    ``profile_data`` when present; missing keys are still emitted as ``None``.
    """
    profile = row.get("profile_data") or {}
    if isinstance(profile, str):
        try:
            profile = json.loads(profile)
        except json.JSONDecodeError:
            profile = {}
    if not isinstance(profile, dict):
        profile = {}

    projected = {
        "id": row.get("id"),
        "email": row.get("email"),
        "first_name": profile.get("first_name") or profile.get("given_name"),
        "last_name": profile.get("last_name") or profile.get("family_name"),
        "avatar_url": (
            profile.get("avatar_url") or profile.get("picture") or profile.get("avatar")
        ),
    }
    for key in USER_REDACTED_KEYS:
        projected.pop(key, None)
    return {key: projected.get(key) for key in USER_PUBLIC_KEYS}
