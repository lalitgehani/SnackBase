"""OAuth provider implementations."""

from snackbase.infrastructure.configuration.providers.oauth.google import (
    GoogleOAuthHandler,
)
from snackbase.infrastructure.configuration.providers.oauth.oauth_handler import (
    OAuthProviderHandler,
)

__all__ = ["OAuthProviderHandler", "GoogleOAuthHandler"]

