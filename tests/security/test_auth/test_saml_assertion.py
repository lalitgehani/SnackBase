"""SAML-ASRT-*: SAML assertion-validation guards (H-03).

``GenericSAMLProvider.parse_saml_response`` verifies the XML signature and then
goes straight to extracting the NameID and attributes. Everything that binds an
assertion to *this* SP, *this* moment, and *one* use is missing:

* ``Conditions/@NotBefore`` and ``@NotOnOrAfter`` are never read, so a captured
  assertion stays valid forever.
* ``AudienceRestriction`` is never read, so an assertion minted for a different
  service provider is accepted here.
* There is no replay cache, so the same assertion ID mints a session as many
  times as it is presented.

A signature check alone does not provide any of these: a validly-signed
assertion captured from a browser, or obtained from another SP that shares the
IdP, is a complete authentication bypass.

Each test signs a real assertion with a throwaway key so the signature step
genuinely passes and the failure is attributable to the missing validation.
"""

from __future__ import annotations

import base64
import datetime
import uuid
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import XMLSigner

from snackbase.infrastructure.configuration.providers.saml.generic import GenericSAMLProvider

SP_ENTITY_ID = "https://sp.snackbase.test/metadata"
OTHER_SP_ENTITY_ID = "https://attacker-sp.example.com/metadata"
IDP_ENTITY_ID = "https://idp.example.com/metadata"
USER_EMAIL = "sso-user@example.com"


def _utc(offset_minutes: int = 0) -> str:
    moment = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=offset_minutes)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(scope="module")
def idp_keypair() -> dict[str, Any]:
    """A throwaway RSA key and self-signed certificate acting as the IdP."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "snackbase-test-idp")]
    )
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )

    return {
        "key_pem": key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        "cert_pem": cert.public_bytes(serialization.Encoding.PEM),
    }


@pytest.fixture
def saml_config(idp_keypair: dict[str, Any]) -> dict[str, Any]:
    return {
        "idp_entity_id": IDP_ENTITY_ID,
        "idp_sso_url": "https://idp.example.com/sso",
        "idp_x509_cert": idp_keypair["cert_pem"].decode(),
        "sp_entity_id": SP_ENTITY_ID,
        "assertion_consumer_url": "https://sp.snackbase.test/api/v1/auth/saml/acs",
    }


def _build_response_xml(
    *,
    assertion_id: str,
    audience: str,
    not_before: str,
    not_on_or_after: str,
) -> str:
    return f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
        ID="_resp_{uuid.uuid4().hex}" Version="2.0" IssueInstant="{_utc()}">
  <saml:Issuer>{IDP_ENTITY_ID}</saml:Issuer>
  <samlp:Status>
    <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
  </samlp:Status>
  <saml:Assertion ID="{assertion_id}" Version="2.0" IssueInstant="{_utc()}">
    <saml:Issuer>{IDP_ENTITY_ID}</saml:Issuer>
    <saml:Subject>
      <saml:NameID
        Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{USER_EMAIL}</saml:NameID>
    </saml:Subject>
    <saml:Conditions NotBefore="{not_before}" NotOnOrAfter="{not_on_or_after}">
      <saml:AudienceRestriction>
        <saml:Audience>{audience}</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AttributeStatement>
      <saml:Attribute Name="email">
        <saml:AttributeValue>{USER_EMAIL}</saml:AttributeValue>
      </saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>"""


def _signed_response(
    idp_keypair: dict[str, Any],
    *,
    assertion_id: str | None = None,
    audience: str = SP_ENTITY_ID,
    not_before_minutes: int = -5,
    not_on_or_after_minutes: int = 5,
) -> str:
    """Return a Base64 SAML Response carrying a valid enveloped signature."""
    xml = _build_response_xml(
        assertion_id=assertion_id or f"_assert_{uuid.uuid4().hex}",
        audience=audience,
        not_before=_utc(not_before_minutes),
        not_on_or_after=_utc(not_on_or_after_minutes),
    )
    root = etree.fromstring(xml.encode())
    signed = XMLSigner().sign(
        root,
        key=idp_keypair["key_pem"],
        cert=idp_keypair["cert_pem"],
    )
    return base64.b64encode(etree.tostring(signed)).decode()


@pytest.fixture
def provider() -> GenericSAMLProvider:
    return GenericSAMLProvider()


# ---------------------------------------------------------------------------
# Positive control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_saml_asrt_001_valid_assertion_accepted(
    provider: GenericSAMLProvider,
    saml_config: dict[str, Any],
    idp_keypair: dict[str, Any],
) -> None:
    """SAML-ASRT-001: positive control — an in-window, correct-audience assertion works."""
    response = _signed_response(idp_keypair)

    user_info = await provider.parse_saml_response(saml_config, response)

    assert user_info["email"] == USER_EMAIL


@pytest.mark.asyncio
async def test_saml_asrt_002_tampered_assertion_rejected(
    provider: GenericSAMLProvider,
    saml_config: dict[str, Any],
    idp_keypair: dict[str, Any],
) -> None:
    """SAML-ASRT-002: regression — the signature check itself still holds."""
    response = _signed_response(idp_keypair)
    tampered = base64.b64encode(
        base64.b64decode(response).replace(
            USER_EMAIL.encode(), b"attacker@evil.example.com"
        )
    ).decode()

    with pytest.raises(ValueError, match="SAML validation failed"):
        await provider.parse_saml_response(saml_config, tampered)


# ---------------------------------------------------------------------------
# Missing condition / audience / replay validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-03 fix pending", strict=True)
async def test_saml_asrt_010_expired_assertion_rejected(
    provider: GenericSAMLProvider,
    saml_config: dict[str, Any],
    idp_keypair: dict[str, Any],
) -> None:
    """SAML-ASRT-010: `NotOnOrAfter` in the past must be rejected."""
    response = _signed_response(
        idp_keypair, not_before_minutes=-120, not_on_or_after_minutes=-60
    )

    with pytest.raises(ValueError):
        await provider.parse_saml_response(saml_config, response)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-03 fix pending", strict=True)
async def test_saml_asrt_011_not_yet_valid_assertion_rejected(
    provider: GenericSAMLProvider,
    saml_config: dict[str, Any],
    idp_keypair: dict[str, Any],
) -> None:
    """SAML-ASRT-011: `NotBefore` in the future must be rejected."""
    response = _signed_response(
        idp_keypair, not_before_minutes=60, not_on_or_after_minutes=120
    )

    with pytest.raises(ValueError):
        await provider.parse_saml_response(saml_config, response)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-03 fix pending", strict=True)
async def test_saml_asrt_012_wrong_audience_rejected(
    provider: GenericSAMLProvider,
    saml_config: dict[str, Any],
    idp_keypair: dict[str, Any],
) -> None:
    """SAML-ASRT-012: an assertion minted for another SP must be rejected."""
    response = _signed_response(idp_keypair, audience=OTHER_SP_ENTITY_ID)

    with pytest.raises(ValueError):
        await provider.parse_saml_response(saml_config, response)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="H-03 fix pending", strict=True)
async def test_saml_asrt_013_replayed_assertion_rejected(
    provider: GenericSAMLProvider,
    saml_config: dict[str, Any],
    idp_keypair: dict[str, Any],
) -> None:
    """SAML-ASRT-013: presenting the same assertion ID twice must be rejected."""
    assertion_id = f"_assert_{uuid.uuid4().hex}"
    response = _signed_response(idp_keypair, assertion_id=assertion_id)

    first = await provider.parse_saml_response(saml_config, response)
    assert first["email"] == USER_EMAIL

    with pytest.raises(ValueError):
        await provider.parse_saml_response(saml_config, response)
