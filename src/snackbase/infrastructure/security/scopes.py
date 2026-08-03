"""API-key permission scopes for secret and privileged access.

Scopes are granted only on account-bound service API keys. They are never
implied by JWT user sessions, superadmin role, or ordinary collection rules.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable

# Scope required to reveal encrypted collection field plaintext.
SCOPE_RECORDS_SECRETS_READ = "records:secrets:read"

# All scopes that may be assigned to service API keys in this release.
APPROVED_SCOPES: frozenset[str] = frozenset(
    {
        SCOPE_RECORDS_SECRETS_READ,
    }
)


def is_approved_scope(scope: str) -> bool:
    """Return True if the scope is on the approved list."""
    return scope in APPROVED_SCOPES


def validate_scopes(scopes: Iterable[str] | None) -> list[str]:
    """Validate and normalize a list of scopes.

    Args:
        scopes: Requested scopes (may be None or empty).

    Returns:
        Deduplicated list of approved scopes in stable order.

    Raises:
        ValueError: If any scope is not approved.
    """
    if not scopes:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    unknown: list[str] = []
    for scope in scopes:
        if not isinstance(scope, str) or not scope.strip():
            unknown.append(str(scope))
            continue
        s = scope.strip()
        if s not in APPROVED_SCOPES:
            unknown.append(s)
            continue
        if s not in seen:
            seen.add(s)
            normalized.append(s)
    if unknown:
        raise ValueError(
            f"Unapproved scope(s): {', '.join(sorted(set(unknown)))}. "
            f"Approved scopes: {', '.join(sorted(APPROVED_SCOPES))}"
        )
    return normalized


def has_scope(granted: Collection[str] | None, required: str) -> bool:
    """Return True if ``required`` is present in ``granted`` scopes."""
    if not granted:
        return False
    return required in granted
