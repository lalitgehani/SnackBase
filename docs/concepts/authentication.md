# Authentication Model

SnackBase provides a comprehensive authentication system designed for multi-tenant applications. This guide explains authentication flows, token management, multi-account users, email verification, OAuth/SAML integration, and security considerations.

---

## Table of Contents

- [Overview](#overview)
- [Authentication Architecture](#authentication-architecture)
- [Account Registration](#account-registration)
- [User Registration](#user-registration)
- [Email Verification](#email-verification)
- [Login Flow](#login-flow)
- [Token Management](#token-management)
- [OAuth 2.0 Authentication](#oauth-20-authentication)
- [SAML 2.0 Authentication](#saml-20-authentication)
- [Multi-Provider Authentication](#multi-provider-authentication)
- [Multi-Account Users](#multi-account-users)
- [Security Features](#security-features)
- [Authentication Configuration](#authentication-configuration)
- [Best Practices](#best-practices)

---

## Overview

SnackBase authentication is built for **enterprise multi-account scenarios**:

| Feature                    | Description                                           |
| -------------------------- | ----------------------------------------------------- |
| **Account-Scoped Users**   | Users belong to specific accounts                     |
| **Multi-Account Support**  | Same email can exist in multiple accounts             |
| **Per-Account Passwords**  | Different passwords per (email, account) tuple        |
| **JWT Tokens**             | Access tokens (1 hour) + Refresh tokens (7 days)      |
| **Token Rotation**         | Refresh token rotation on each use with revocation    |
| **Email Verification**     | Required for login, tokens expire in 1 hour           |
| **Multi-Provider**         | Support for Password, OAuth, and SAML providers       |
| **Identity Linking**       | Link local accounts with external provider identities |
| **Timing-Safe Comparison** | Password verification resistant to timing attacks     |
| **Hierarchical Config**    | System-level and account-level provider settings      |

> **Screenshot Placeholder 1**
>
> **Description**: A high-level architecture diagram showing the authentication system components: Client, API, JWT Service, Password Hasher, Email Service, OAuth Providers, SAML Providers, Database.

---

## Authentication Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Client                              │
│  (Browser, Mobile App, CLI)                                 │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Request
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                │
│  - /auth/register (account)                                 │
│  - /auth/register (user)                                    │
│  - /auth/verify-email                                       │
│  - /auth/login                                              │
│  - /auth/refresh                                            │
│  - /auth/me                                                 │
│  - /oauth/*                                                 │
│  - /saml/*                                                  │
└────────┬────────────────────────────────────────────────────┘
         │
         ├─────────────────┬──────────────────┬──────────────┐
         ▼                 ▼                  ▼              ▼
┌─────────────────┐ ┌─────────────┐ ┌────────────┐ ┌──────────────┐
│   JWT Service   │ │   Email     │ │   OAuth    │ │    SAML      │
│  - Gen tokens   │ │   Service   │ │  Handlers  │ │   Handlers   │
│  - Validate     │ │ - Templates │ │ - Callback │ │ - ACS        │
│  - Extract ctx  │ │ - Sending   │ │ - Exchange │ │ - Parse      │
└────────┬────────┘ └──────┬──────┘ └─────┬──────┘ └──────┬───────┘
         │                │               │               │
         └────────────────┴───────────────┴───────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Password Hasher                             │
│  - Argon2id (OWASP recommended)                             │
│  - Timing-safe comparison                                   │
│  - Dummy hash for non-existent users                        │
└────────────────────────┬────────────────────────────────────┘
                         │ Store/Retrieve
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database                                  │
│  - accounts table                                           │
│  - users table (account_id, email, password_hash)           │
│  - email_verifications table                                │
│  - tokens table (refresh tokens)                            │
│  - oauth_states table                                       │
│  - configurations table (provider settings)                 │
└─────────────────────────────────────────────────────────────┘
```

> **Screenshot Placeholder 2**
>
> **Description**: A layered architecture diagram showing the flow from Client through multiple service paths (JWT, Email, OAuth, SAML) to unified database storage.

### User Identity Model

In SnackBase, a user's identity is defined by a **tuple**:

```
(email, account_id) = unique user identity
```

This means:

- `alice@acme.com` in account `AB1001` = User Identity #1
- `alice@acme.com` in account `XY2048` = User Identity #2
- These are **different users** with different passwords

> **Screenshot Placeholder 3**
>
> **Description**: A visual representation showing user identity as a tuple with two components (email, account_id), with examples of the same email in different accounts.

---

## Account Registration

Account registration creates a new tenant/workspace in SnackBase.

### Registration Flow

```
┌──────────────┐
│ Superadmin   │
│ creates new  │
│ account      │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────┐
│ POST /api/v1/accounts       │
│ {                           │
│   "name": "Acme Corp",      │
│   "slug": "acme-corp"       │
│ }                           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ System generates account ID │
│ - id: UUID (primary key)    │
│ - account_code: XX####      │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ Account record created      │
│ - id: <uuid>                │
│ - account_code: AB1001      │
│ - slug: acme-corp           │
│ - name: Acme Corp           │
└─────────────────────────────┘
```

> **Screenshot Placeholder 4**
>
> **Description**: A sequence diagram showing the account registration flow from superadmin action to account creation with UUID ID and human-readable code.

### Account ID Format

Accounts use **two identifiers**:

```python
# Example account
{
  "id": "550e8400-e29b-41d4-a716-446655440000",  # UUID (primary key)
  "account_code": "AB1001",                       # Human-readable code
  "slug": "acme-corp",                            # URL-friendly identifier
  "name": "Acme Corp"                             # Display name
}
```

**Properties:**

- **id (UUID)**: Primary key, immutable, globally unique
- **account_code (XX####)**: Human-readable format for display
  - Format: 2 letters + 4 digits (e.g., AB1001, XY2048)
  - Sequential generation for easy reference
  - Used in UI and exports
- **slug**: URL-friendly identifier for login
- **name**: Display name (not unique)

> **Screenshot Placeholder 5**
>
> **Description**: A visual breakdown of account identifiers showing UUID (primary), account_code (display), slug (URL), and name (human-readable).

---

## User Registration

User registration creates a new user within a specific account.

### Registration Flow

```
┌──────────────┐
│ User fills   │
│ registration │
│ form         │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ POST /api/v1/auth/register      │
│ {                               │
│   "account": "acme-corp",        │
│   "email": "alice@acme.com",     │
│   "password": "SecurePass123!",  │
│   "name": "Alice Johnson"        │
│ }                               │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Resolve account by slug      │
│    "acme-corp" → account_id     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Validate email uniqueness    │
│    (within account)             │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Validate password strength   │
│    - Min 8 chars                │
│    - Uppercase, lowercase       │
│    - Number, special char       │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Hash password (Argon2id)     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 5. Create user record           │
│ - id: user_abc123               │
│ - account_id: <uuid>            │
│ - email: alice@acme.com         │
│ - password_hash: <argon2 hash>  │
│ - email_verified: false         │
│ - auth_provider: "password"     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 6. Generate verification token  │
│    - SHA-256 hash               │
│    - 1 hour expiration          │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 7. Send verification email      │
│    To: alice@acme.com           │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 6**
>
> **Description**: A detailed sequence diagram showing user registration from form submission through account resolution, validation, password hashing, user creation, token generation, and email sending.

### Email Uniqueness

Email uniqueness is **scoped to account**:

```
✅ ALLOWED:
Account AB1001: alice@acme.com
Account XY2048: alice@acme.com  (Same email, different account)

❌ NOT ALLOWED:
Account AB1001: alice@acme.com
Account AB1001: alice@acme.com  (Duplicate within account)
```

> **Screenshot Placeholder 7**
>
> **Description**: A database table view showing users with the same email in different accounts (allowed) and the same email within one account (not allowed).

---

## Email Verification

Email verification is **required** before users can log in to their accounts. This ensures email address ownership and prevents account creation with invalid or fake emails.

### Verification Flow

```
┌─────────────────────────────────┐
│ User completes registration     │
│ Account created                 │
│ email_verified: false           │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ System generates verification   │
│ token (random 32-byte string)   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Token hashed with SHA-256       │
│ Stored in email_verifications   │
│ - token_hash: <sha256>          │
│ - expires_at: now() + 1 hour    │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Verification email sent         │
│ Subject: Verify your email      │
│ Contains verification link      │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ User clicks link                │
│ GET /auth/verify-email?token=...│
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Hash provided token          │
│    SHA-256(token)               │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Lookup token_hash in DB      │
│    Check not expired            │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Update user record           │
│    - email_verified: true       │
│    - email_verified_at: now()   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Delete verification token    │
│    (single-use only)            │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 5. Return success response      │
│    User can now login           │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 8**
>
> **Description**: A comprehensive sequence diagram showing the email verification flow from token generation through email sending, user clicking link, token verification, and user record update.

### Verification Token Model

```python
# Email Verification Token
{
  "id": "ev_abc123",
  "user_id": "user_xyz789",
  "token_hash": "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",  # SHA-256
  "expires_at": "2025-01-01T01:00:00Z",  # 1 hour from creation
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Security Properties:**

- Tokens are **hashed** with SHA-256 before storage (never stored in plaintext)
- Tokens **expire** after 1 hour
- Tokens are **single-use** (deleted after verification)
- Token hash uses **constant-time comparison** to prevent timing attacks

### Verification Email Templates

SnackBase uses email templates for verification emails:

```
Subject: Verify your email address

Hello {{user_name}},

Please verify your email address by clicking the link below:

{{verification_url}}

This link will expire in 1 hour.

If you didn't create an account, please ignore this email.
```

> **Screenshot Placeholder 9**
>
> **Description**: A screenshot of an actual verification email showing the template structure with user name, verification link, and expiration notice.

### Login Requirement

Users **cannot login** until their email is verified:

```python
# Login check
if not user.email_verified:
    raise HTTPException(
        status_code=401,
        detail="Email not verified. Please check your inbox."
    )
```

**Exceptions:**

- Superadmin users can be manually verified by other superadmins
- System configuration can disable email verification (not recommended)

### Resending Verification

Users can request a new verification token if the previous one expired:

```bash
# Request new verification email
POST /api/v1/auth/resend-verification
{
  "email": "alice@acme.com",
  "account": "acme-corp"
}
```

This invalidates any existing tokens and sends a new one.

---

## Login Flow

Login authenticates a user and issues JWT tokens.

### Login Process

```
┌──────────────┐
│ User enters  │
│ credentials: │
│ - account    │
│ - email      │
│ - password   │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ POST /api/v1/auth/login         │
│ {                               │
│   "account": "acme-corp",        │
│   "email": "alice@acme.com",     │
│   "password": "SecurePass123!"  │
│ }                               │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Resolve account by slug      │
│    "acme-corp" → account_id     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Find user by (email, account)│
│    WHERE email = ?              │
│      AND account_id = ?         │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Check email verification     │
│    if not verified: 401 Error   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Timing-safe password verify  │
│    argon2.verify(password_hash, │
│                provided_password)│
│    (uses dummy hash if no user) │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 5. Generate tokens              │
│    - Access token (1 hour)      │
│    - Refresh token (7 days)     │
│    - Store refresh token hash   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 6. Return tokens                │
│ {                               │
│   "access_token": "...",        │
│   "refresh_token": "...",       │
│   "token_type": "bearer",       │
│   "user": { ... }               │
│ }                               │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 10**
>
> **Description**: A comprehensive sequence diagram showing the login flow from credentials input through account resolution, user lookup, email verification check, password verification, token generation, and response.

### Timing-Safe Password Comparison

SnackBase uses **timing-safe comparison** to prevent timing attacks:

```python
# ❌ VULNERABLE: Regular comparison (timing leak)
if user.password_hash == provided_password:
    # Attacker can measure time to guess password

# ✅ SECURE: Timing-safe comparison
# Also uses dummy hash for non-existent users
if argon2.verify(user.password_hash, provided_password):
    # Constant time regardless of match

# For non-existent users:
# - Use dummy hash to prevent username enumeration
# - Still perform full Argon2 verification
# - Return same timing as invalid password
```

**Dummy Hash Strategy:**

```python
# When user doesn't exist
dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$dummy$hash"
argon2.verify(dummy_hash, provided_password)  # Always fails, but takes same time
```

> **Screenshot Placeholder 11**
>
> **Description**: A code comparison showing vulnerable (regular comparison) vs secure (timing-safe with dummy hash) password verification with timing visualization.

---

## Token Management

SnackBase uses **JWT (JSON Web Tokens)** with access and refresh tokens, with true token rotation for enhanced security.

### Token Types

| Token Type        | Lifetime | Purpose              | Storage                         | Database |
| ----------------- | -------- | -------------------- | ------------------------------- | -------- |
| **Access Token**  | 1 hour   | API requests         | localStorage/memory             | No       |
| **Refresh Token** | 7 days   | Get new access token | HttpOnly cookie or localStorage | Yes      |

> **Screenshot Placeholder 12**
>
> **Description**: A comparison table showing access token vs refresh token with their properties, lifetimes, storage locations, and database persistence.

### Access Token Structure

```json
{
  "sub": "user_abc123",           // Subject (user ID)
  "account_id": "550e8400-...",   // Account context (UUID)
  "email": "alice@acme.com",      // User email
  "role": "admin",                // User role
  "exp": 1704067200,              // Expiration timestamp
  "iat": 1704063600               // Issued at timestamp
}
```

### Refresh Token Structure

```json
{
  "sub": "user_abc123",           // Subject (user ID)
  "account_id": "550e8400-...",   // Account context (UUID)
  "jti": "token_xyz789",          // JWT ID (unique token identifier)
  "exp": 1704668400,              // Expiration timestamp (7 days)
  "iat": 1704063600               // Issued at timestamp
}
```

**The `jti` (JWT ID) claim** uniquely identifies each refresh token and is used to track revocation.

> **Screenshot Placeholder 13**
>
> **Description**: A decoded JWT refresh token showing its payload/claims with the jti field highlighted.

### Token Usage Pattern with Rotation

```
┌──────────────┐
│ Initial      │
│ Login        │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ Receive access + refresh tokens │
│ Store in secure storage         │
│ Refresh token hash stored in DB │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Use access token for API calls  │
│ Authorization: Bearer <token>   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Token expires (1 hour)          │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Use refresh token to get new    │
│ access token                    │
│ POST /api/v1/auth/refresh       │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Hash refresh token           │
│ 2. Lookup in database           │
│ 3. Verify not revoked           │
│ 4. Verify not expired           │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Generate NEW tokens:            │
│ - New access token              │
│ - New refresh token             │
│ - Mark old refresh revoked      │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Return new tokens               │
│ Old refresh token cannot be     │
│ used again (revoked)            │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 14**
>
> **Description**: A flow diagram showing the token lifecycle with rotation, highlighting how old refresh tokens are revoked when new ones are issued.

### Token Refresh with Rotation

```bash
# Refresh access token
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  // NEW!
  "token_type": "bearer"
}
```

**True Token Rotation:**

1. Old refresh token is marked as **revoked** in database
2. New refresh token is generated and stored (hash)
3. Old token cannot be used again (returns 401 if attempted)
4. Each refresh creates a new token in the chain

### Refresh Token Model

```python
# Refresh Token in Database
{
  "id": "token_xyz789",                  # Matches JWT jti claim
  "user_id": "user_abc123",
  "account_id": "550e8400-...",
  "token_hash": "<SHA-256 hash>",         # Hashed, not plaintext
  "revoked": false,                       # Revocation status
  "expires_at": "2025-01-08T00:00:00Z",   # 7 days from creation
  "created_at": "2025-01-01T00:00:00Z",
  "revoked_at": null                      # Set when revoked
}
```

**Security Benefits of Token Rotation:**

- **Stolen token detection**: If old token is used after refresh, alert user
- **Automatic expiration**: Old tokens become invalid immediately after refresh
- **Audit trail**: Track token issuance and revocation
- **Compromise containment**: Limit window of misuse

> **Screenshot Placeholder 15**
>
> **Description**: A code example showing the refresh token request/response with the token rotation flow and database update highlighted.

---

## OAuth 2.0 Authentication

SnackBase supports OAuth 2.0 / OpenID Connect authentication for popular social and enterprise identity providers.

### Supported OAuth Providers

| Provider    | Description                     |
| ----------- | ------------------------------- |
| **Google**  | Google Account login            |
| **GitHub**  | GitHub account login            |
| **Microsoft**| Microsoft / Azure AD login      |
| **Apple**   | Sign in with Apple              |

### OAuth Flow

```
┌──────────────┐
│ User clicks  │
│ "Login with  │
│ Google"      │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ GET /oauth/google/authorize     │
│ ?account=acme-corp              │
│ &client_state=abc123            │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Generate state token         │
│    - Random 32-byte string      │
│    - Hash with SHA-256          │
│    - Store in oauth_states      │
│    - expires_at: 10 minutes     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Encode RelayState            │
│    Base64(account_id, provider, │
│    client_state)                │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Redirect to Google           │
│    https://accounts.google.com/ │
│    o/oauth2/v2/auth?            │
│    client_id=...&               │
│    redirect_uri=...&            │
│    response_type=code&          │
│    scope=openid email profile&  │
│    state=<state_token>&         │
│    relay_state=<encoded>        │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ User authenticates              │
│ with Google                     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Google redirects back           │
│ GET /oauth/google/callback?     │
│   code=...&                     │
│   state=...&                    │
│   relay_state=...               │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Verify state token           │
│    - Hash provided state        │
│    - Lookup in oauth_states     │
│    - Check not expired (10 min) │
│    - Delete state (single-use)  │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Decode RelayState            │
│    Extract account_id, provider, │
│    client_state                 │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Exchange code for tokens     │
│    POST to Google token endpoint│
│    - Receive access_token,      │
│      id_token                   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Get user info                │
│    GET to Google userinfo API   │
│    - Receive email, name, picture│
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 5. Find or create user          │
│    - Lookup by (email, account) │
│    - If exists: update profile  │
│    - If not exists: create user │
│      with random password       │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 6. Update user record           │
│    - auth_provider: "oauth"     │
│    - auth_provider_name: "google"│
│    - external_id: <Google user ID>│
│    - external_email: <from Google>│
│    - profile_data: {name, picture}│
│    - email_verified: true       │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 7. Generate JWT tokens          │
│    - Access token (1 hour)      │
│    - Refresh token (7 days)     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 8. Redirect to client app       │
│    ?token=<access_token>&       │
│    state=<client_state>         │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 16**
>
> **Description**: A comprehensive sequence diagram showing the OAuth 2.0 flow from user clicking login through authorization, callback, token exchange, user info retrieval, user creation/update, and token generation.

### OAuth State Token

```python
# OAuth State Token
{
  "id": "oauth_state_abc123",
  "state": "random_32_byte_string",
  "state_hash": "<SHA-256 hash>",
  "provider": "google",
  "account_id": "550e8400-...",
  "client_state": "abc123",         # Client-provided state
  "relay_state": "<Base64 encoded>",
  "expires_at": "2025-01-01T00:10:00Z",  # 10 minutes
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Purpose:** Prevent CSRF attacks by verifying that the callback matches the authorization request.

### Auto-Provisioning

OAuth can automatically create new accounts on first login (configurable):

```python
# Configuration
{
  "provider_name": "google",
  "auto_provision": true,           # Create account if not exists
  "allowed_domains": ["acme.com"],  # Restrict to domains (optional)
  "default_role": "viewer"          # Default role for new users
}
```

When `auto_provision` is enabled:
1. New account is created with user's email domain
2. User is added to the account
3. User can immediately access the application

### OAuth User Password

Users created via OAuth receive **random, unknowable passwords**:

```python
# Generate random password (32 bytes)
random_password = secrets.token_urlsafe(32)
password_hash = argon2.hash(random_password)
```

This ensures:
- Database `password_hash` column is `NOT NULL`
- User can only authenticate via OAuth (unless password is reset)
- Security is maintained even if OAuth is disabled later

### RelayState Encoding

RelayState encodes account context and client state:

```python
# RelayState structure
relay_state_data = {
  "account_id": "550e8400-...",
  "provider_name": "google",
  "client_state": "abc123"
}

# Base64 encode
relay_state = base64.urlsafe_b64encode(
  json.dumps(relay_state_data).encode()
).decode()
```

This ensures the callback knows:
- Which account the user is logging into
- Which OAuth provider was used
- What state to return to the client

---

## SAML 2.0 Authentication

SnackBase supports SAML 2.0 for enterprise single sign-on (SSO) with identity providers like Okta, Azure AD, and other SAML-compliant systems.

### Supported SAML Providers

| Provider    | Description                     |
| ----------- | ------------------------------- |
| **Okta**    | Okta Identity Cloud SSO         |
| **Azure AD**| Microsoft Azure Active Directory|
| **Generic** | Any SAML 2.0 compliant IdP      |

### SAML Flow

```
┌──────────────┐
│ User clicks  │
│ "Login with  │
│ SSO"         │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ GET /saml/{provider}/sso        │
│ ?account=acme-corp              │
│ &client_state=abc123            │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Resolve SAML config          │
│    - Load provider settings     │
│      from configuration         │
│    - Get IdP metadata           │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Generate SAML request        │
│    - Create AuthnRequest        │
│    - Sign with SP certificate   │
│    - Generate RelayState        │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Encode RelayState            │
│    Base64(account_id, provider, │
│    client_state)                │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Redirect to IdP              │
│    SAMLRequest=<base64>         │
│    &RelayState=<base64>         │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ User authenticates              │
│ with IdP (e.g., Okta)           │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ IdP posts SAML response         │
│ POST /saml/{provider}/acs       │
│ - SAMLResponse=<base64>         │
│ - RelayState=<base64>           │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Decode RelayState            │
│    Extract account_id, provider, │
│    client_state                 │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Verify SAML response         │
│    - Validate signature         │
│    - Check not expired          │
│    - Verify destination         │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Extract user attributes      │
│    - NameID (email)             │
│    - firstName, lastName        │
│    - Other attributes           │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Find or create user          │
│    - Lookup by (email, account) │
│    - If exists: update profile  │
│    - If not exists: create user │
│      with random password       │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 5. Update user record           │
│    - auth_provider: "saml"      │
│    - auth_provider_name: "okta" │
│    - external_id: <NameID>      │
│    - external_email: <from SAML>│
│    - profile_data: {name, ...}  │
│    - email_verified: true       │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 6. Generate JWT tokens          │
│    - Access token (1 hour)      │
│    - Refresh token (7 days)     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 7. Redirect to client app       │
│    ?token=<access_token>&       │
│    state=<client_state>         │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 17**
>
> **Description**: A comprehensive sequence diagram showing the SAML 2.0 flow from user clicking SSO login through SAML request generation, IdP authentication, ACS callback, SAML response verification, user creation/update, and token generation.

### SAML Configuration

SAML providers are configured via the configuration system:

```python
# SAML Provider Configuration
{
  "provider_name": "okta",
  "provider_type": "saml",
  "enabled": true,
  "config": {
    "idp_entity_id": "https://dev-123456.okta.com",
    "idp_sso_url": "https://dev-123456.okta.com/sso/saml",
    "idp_x509_cert": "-----BEGIN CERTIFICATE-----\n...",
    "sp_entity_id": "https://yourapp.com/saml/metadata",
    "sp_acs_url": "https://yourapp.com/saml/okta/acs",
    "sp_slo_url": "https://yourapp.com/saml/okta/slo",
    "sp_x509_cert": "-----BEGIN CERTIFICATE-----\n...",
    "sp_x509_key": "-----BEGIN PRIVATE KEY-----\n...",
    "attribute_mapping": {
      "email": "NameID",
      "first_name": "firstName",
      "last_name": "lastName"
    }
  }
}
```

### SAML Metadata Endpoint

SnackBase provides a Service Provider (SP) metadata endpoint for easy IdP configuration:

```bash
# Get SP metadata
GET /saml/metadata?account=acme-corp&provider=okta
```

This returns XML metadata that can be imported into Okta, Azure AD, etc.:

```xml
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata">
  <SPSSODescriptor>
    <NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</NameIDFormat>
    <AssertionConsumerService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="https://yourapp.com/saml/okta/acs"/>
    <KeyDescriptor use="signing">
      <KeyInfo>
        <X509Data>
          <X509Certificate>...</X509Certificate>
        </X509Data>
      </KeyInfo>
    </KeyDescriptor>
  </SPSSODescriptor>
</EntityDescriptor>
```

### RelayState in SAML

SAML RelayState serves the same purpose as OAuth state:

```python
# RelayState structure
relay_state_data = {
  "account_id": "550e8400-...",
  "provider_name": "okta",
  "client_state": "abc123"
}

# Base64 encode for URL transmission
relay_state = base64.urlsafe_b64encode(
  json.dumps(relay_state_data).encode()
).decode()
```

### SAML User Attributes

User attributes are extracted from the SAML response and mapped to local user fields:

```python
# Attribute mapping example
attribute_mapping = {
  "email": "NameID",                      # SAML NameID
  "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
  "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
  "display_name": "http://schemas.microsoft.com/identity/claims/displayname"
}
```

---

## Multi-Provider Authentication

SnackBase supports multiple authentication providers simultaneously, allowing users to choose their preferred login method.

### Provider Types

| Provider Type | Description                                         |
| ------------- | --------------------------------------------------- |
| **password**  | Traditional email/password authentication (Default) |
| **oauth**     | Social login via OAuth 2.0 / OpenID Connect         |
| **saml**      | Enterprise Single Sign-On (SSO)                     |

### Tracking Provider Data

For every user, SnackBase tracks provider-specific information:

```python
# User record with provider tracking
{
  "id": "user_abc123",
  "account_id": "550e8400-...",
  "email": "alice@acme.com",
  "password_hash": "<argon2 hash>",
  "auth_provider": "oauth",              # 'password', 'oauth', or 'saml'
  "auth_provider_name": "google",        # Specific provider name
  "external_id": "123456789",            # Provider's user ID
  "external_email": "alice@gmail.com",   # Email from provider
  "profile_data": {                      # Additional profile info
    "name": "Alice Johnson",
    "picture": "https://...",
    "locale": "en"
  },
  "email_verified": true,
  "email_verified_at": "2025-01-01T00:00:00Z"
}
```

**Field Descriptions:**

- **auth_provider**: The type of provider (`password`, `oauth`, `saml`)
- **auth_provider_name**: Specific name (e.g., 'google', 'github', 'okta')
- **external_id**: Unique user ID from the external provider
- **external_email**: Email from provider (may differ from registration email)
- **profile_data**: JSON with additional profile info (name, avatar, etc.)

### Password Policy with External Providers

When a user registers via OAuth or SAML, a **random, unknowable password** is still generated:

```python
# Generate random password for OAuth/SAML users
random_password = secrets.token_urlsafe(32)
password_hash = argon2.hash(random_password)
```

This ensures:
1. The `password_hash` column remains `NOT NULL` for database consistency
2. The user can **only** authenticate via the external provider
3. Password login is **disabled** unless a superadmin manually resets the password
4. Security is maintained even if the external provider is later disabled

### Linking Multiple Providers

A user can have multiple linked providers (future feature):

```python
# User with multiple linked providers
{
  "email": "alice@acme.com",
  "auth_provider": "password",  # Primary provider
  "linked_providers": [
    {
      "provider": "google",
      "external_id": "123456789",
      "linked_at": "2025-01-01T00:00:00Z"
    },
    {
      "provider": "github",
      "external_id": "987654321",
      "linked_at": "2025-01-02T00:00:00Z"
    }
  ]
}
```

This allows users to:
- Log in with any linked provider
- Switch between authentication methods
- Maintain a single user account across providers

---

## Multi-Account Users

SnackBase supports **enterprise multi-account scenarios** where users can belong to multiple accounts.

### User Identity Matrix

```
┌────────────────────┬──────────────┬──────────────┬──────────────┐
│ email              │ account_id   │ password     │ role         │
├────────────────────┼──────────────┼──────────────┼──────────────┤
│ alice@acme.com     │ 550e8400-... │ Password1!   │ admin        │
│ alice@acme.com     │ 660e8400-... │ Password2!   │ viewer       │
│ bob@acme.com       │ 550e8400-... │ Password3!   │ editor       │
│ jane@globex.com    │ 660e8400-... │ Password4!   │ admin        │
└────────────────────┴──────────────┴──────────────┴──────────────┘
```

**Key Points:**

- Same email can exist in multiple accounts
- Each `(email, account_id)` tuple has a unique password
- Users must specify account when logging in

> **Screenshot Placeholder 18**
>
> **Description**: A database table view showing multi-account users with the same email appearing multiple times with different account_ids and passwords.

### Login with Account Selection

When logging in, users must specify which account they're accessing:

**Option 1: Account in URL (subdomain)**

```
POST https://acme-corp.snackbase.com/api/v1/auth/login
{
  "email": "alice@acme.com",
  "password": "Password1!"
}
```

**Option 2: Account in Request Body**

```
POST https://snackbase.com/api/v1/auth/login
{
  "account": "acme-corp",  // Account slug
  "email": "alice@acme.com",
  "password": "Password1!"
}
```

> **Screenshot Placeholder 19**
>
> **Description**: Code examples showing two login methods: account in URL subdomain vs account in request body.

### Account Switching

Users can switch between accounts they belong to:

```bash
# Get user's accounts
GET /api/v1/auth/accounts
Authorization: Bearer <token>

# Response
{
  "accounts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "account_code": "AB1001",
      "name": "Acme Corp",
      "slug": "acme-corp",
      "role": "admin"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "account_code": "XY2048",
      "name": "Globex Inc",
      "slug": "globex",
      "role": "viewer"
    }
  ]
}
```

To switch accounts, user logs in with credentials for the target account.

> **Screenshot Placeholder 20**
>
> **Description**: A UI screenshot showing an account switcher dropdown displaying multiple accounts the user belongs to.

---

## Security Features

### Password Hashing (Argon2id)

SnackBase uses **Argon2id**, the OWASP-recommended password hashing algorithm:

```python
import argon2

# Password hasher configuration
hasher = argon2.PasswordHasher(
    time_cost=3,       # Number of iterations
    memory_cost=65536, # Memory in KiB (64 MB)
    parallelism=4,     # Number of threads
    hash_len=32,       # Hash length
    salt_len=16        # Salt length
)

# Hash password
password_hash = hasher.hash("SecurePass123!")
# $argon2id$v=19$m=65536,t=3,p=4$...

# Verify password (timing-safe)
is_valid = hasher.verify(password_hash, "SecurePass123!")
```

> **Screenshot Placeholder 21**
>
> **Description**: A code example showing Argon2id password hashing with configuration parameters and the resulting hash format.

### Password Requirements

Default password requirements (configurable via `default_password_validator`):

| Requirement       | Minimum      |
| ----------------- | ------------ |
| Length            | 8 characters |
| Uppercase         | 1 character  |
| Lowercase         | 1 character  |
| Number            | 1 digit      |
| Special character | 1 character  |

> **Screenshot Placeholder 22**
>
> **Description**: A visual password requirements checklist showing all requirements with checkmarks as user types.

### Token Expiration

| Token Type    | Default Lifetime | Configurable Via                        |
| ------------- | ---------------- | --------------------------------------- |
| Access Token  | 1 hour           | `SNACKBASE_ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token | 7 days           | `SNACKBASE_REFRESH_TOKEN_EXPIRE_DAYS`   |

> **Screenshot Placeholder 23**
>
> **Description**: A table showing token expiration times with their configuration environment variables.

### Token Security

**Refresh Token Storage in Database:**

- Tokens are **hashed** with SHA-256 before storage
- Tokens include **revocation status** tracking
- **True rotation**: Old tokens revoked when new ones issued
- **JWT ID (jti)** claim links token to database record

**Access Token Security:**

- Stateless JWT (not stored in database)
- Short lifetime (1 hour) limits misuse window
- Contains account context for authorization
- Signed with HS256 or RS256 (configurable)

### Email Verification Security

**Token Hashing:**
```python
# Verification tokens are hashed, not stored in plaintext
token = secrets.token_urlsafe(32)  # 256-bit random token
token_hash = hashlib.sha256(token.encode()).hexdigest()

# Store hash in database
email_verification.token_hash = token_hash

# Constant-time comparison when verifying
provided_hash = hashlib.sha256(provided_token.encode()).hexdigest()
if secrets.compare_digest(provided_hash, stored_hash):
    # Token is valid
```

**Expiration:**
- Tokens expire after **1 hour**
- Expired tokens cannot be used
- Users can request new tokens via resend endpoint

**Single-Use:**
- Tokens are deleted after successful verification
- Prevents token reuse attacks

### CSRF Protection (OAuth/SAML)

**State Tokens:**

- OAuth and SAML use **state tokens** to prevent CSRF
- State is generated server-side and stored in database
- State token is included in authorization request
- Callback must return matching state
- State expires after **10 minutes**
- State is **single-use** (deleted after verification)

**RelayState:**

- Encodes account context and client state
- Base64-encoded to prevent tampering
- Verified on callback to ensure integrity

### Failed Login Attempts

SnackBase tracks failed login attempts and can implement rate limiting:

```python
# Track failed attempts (future feature)
{
  "email": "alice@acme.com",
  "account_id": "550e8400-...",
  "failed_attempts": 3,
  "last_attempt": "2025-01-01T00:00:00Z",
  "locked_until": "2025-01-01T00:05:00Z"  # Locked for 5 minutes
}
```

> **Screenshot Placeholder 24**
>
> **Description**: A code snippet showing the structure of tracking failed login attempts with account lockout information.

---

## Authentication Configuration

Authentication providers are configured using SnackBase's **hierarchical configuration system**, allowing both system-level defaults and account-level overrides.

### Configuration Hierarchy

```
System-Level Configuration
└── account_id: "00000000-0000-0000-0000-000000000000"
    └── Default provider settings for all accounts

Account-Level Configuration
└── account_id: "550e8400-..."
    └── Account-specific overrides (take precedence)
```

**Resolution Order:**
1. Check account-level configuration
2. If not found, use system-level default
3. If not found, use built-in defaults

### Configuration Registry

The `ConfigurationRegistry` manages provider definitions and config resolution:

```python
from snackbase.core.configuration.config_registry import config_registry

# Register a provider definition
config_registry.register_provider_definition(
    provider_type="oauth",
    name="google",
    schema=GoogleOAuthConfig,
    handler=google_oauth_handler
)

# Resolve effective config for an account
config = config_registry.get_effective_config(
    account_id="550e8400-...",
    provider_name="google"
)
```

**Cache:** Effective configs are cached for **5 minutes** to improve performance.

### Password Authentication Configuration

```python
# System-level password configuration
{
  "account_id": "00000000-0000-0000-0000-000000000000",
  "provider_name": "password",
  "provider_type": "auth",
  "enabled": true,
  "config": {
    "min_length": 8,
    "require_uppercase": true,
    "require_lowercase": true,
    "require_digit": true,
    "require_special": true,
    "email_verification_required": true
  }
}
```

### OAuth Provider Configuration

```python
# Account-level Google OAuth configuration
{
  "account_id": "550e8400-...",
  "provider_name": "google",
  "provider_type": "oauth",
  "enabled": true,
  "config": {
    "client_id": "your-google-client-id.apps.googleusercontent.com",
    "client_secret": "your-google-client-secret",
    "redirect_uri": "https://yourapp.com/oauth/google/callback",
    "scopes": ["openid", "email", "profile"],
    "auto_provision": true,
    "allowed_domains": ["acme.com"],
    "default_role": "viewer"
  }
}
```

### SAML Provider Configuration

```python
# Account-level Okta SAML configuration
{
  "account_id": "550e8400-...",
  "provider_name": "okta",
  "provider_type": "saml",
  "enabled": true,
  "config": {
    "idp_entity_id": "https://dev-123456.okta.com",
    "idp_sso_url": "https://dev-123456.okta.com/sso/saml",
    "idp_x509_cert": "-----BEGIN CERTIFICATE-----\n...",
    "sp_entity_id": "https://yourapp.com/saml/metadata",
    "sp_acs_url": "https://yourapp.com/saml/okta/acs",
    "sp_x509_cert": "-----BEGIN CERTIFICATE-----\n...",
    "sp_x509_key": "-----BEGIN PRIVATE KEY-----\n...",
    "attribute_mapping": {
      "email": "NameID",
      "first_name": "firstName",
      "last_name": "lastName"
    },
    "auto_provision": true,
    "default_role": "admin"
  }
}
```

### Email Service Configuration

```python
# System-level email configuration
{
  "account_id": "00000000-0000-0000-0000-000000000000",
  "provider_name": "email",
  "provider_type": "email",
  "enabled": true,
  "config": {
    "smtp_host": "smtp.resend.com",
    "smtp_port": 587,
    "smtp_use_tls": true,
    "smtp_username": "resend",
    "smtp_password": "your-api-key",
    "from_email": "noreply@yourapp.com",
    "from_name": "SnackBase"
  }
}
```

### Configuration API

```bash
# Get effective configuration for an account
GET /api/v1/admin/config
  ?account=acme-corp
  &provider=google

# Update account-level configuration
PUT /api/v1/admin/config
{
  "account": "acme-corp",
  "provider_name": "google",
  "config": {
    "enabled": true,
    "client_id": "new-client-id"
  }
}

# Test configuration
POST /api/v1/admin/config/test
{
  "account": "acme-corp",
  "provider_name": "google"
}
```

---

## Best Practices

### 1. Token Storage

**For Web Applications:**

```javascript
// ✅ Recommended: HttpOnly cookies for refresh tokens
// Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict

// ⚠️ Acceptable: localStorage for access token only
localStorage.setItem("access_token", token);

// ❌ Avoid: localStorage for refresh tokens
localStorage.setItem("refresh_token", token); // Vulnerable to XSS
```

> **Screenshot Placeholder 25**
>
> **Description**: Code comparison showing recommended (HttpOnly cookie) vs acceptable (localStorage for access token) vs avoid (localStorage for refresh token) token storage.

### 2. Token Refresh

Implement proactive token refresh:

```javascript
// Refresh token 5 minutes before expiration
const token = parseJwt(access_token);
const expiresAt = token.exp * 1000;
const now = Date.now();
const refreshBefore = 5 * 60 * 1000; // 5 minutes

if (expiresAt - now < refreshBefore) {
  await refreshToken();
}
```

> **Screenshot Placeholder 26**
>
> **Description**: A code example showing proactive token refresh logic with a timeline visualization.

### 3. Handle Token Expiration

```javascript
// Axios interceptor for automatic token refresh
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Access token expired
      try {
        const newToken = await refreshToken();
        // Retry original request
        return axios.request(error.config);
      } catch {
        // Refresh token expired - redirect to login
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
```

> **Screenshot Placeholder 27**
>
> **Description**: A code example showing an Axios interceptor that handles 401 errors with automatic token refresh and retry.

### 4. Logout Properly

```javascript
async function logout() {
  // Clear tokens from storage
  localStorage.removeItem("access_token");
  document.cookie = "refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";

  // Call backend logout to revoke refresh token
  await axios.post("/api/v1/auth/logout");

  // Redirect to login
  window.location.href = "/login";
}
```

> **Screenshot Placeholder 28**
>
> **Description**: A code example showing proper logout implementation including clearing storage, backend call, and redirect.

### 5. Use HTTPS in Production

Never send tokens over unencrypted connections:

```bash
# ❌ Development only
http://localhost:8000

# ✅ Production
https://yourdomain.com
```

> **Screenshot Placeholder 29**
>
> **Description**: A comparison showing insecure HTTP vs secure HTTPS with lock icons and warnings.

### 6. Email Verification UX

```javascript
// Show email verification status
function showVerificationStatus() {
  if (!user.email_verified) {
    showNotification(
      "Please verify your email. Check your inbox for a verification link.",
      "warning"
    );
    // Provide resend option
    showResendButton();
  }
}

// Resend verification email
async function resendVerification() {
  await axios.post("/api/v1/auth/resend-verification", {
    email: user.email,
    account: currentAccount
  });
  showNotification("Verification email sent!", "success");
}
```

> **Screenshot Placeholder 30**
>
> **Description**: A UI flow showing email verification status display and resend verification functionality.

### 7. Provider Selection

```javascript
// Show available authentication providers
function showLoginOptions() {
  const providers = getEnabledProviders(currentAccount);

  return (
    <div>
      <button onClick={() => loginWithPassword()}>
        Email and Password
      </button>
      <button onClick={() => loginWithOAuth('google')}>
        Continue with Google
      </button>
      <button onClick={() => loginWithSAML('okta')}>
        Single Sign-On (SSO)
      </button>
    </div>
  );
}
```

> **Screenshot Placeholder 31**
>
> **Description**: A UI screenshot showing login page with multiple authentication provider options.

---

## Summary

| Concept                    | Key Takeaway                                                           |
| -------------------------- | ---------------------------------------------------------------------- |
| **User Identity**          | Defined by `(email, account_id)` tuple                                 |
| **Account Registration**   | Creates new tenant with UUID primary key and `XX####` display code     |
| **User Registration**      | Creates user within specific account, email unique per account         |
| **Email Verification**     | Required for login, tokens expire in 1 hour, single-use                |
| **Login Flow**             | Resolve account → Find user → Check verification → Verify password → Issue JWT |
| **Token Management**       | Access token (1 hour) + Refresh token (7 days) with true rotation      |
| **OAuth Authentication**   | Redirect → Authorize → Callback → Exchange tokens → Create/update user |
| **SAML Authentication**    | SSO request → IdP → ACS response → Verify → Create/update user         |
| **Multi-Account Users**    | Same email can exist in multiple accounts with different passwords     |
| **Security**               | Argon2id hashing, timing-safe comparison, token rotation, HTTPS required |
| **Configuration**          | Hierarchical: system-level defaults → account-level overrides          |

---

## Related Documentation

- [Multi-Tenancy Model](./multi-tenancy.md) - How accounts work
- [Security Model](./security.md) - Authorization and permissions
- [Configuration System](./configuration.md) - Provider configuration
- [API Examples](../api-examples.md) - Authentication API usage

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
