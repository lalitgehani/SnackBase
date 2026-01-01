# Okta SAML Setup Guide

This guide explains how to configure Okta as a SAML Identity Provider (IdP) for SnackBase.

## Prerequisites

- Administrator access to your Okta organization.
- SnackBase installed and running.

## Step 1: Create an App Integration in Okta

1. Log in to your Okta Admin Console.
2. Go to **Applications** > **Applications**.
3. Click **Create App Integration**.
4. Select **SAML 2.0** and click **Next**.

## Step 2: General Settings

1. **App name**: Enter "SnackBase" (or your preferred name).
2. **App logo**: (Optional) Upload a logo.
3. Click **Next**.

## Step 3: Configure SAML

1. **Single Sign On URL (ACS URL)**: Enter your SnackBase ACS URL.
   - Format: `https://<your-domain>/api/v1/auth/saml/acs`
2. **Audience URI (SP Entity ID)**: Enter a unique identifier for SnackBase.
   - Format: `https://<your-domain>` (or `snackbase-app`)
   - **Note**: This value must match the `sp_entity_id` in your SnackBase configuration.
3. **Name ID format**: Select `EmailAddress`.
4. **Application username**: Select `Email`.
5. **Update application username on**: Create and update.

## Step 4: Attribute Statements (Optional but Recommended)

Add the following attribute statements to map user details:

| Name      | Name format | Value          |
| --------- | ----------- | -------------- |
| email     | Unspecified | user.email     |
| firstName | Unspecified | user.firstName |
| lastName  | Unspecified | user.lastName  |

Click **Next** and then **Finish**.

## Step 5: Configure SnackBase

1. In Okta, go to the **Sign On** tab of your new application.
2. Scroll down to **SAML Signing Certificates**.
3. Locate the active certificate and click **View SAML setup instructions**.
4. In SnackBase, create a new SAML provider configuration with the following values:

| SnackBase Field          | Okta Value                                                 |
| ------------------------ | ---------------------------------------------------------- |
| `idp_entity_id`          | **Identity Provider Issuer**                               |
| `idp_sso_url`            | **Identity Provider Single Sign-On URL**                   |
| `idp_x509_cert`          | **X.509 Certificate** (Paste the full certificate content) |
| `sp_entity_id`           | The **Audience URI** you set in Step 3                     |
| `assertion_consumer_url` | The **Single Sign On URL** you set in Step 3               |

## Testing

1. Save your configuration in SnackBase.
2. Attempt to sign in via the SAML SSO button.
