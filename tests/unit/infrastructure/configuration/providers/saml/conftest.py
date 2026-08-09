"""Shared assertion-building fixtures for the SAML provider unit tests.

Every provider now runs `_validate_assertion` after the signature check, so a
fixture is only a usable assertion if it carries an ID, an in-window
`Conditions` element and an `AudienceRestriction` naming this SP. These fixtures
supply that boilerplate, leaving each test focused on attribute mapping.
"""

import datetime
import uuid

import pytest


@pytest.fixture
def assertion_id() -> str:
    """A fresh assertion ID. Reusing one across tests would trip the replay cache."""
    return f"_assert_{uuid.uuid4().hex}"


@pytest.fixture
def conditions(valid_config: dict) -> str:
    """An in-window `Conditions` element restricted to the configured SP."""
    now = datetime.datetime.now(datetime.UTC)
    not_before = (now - datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    not_on_or_after = (now + datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    return (
        f'<saml:Conditions NotBefore="{not_before}" NotOnOrAfter="{not_on_or_after}">'
        f"<saml:AudienceRestriction>"
        f"<saml:Audience>{valid_config['sp_entity_id']}</saml:Audience>"
        f"</saml:AudienceRestriction>"
        f"</saml:Conditions>"
    )
