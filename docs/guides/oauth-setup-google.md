# Google OAuth Setup Guide

This guide explains how to configure Google as an OAuth 2.0 provider for SnackBase.

## Prerequisites

- A Google Cloud Platform (GCP) project.
- SnackBase installed and running.

## Step 1: Configure OAuth Consent Screen

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **APIs & Services** > **OAuth consent screen**.
3. Select **User Type** (Internal or External) and click **Create**.
4. Fill in the required application information (Name, User support email, etc.).
5. Add scopes: `.../auth/userinfo.email`, `.../auth/userinfo.profile`, `openid`.
6. Add test users (if External and in Testing mode).

## Step 2: Create Credentials

1. Navigate to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. Select **Web application**.
4. **Name**: Enter "SnackBase".
5. **Authorized redirect URIs**: Add your SnackBase callback URL.
   - Format: `https://<your-domain>/api/v1/auth/oauth/google/callback`
   - For local development: `http://localhost:8000/api/v1/auth/oauth/google/callback`

## Step 3: Configure SnackBase

Copy the **Client ID** and **Client Secret** from the Google Cloud Console.

In SnackBase, configure the Google provider:

| Field           | Value                                |
| --------------- | ------------------------------------ |
| `client_id`     | Your Google Client ID                |
| `client_secret` | Your Google Client Secret            |
| `redirect_uri`  | The Redirect URI you added in Step 2 |
| `scopes`        | `openid email profile` (default)     |

## Testing

1. Save your configuration.
2. Attempt to sign in via the Google button on the login page.
