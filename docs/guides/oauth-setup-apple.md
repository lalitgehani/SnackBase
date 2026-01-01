# Apple OAuth Setup Guide

This guide explains how to configure Sign in with Apple for SnackBase.

## Prerequisites

- An Apple Developer account.
- SnackBase installed and running on a domain with HTTPS (Apple requires HTTPS).

## Step 1: Create an App ID

1. Log in to the [Apple Developer Console](https://developer.apple.com/account/).
2. Go to **Certificates, Identifiers & Profiles** > **Identifiers**.
3. Click **+** to add a new identifier.
4. Select **App IDs**, continue.
5. Select **App**, continue.
6. Enter a **Description** and **Bundle ID**.
7. Scroll down to **Capabilities** and check **Sign In with Apple**.
8. Click **Continue** and **Register**.

## Step 2: Create a Service ID

1. Go back to **Identifiers**.
2. Click **+**, select **Service IDs**, continue.
3. Enter a **Description** and **Identifier** (e.g., `com.example.snackbase.client`).
4. Click **Continue** and **Register**.
5. Click on the newly created Service ID to edit it.
6. Enable **Sign In with Apple** and click **Configure**.
7. Select your **Primary App ID**.
8. Add your **Web Domain** (verify ownership if required).
9. Add your **Return URLs** (Redirect URIs).
   - Format: `https://<your-domain>/api/v1/auth/oauth/apple/callback`
10. Click **Save**, **Continue**, and **Save**.

## Step 3: Create a Client Secret (Private Key)

1. Go to **Keys**.
2. Click **+** to create a new key.
3. Enter a name and check **Sign In with Apple**.
4. Click **Configure**, select your Primary App ID.
5. Click **Save**, **Continue**, and **Register**.
6. **Download** the `.p8` file (save this securely, you cannot download it again).
7. Note the **Key ID**.
8. Get your **Team ID** from the top right of the developer console.

## Step 4: Configure SnackBase

In SnackBase, configure the Apple provider:

| Field           | Value                                       |
| --------------- | ------------------------------------------- |
| `client_id`     | Your Service ID Identifier (from Step 2)    |
| `team_id`       | Your Apple Team ID                          |
| `key_id`        | The Key ID (from Step 3)                    |
| `client_secret` | The contents of your `.p8` private key file |
| `redirect_uri`  | The Return URL from Step 2                  |
| `scopes`        | `name email` (default)                      |

## Testing

1. Save your configuration.
2. Attempt to sign in via the Apple button on the login page.
