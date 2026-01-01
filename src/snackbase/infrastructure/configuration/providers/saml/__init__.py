"""SAML 2.0 authentication providers."""

from snackbase.infrastructure.configuration.providers.saml.azure_ad import (
    AzureADSAMLProvider,
)
from snackbase.infrastructure.configuration.providers.saml.okta import OktaSAMLProvider
from snackbase.infrastructure.configuration.providers.saml.saml_handler import (
    SAMLProviderHandler,
)

from snackbase.infrastructure.configuration.providers.saml.generic import (
    GenericSAMLProvider,
)

__all__ = [
    "SAMLProviderHandler",
    "OktaSAMLProvider",
    "AzureADSAMLProvider",
    "GenericSAMLProvider",
]
