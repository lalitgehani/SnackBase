# Generic SAML Provider Setup Guide

This guide explains how to configure a generic SAML Identity Provider (IdP) for SnackBase.

## Prerequisites

- A SAML 2.0 compliant Identity Provider (e.g., Auth0, OneLogin, Keycloak, Shibboleth).
- SnackBase installed and running.

## Step 1: Get Service Provider (SP) Information from SnackBase

You will need to provide the following information to your IdP:

1. **SP Entity ID (Audience URI)**: A unique identifier for your SnackBase instance.
   - Example: `https://snackbase.yourdomain.com`
2. **Assertion Consumer Service (ACS) URL**: The endpoint where the IdP sends the SAML assertion.
   - Example: `https://snackbase.yourdomain.com/api/v1/auth/saml/acs`
3. **NameID Format**: `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress`

## Step 2: Configure your Identity Provider

1. Create a new SAML application in your IdP.
2. Input the **Entity ID** and **ACS URL** from Step 1.
3. Ensure the IdP signs the assertion (SnackBase requires signed assertions or signed responses).
4. Configure attribute mapping (optional but recommended):
   - Map user email to `email`, `mail`, or `Email`.
   - Map name to `firstName`/`lastName` or `displayName`.

## Step 3: Configure SnackBase

Collect the following information from your IdP metadata:

1. **IdP Entity ID (Issuer)**: The unique identifier of your IdP.
2. **IdP SSO URL**: The URL where SnackBase will redirect users for login.
3. **X.509 Certificate**: The public certificate used to verify the IdP's signature.

In SnackBase, configure the Generic SAML provider:

| Field                    | Description                                                                |
| ------------------------ | -------------------------------------------------------------------------- |
| `idp_entity_id`          | The Issuer URI from your IdP.                                              |
| `idp_sso_url`            | The Single Sign-On URL from your IdP.                                      |
| `idp_x509_cert`          | The public certificate (PEM format).                                       |
| `sp_entity_id`           | The Entity ID you defined in Step 1.                                       |
| `assertion_consumer_url` | The ACS URL you defined in Step 1.                                         |
| `binding`                | Set to `HTTP-Redirect` (default).                                          |
| `name_id_format`         | Set to `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress` (default). |

## Testing

1. Save your configuration.
2. Attempt to sign in via the Generic SAML SSO button.
