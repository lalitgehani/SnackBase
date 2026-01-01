# OAuth Authentication Flow

SnackBase implements the OAuth 2.0 Authorization Code Flow with PKCE (for supported providers) and state validation for security.

## Overview

The OAuth flow allows users to sign in to SnackBase using their existing accounts from providers like Google, GitHub, Microsoft, and Apple.

## Detailed Flow

1. **Initiate Login**:

   - The frontend calls `POST /api/v1/auth/oauth/{provider}/authorize` with a `redirect_uri`.
   - SnackBase generates a secure random `state` token and stores it.
   - SnackBase returns an authorization URL for the provider.

2. **User Authorization**:

   - The user is redirected to the provider's login page.
   - The user grants permission to SnackBase.

3. **Callback Handling**:

   - The provider redirects the user back to the `redirect_uri` with a `code` and `state`.
   - The frontend forwards these parameters to `POST /api/v1/auth/oauth/{provider}/callback`.

4. **Token Exchange**:

   - SnackBase verifies the `state` token against the stored one to prevent CSRF attacks.
   - SnackBase exchanges the authorization `code` for an access token (and ID token) from the provider.

5. **User Profile Retrieval**:

   - SnackBase uses the access token to fetch user profile information (email, name).

6. **Account Creation/Login**:
   - If the email exists, the user is logged in.
   - If the email is new, a new user account is created (auto-provisioning).
   - SnackBase issues its own JWT access and refresh tokens for the session.

## Configuration

OAuth providers can be configured at:

- **System Level**: `config.yaml` or environment variables. Applies to all tenants.
- **Account Level**: Overrides via the `configs` table. Specific to a tenant account.

## Security

- **State Parameter**: Used to prevent Cross-Site Request Forgery (CSRF).
- **PKCE**: Proof Key for Code Exchange (where supported) adds protection against code interception.
- **Token Storage**: External provider tokens are used only during the callback to fetch data and are not permanently stored unless linked functionalities are enabled.
