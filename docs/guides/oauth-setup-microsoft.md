# Microsoft OAuth Setup Guide

This guide explains how to configure Microsoft (Azure AD) as an OAuth 2.0 provider for SnackBase.

## Prerequisites

- An Azure account.
- SnackBase installed and running.

## Step 1: Register an Application

1. Go to the [Azure Portal](https://portal.azure.com/).
2. Navigate to **Microsoft Entra ID** (formerly Azure Active Directory) > **App registrations**.
3. Click **New registration**.
4. **Name**: SnackBase.
5. **Supported account types**: Select who can use this application (e.g., "Accounts in any organizational directory and personal Microsoft accounts").
6. **Redirect URI**: Select **Web** and enter your callback URL.
   - Format: `https://<your-domain>/api/v1/auth/oauth/microsoft/callback`
   - For local development: `http://localhost:8000/api/v1/auth/oauth/microsoft/callback`
7. Click **Register**.

## Step 2: Create Client Secret

1. In the app overview, note the **Application (client) ID**.
2. Navigate to **Certificates & secrets** > **Client secrets**.
3. Click **New client secret**.
4. Add a description and expiry.
5. Copy the **Value** (not the Secret ID) immediately.

## Step 3: Configure SnackBase

In SnackBase, configure the Microsoft provider:

| Field           | Value                                                     |
| --------------- | --------------------------------------------------------- |
| `client_id`     | Your Application (client) ID                              |
| `client_secret` | Your Client Secret Value                                  |
| `tenant_id`     | `common` (for multi-tenant) or your specific Tenant ID    |
| `redirect_uri`  | The Redirect URI from Step 1                              |
| `scopes`        | `User.Read email openid profile offline_access` (default) |

## Testing

1. Save your configuration.
2. Attempt to sign in via the Microsoft button on the login page.
