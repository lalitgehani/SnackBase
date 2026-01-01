# Azure AD SAML Setup Guide

This guide explains how to configure Azure Active Directory (Microsoft Entra ID) as a SAML Identity Provider (IdP) for SnackBase.

## Prerequisites

- Administrator access to your Azure AD tenant.
- SnackBase installed and running.

## Step 1: Create an Enterprise Application

1. Log in to the [Azure Portal](https://portal.azure.com/).
2. Navigate to **Microsoft Entra ID** > **Enterprise applications**.
3. Click **New application**.
4. Click **Create your own application**.
5. Enter a name (e.g., "SnackBase") and select **Integrate any other application you don't find in the gallery (Non-gallery)**.
6. Click **Create**.

## Step 2: Set up Single Sign-On

1. In your new application, go to **Single sign-on** in the left menu.
2. Select **SAML**.

## Step 3: Configure Basic SAML Configuration

Click **Edit** on the **Basic SAML Configuration** card.

1. **Identifier (Entity ID)**: Enter a unique identifier for SnackBase.
   - Format: `https://<your-domain>` (must match `sp_entity_id` in SnackBase).
2. **Reply URL (Assertion Consumer Service URL)**: Enter your SnackBase ACS URL.
   - Format: `https://<your-domain>/api/v1/auth/saml/acs`
3. Click **Save**.

## Step 4: Configure Attributes & Claims

Click **Edit** on the **Attributes & Claims** card.

Ensure the following claims are present (Azure AD usually adds them by default):

- `emailaddress` or `name` (user principal name) for email.
- `givenname` and `surname` for name mapping.

## Step 5: Configure SnackBase

1. On the **SAML-based Sign-on** page, scroll down to **SAML Certificates**.
2. Download **Certificate (Base64)**. open it in a text editor to copy the content.
3. Scroll down to the **Set up <App Name>** section.
4. In SnackBase, create a new SAML provider configuration with the following values:

| SnackBase Field          | Azure AD Value                                   |
| ------------------------ | ------------------------------------------------ |
| `idp_entity_id`          | **Azure AD Identifier**                          |
| `idp_sso_url`            | **Login URL**                                    |
| `idp_x509_cert`          | Content of the **Certificate (Base64)** file     |
| `sp_entity_id`           | The **Identifier (Entity ID)** you set in Step 3 |
| `assertion_consumer_url` | The **Reply URL** you set in Step 3              |

## Testing

1. Save your configuration in SnackBase.
2. Assign a user to the application in Azure AD (Users and groups > Add user/group).
3. Attempt to sign in via the SAML SSO button.
