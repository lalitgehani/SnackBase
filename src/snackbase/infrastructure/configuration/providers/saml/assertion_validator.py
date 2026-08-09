"""Validation that binds a SAML assertion to this SP, this moment, and one use.

A verified signature proves only that the IdP issued the document. It says
nothing about *when* it was issued, *who* it was issued for, or whether it has
already been spent. Without the checks here, a validly-signed assertion captured
from a browser can be replayed forever, and an assertion minted for a different
service provider that shares the same IdP is accepted as if it were ours.

Replay detection is in-process. Assertion IDs are held only until the assertion's
own ``NotOnOrAfter``, which the window checks below keep to minutes, so the cache
stays small. The trade-off is that a multi-instance deployment can accept one
replay per instance inside that window; closing that fully needs a shared store
and is only worth it once the window itself is the binding constraint.
"""

import time
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from lxml.etree import _Element

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger

logger = get_logger(__name__)

SAML_NS = {
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
}

# assertion ID -> unix timestamp after which the entry may be dropped.
_seen_assertions: dict[str, float] = {}
_seen_lock = Lock()


def _localname(tag: Any) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _parse_instant(value: str) -> datetime:
    """Parse an ``xs:dateTime`` attribute into an aware UTC datetime."""
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as e:
        raise ValueError(f"Malformed SAML timestamp: {value!r}") from e

    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _claim_assertion_id(assertion_id: str, expires_at: datetime) -> None:
    """Record an assertion ID as spent, rejecting a second presentation.

    Raises:
        ValueError: If this ID has already been seen within its validity window.
    """
    now = time.time()
    with _seen_lock:
        for known, drop_after in list(_seen_assertions.items()):
            if drop_after <= now:
                del _seen_assertions[known]

        if assertion_id in _seen_assertions:
            raise ValueError("SAML Assertion has already been used (replay detected)")

        _seen_assertions[assertion_id] = expires_at.timestamp()


def validate_assertion(verified_data: _Element, config: dict[str, Any]) -> None:
    """Enforce the conditions, audience and single-use properties of an assertion.

    Args:
        verified_data: The signature-verified element — either the Response or,
            when the IdP signs the assertion rather than the response, the
            Assertion itself.
        config: Provider configuration; ``sp_entity_id`` is required and
            ``assertion_consumer_url`` is used when the IdP names a Recipient.

    Raises:
        ValueError: If the assertion is outside its validity window, was issued
            for another service provider, or has already been used.
    """
    skew = timedelta(seconds=get_settings().saml_clock_skew_seconds)
    now = datetime.now(UTC)

    assertion: _Element | None = verified_data
    if _localname(verified_data.tag) != "Assertion":
        assertion = verified_data.find(".//saml:Assertion", SAML_NS)

    if assertion is None:
        raise ValueError("SAML Response contains no signed Assertion")

    conditions = assertion.find("saml:Conditions", SAML_NS)
    if conditions is None:
        raise ValueError("SAML Assertion has no Conditions element")

    # Validity window. Without these an assertion never stops being usable.
    not_before = conditions.get("NotBefore")
    if not_before and now + skew < _parse_instant(not_before):
        raise ValueError("SAML Assertion is not yet valid (NotBefore is in the future)")

    not_on_or_after = conditions.get("NotOnOrAfter")
    if not_on_or_after and now - skew >= _parse_instant(not_on_or_after):
        raise ValueError("SAML Assertion has expired (NotOnOrAfter has passed)")

    # Audience. Without this, any SP sharing the IdP can relay its assertions here.
    audiences = [
        (node.text or "").strip()
        for node in conditions.findall("saml:AudienceRestriction/saml:Audience", SAML_NS)
    ]
    if not audiences:
        raise ValueError("SAML Assertion carries no AudienceRestriction")

    sp_entity_id = config.get("sp_entity_id")
    if sp_entity_id not in audiences:
        raise ValueError(
            "SAML Assertion audience does not include this service provider"
        )

    # Subject confirmation, when the IdP supplies it.
    subject_confirmations = assertion.findall(
        "saml:Subject/saml:SubjectConfirmation/saml:SubjectConfirmationData", SAML_NS
    )
    acs_url = config.get("assertion_consumer_url")
    for confirmation in subject_confirmations:
        expiry = confirmation.get("NotOnOrAfter")
        if expiry and now - skew >= _parse_instant(expiry):
            raise ValueError("SAML SubjectConfirmationData has expired")

        recipient = confirmation.get("Recipient")
        if recipient and acs_url and recipient != acs_url:
            raise ValueError(
                "SAML SubjectConfirmationData Recipient is not this assertion consumer URL"
            )

    # Single use. Claimed last so a rejected assertion does not burn its own ID.
    assertion_id = assertion.get("ID")
    if not assertion_id:
        raise ValueError("SAML Assertion has no ID, so replay cannot be detected")

    expires_at = _parse_instant(not_on_or_after) if not_on_or_after else now + skew
    _claim_assertion_id(assertion_id, expires_at)
