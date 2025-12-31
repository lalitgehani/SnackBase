# Authentication Model

SnackBase provides a comprehensive authentication system designed for multi-tenant applications. This guide explains authentication flows, token management, multi-account users, and security considerations.

---

## Table of Contents

- [Overview](#overview)
- [Authentication Architecture](#authentication-architecture)
- [Account Registration](#account-registration)
- [User Registration](#user-registration)
- [Login Flow](#login-flow)
- [Token Management](#token-management)
- [Multi-Account Users](#multi-account-users)
- [Security Features](#security-features)
- [Best Practices](#best-practices)

---

## Overview

SnackBase authentication is built for **enterprise multi-account scenarios**:

| Feature | Description |
|---------|-------------|
| **Account-Scoped Users** | Users belong to specific accounts |
| **Multi-Account Support** | Same email can exist in multiple accounts |
| **Per-Account Passwords** | Different passwords per (email, account) tuple |
| **JWT Tokens** | Access tokens (1 hour) + Refresh tokens (7 days) |
| **Token Rotation** | Refresh token rotation on each use |
| **Timing-Safe Comparison** | Password verification resistant to timing attacks |

> **Screenshot Placeholder 1**
>
> **Description**: A high-level architecture diagram showing the authentication system components: Client, API, JWT Service, Password Hasher, Database.

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
│  - /auth/login                                              │
│  - /auth/refresh                                            │
│  - /auth/me                                                 │
└────────────────────────┬────────────────────────────────────┘
                         │ Validate Credentials
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   JWT Service                               │
│  - Generate access/refresh tokens                           │
│  - Validate tokens                                           │
│  - Extract user/account context                             │
└────────────────────────┬────────────────────────────────────┘
                         │ Hash/Verify
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Password Hasher                             │
│  - Argon2id (OWASP recommended)                             │
│  - Timing-safe comparison                                   │
└────────────────────────┬────────────────────────────────────┘
                         │ Store/Retrieve
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database                                  │
│  - accounts table                                           │
│  - users table (account_id, email, password_hash)           │
└─────────────────────────────────────────────────────────────┘
```

> **Screenshot Placeholder 2**
>
> **Description**: A layered architecture diagram showing the flow from Client → API → JWT Service → Password Hasher → Database.

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
│ Format: XX#### (e.g., AB1001)│
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ Account record created      │
│ - id: AB1001                │
│ - slug: acme-corp           │
│ - name: Acme Corp           │
└─────────────────────────────┘
```

> **Screenshot Placeholder 4**
>
> **Description**: A sequence diagram showing the account registration flow from superadmin action to account creation with auto-generated ID.

### Account ID Generation

Account IDs follow the `XX####` format:

```python
# Example account IDs
SY0000  # System account (reserved)
AB1001  # First account
XY2048  # Second account
ZZ9999  # Another account
```

**Properties:**
- **Format**: 2 letters + 4 digits
- **Immutable**: Once assigned, never changes
- **Globally unique**: No two accounts share the same ID
- **Sequential**: Digits increment with each new account

> **Screenshot Placeholder 5**
>
> **Description**: A visual breakdown of the account ID format showing the letter component (random A-Z) and digit component (sequential starting from 0001).

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
│    "acme-corp" → AB1001         │
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
│ 3. Hash password (Argon2id)     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Create user record           │
│ - id: user_abc123               │
│ - account_id: AB1001            │
│ - email: alice@acme.com         │
│ - password_hash: <argon2 hash>  │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 6**
>
> **Description**: A detailed sequence diagram showing user registration from form submission through account resolution, validation, password hashing, and user creation.

### Email Uniqueness

Email uniqueness is **scoped to account**:

```
✅ ALLOWED:
AB1001: alice@acme.com
XY2048: alice@acme.com  (Same email, different account)

❌ NOT ALLOWED:
AB1001: alice@acme.com
AB1001: alice@acme.com  (Duplicate within account)
```

> **Screenshot Placeholder 7**
>
> **Description**: A database table view showing users with the same email in different accounts (allowed) and the same email within one account (not allowed).

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
│    "acme-corp" → AB1001         │
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
│ 3. Timing-safe password verify  │
│    argon2.verify(password_hash, │
│                provided_password)│
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Generate tokens              │
│    - Access token (1 hour)      │
│    - Refresh token (7 days)     │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 5. Return tokens                │
│ {                               │
│   "access_token": "...",        │
│   "refresh_token": "...",       │
│   "token_type": "bearer",       │
│   "user": { ... }               │
│ }                               │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 8**
>
> **Description**: A comprehensive sequence diagram showing the login flow from credentials input through account resolution, user lookup, password verification, token generation, and response.

### Timing-Safe Password Comparison

SnackBase uses **timing-safe comparison** to prevent timing attacks:

```python
# ❌ VULNERABLE: Regular comparison (timing leak)
if user.password_hash == provided_password:
    # Attacker can measure time to guess password

# ✅ SECURE: Timing-safe comparison
if argon2.verify(user.password_hash, provided_password):
    # Constant time regardless of match
```

> **Screenshot Placeholder 9**
>
> **Description**: A code comparison showing vulnerable (regular comparison) vs secure (timing-safe) password verification with timing visualization.

---

## Token Management

SnackBase uses **JWT (JSON Web Tokens)** with access and refresh tokens.

### Token Types

| Token Type | Lifetime | Purpose | Storage |
|------------|----------|---------|---------|
| **Access Token** | 1 hour | API requests | localStorage/memory |
| **Refresh Token** | 7 days | Get new access token | HttpOnly cookie or localStorage |

> **Screenshot Placeholder 10**
>
> **Description**: A comparison table showing access token vs refresh token with their properties, lifetimes, and recommended storage locations.

### Access Token Structure

```json
{
  "sub": "user_abc123",           // Subject (user ID)
  "account_id": "AB1001",         // Account context
  "email": "alice@acme.com",      // User email
  "role": "admin",                // User role
  "exp": 1704067200,              // Expiration timestamp
  "iat": 1704063600               // Issued at timestamp
}
```

> **Screenshot Placeholder 11**
>
> **Description**: A decoded JWT access token showing its payload/claims with annotations explaining each field.

### Token Usage Pattern

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
│ Receive new access token        │
│ (and new refresh token)         │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 12**
>
> **Description**: A flow diagram showing the token lifecycle from login through usage to expiration and refresh.

### Token Refresh

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

**Token Rotation**: Each refresh returns a new refresh token, invalidating the old one.

> **Screenshot Placeholder 13**
>
> **Description**: A code example showing the refresh token request/response with the new refresh token highlighted.

---

## Multi-Account Users

SnackBase supports **enterprise multi-account scenarios** where users can belong to multiple accounts.

### User Identity Matrix

```
┌────────────────────┬─────────────┬──────────────┬──────────────┐
│ email              │ account_id  │ password     │ role         │
├────────────────────┼─────────────┼──────────────┼──────────────┤
│ alice@acme.com     │ AB1001      │ Password1!   │ admin        │
│ alice@acme.com     │ XY2048      │ Password2!   │ viewer       │
│ bob@acme.com       │ AB1001      │ Password3!   │ editor       │
│ jane@globex.com    │ XY2048      │ Password4!   │ admin        │
└────────────────────┴─────────────┴──────────────┴──────────────┘
```

**Key Points:**
- Same email can exist in multiple accounts
- Each `(email, account_id)` tuple has a unique password
- Users must specify account when logging in

> **Screenshot Placeholder 14**
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

> **Screenshot Placeholder 15**
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
      "id": "AB1001",
      "name": "Acme Corp",
      "slug": "acme-corp",
      "role": "admin"
    },
    {
      "id": "XY2048",
      "name": "Globex Inc",
      "slug": "globex",
      "role": "viewer"
    }
  ]
}
```

To switch accounts, user logs in with credentials for the target account.

> **Screenshot Placeholder 16**
>
> **Description**: A UI screenshot showing an account switcher dropdown displaying multiple accounts the user belongs to.

---

## Security Features

### Password Hashing (Argon2id)

SnackBase uses **Argon2id**, the OWASP-recommended password hashing algorithm:

```python
# Password hashing
import argon2

 hasher = argon2.PasswordHasher(
    time_cost=3,       # Number of iterations
    memory_cost=65536, # Memory in KiB
    parallelism=4,     # Number of threads
    hash_len=32,       # Hash length
    salt_len=16        # Salt length
)

# Hash password
password_hash = hasher.hash("SecurePass123!")
# $argon2id$v=19$m=65536,t=3,p=4$...

# Verify password
is_valid = hasher.verify(password_hash, "SecurePass123!")
```

> **Screenshot Placeholder 17**
>
> **Description**: A code example showing Argon2id password hashing with configuration parameters and the resulting hash format.

### Password Requirements

Default password requirements (configurable):

| Requirement | Minimum |
|-------------|---------|
| Length | 8 characters |
| Uppercase | 1 character |
| Lowercase | 1 character |
| Number | 1 digit |
| Special character | 1 character |

> **Screenshot Placeholder 18**
>
> **Description**: A visual password requirements checklist showing all requirements with checkmarks as user types.

### Token Expiration

| Token Type | Default Lifetime | Configurable Via |
|------------|------------------|------------------|
| Access Token | 1 hour | `SNACKBASE_ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token | 7 days | `SNACKBASE_REFRESH_TOKEN_EXPIRE_DAYS` |

> **Screenshot Placeholder 19**
>
> **Description**: A table showing token expiration times with their configuration environment variables.

### Failed Login Attempts

SnackBase tracks failed login attempts and can implement rate limiting (future feature):

```python
# Track failed attempts
{
  "email": "alice@acme.com",
  "account_id": "AB1001",
  "failed_attempts": 3,
  "last_attempt": "2025-01-01T00:00:00Z",
  "locked_until": "2025-01-01T00:05:00Z"  // Locked for 5 minutes
}
```

> **Screenshot Placeholder 20**
>
> **Description**: A code snippet showing the structure of tracking failed login attempts with account lockout information.

---

## Best Practices

### 1. Token Storage

**For Web Applications:**
```javascript
// ✅ Recommended: HttpOnly cookies
// Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict

// ⚠️ Acceptable: localStorage for access token only
localStorage.setItem('access_token', token);

// ❌ Avoid: localStorage for refresh tokens
localStorage.setItem('refresh_token', token);  // Vulnerable to XSS
```

> **Screenshot Placeholder 21**
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

> **Screenshot Placeholder 22**
>
> **Description**: A code example showing proactive token refresh logic with a timeline visualization.

### 3. Handle Token Expiration

```javascript
// Axios interceptor for automatic token refresh
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Access token expired
      try {
        const newToken = await refreshToken();
        // Retry original request
        return axios.request(error.config);
      } catch {
        // Refresh token expired - redirect to login
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

> **Screenshot Placeholder 23**
>
> **Description**: A code example showing an Axios interceptor that handles 401 errors with automatic token refresh and retry.

### 4. Logout Properly

```javascript
async function logout() {
  // Clear tokens from storage
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');

  // Optional: Call backend logout endpoint
  await axios.post('/api/v1/auth/logout');

  // Redirect to login
  window.location.href = '/login';
}
```

> **Screenshot Placeholder 24**
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

> **Screenshot Placeholder 25**
>
> **Description**: A comparison showing insecure HTTP vs secure HTTPS with lock icons and warnings.

---

## Summary

| Concept | Key Takeaway |
|---------|--------------|
| **User Identity** | Defined by `(email, account_id)` tuple |
| **Account Registration** | Creates new tenant with auto-generated `XX####` ID |
| **User Registration** | Creates user within specific account, email unique per account |
| **Login Flow** | Resolve account → Find user → Verify password → Issue JWT tokens |
| **Token Management** | Access token (1 hour) + Refresh token (7 days) with rotation |
| **Multi-Account Users** | Same email can exist in multiple accounts with different passwords |
| **Security** | Argon2id hashing, timing-safe comparison, HTTPS required in production |

---

## Related Documentation

- [Multi-Tenancy Model](./multi-tenancy.md) - How accounts work
- [Security Model](./security.md) - Authorization and permissions
- [API Examples](../api-examples.md) - Authentication API usage

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
