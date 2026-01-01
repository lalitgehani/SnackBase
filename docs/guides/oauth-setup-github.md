# GitHub OAuth Setup Guide

This guide explains how to configure GitHub as an OAuth 2.0 provider for SnackBase.

## Prerequisites

- A GitHub account.
- SnackBase installed and running.

## Step 1: Register a New OAuth Application

1. Go to your GitHub account **Settings**.
2. Navigate to **Developer settings** > **OAuth Apps**.
3. Click **New OAuth App**.
4. Fill in the application details:
   - **Application name**: SnackBase
   - **Homepage URL**: `https://<your-domain>`
   - **Authorization callback URL**: `https://<your-domain>/api/v1/auth/oauth/github/callback`
     - For local development: `http://localhost:8000/api/v1/auth/oauth/github/callback`

## Step 2: Generate Client Secret

1. After creating the app, you will see the **Client ID**.
2. Click **Generate a new client secret**.
3. Copy the **Client Secret**.

## Step 3: Configure SnackBase

In SnackBase, configure the GitHub provider:

| Field           | Value                                      |
| --------------- | ------------------------------------------ |
| `client_id`     | Your GitHub Client ID                      |
| `client_secret` | Your GitHub Client Secret                  |
| `redirect_uri`  | The Authorization callback URL from Step 1 |
| `scopes`        | `user:email read:user` (default)           |

## Testing

1. Save your configuration.
2. Attempt to sign in via the GitHub button on the login page.
