# SnackBase API Examples

Complete guide to using the SnackBase REST API with practical examples.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Email Verification](#email-verification)
- [Accounts Management](#accounts-management)
- [Collections](#collections)
- [Records (CRUD)](#records-crud)
- [Roles & Permissions](#roles--permissions)
- [Groups](#groups)
- [Users](#users)
- [Invitations](#invitations)
- [Macros](#macros)
- [OAuth Authentication](#oauth-authentication)
- [SAML Authentication](#saml-authentication)
- [Files](#files)
- [Admin Configuration](#admin-configuration)
- [Email Template Management](#email-template-management)
- [Audit Logs](#audit-logs)
- [Migrations](#migrations)
- [Dashboard](#dashboard)
- [Health Checks](#health-checks)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

---

## Getting Started

### Base URL

```
Development: http://localhost:8000
Production:  https://api.yourdomain.com
```

### API Version

All endpoints are prefixed with `/api/v1`:

```
http://localhost:8000/api/v1/auth/register
http://localhost:8000/api/v1/collections
http://localhost:8000/api/v1/records/posts
```

**Important**: Records are accessed via `/api/v1/records/{collection}`, NOT `/api/v1/{collection}`. This is critical for proper route registration.

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Common Headers

```bash
Content-Type: application/json
Authorization: Bearer <access_token>
X-Correlation-ID: <optional-request-id>
```

---

## Authentication

### 1. Register New Account

Create a new account with the first admin user.

**Endpoint**: `POST /api/v1/auth/register`

**Authentication**: None (public endpoint)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "Acme Corporation",
    "account_slug": "acme",
    "email": "admin@acme.com",
    "password": "SecurePass123!"
  }'
```

**Response** (201 Created):

```json
{
  "message": "Registration successful. Please check your email to verify your account.",
  "account": {
    "id": "AB1234",
    "slug": "acme",
    "name": "Acme Corporation",
    "created_at": "2025-12-24T22:00:00Z"
  },
  "user": {
    "id": "usr_abc123",
    "email": "admin@acme.com",
    "role": "admin",
    "is_active": true,
    "email_verified": false,
    "created_at": "2025-12-24T22:00:00Z"
  }
}
```

**Important Changes**:
- Registration NO LONGER returns tokens immediately
- Email verification is REQUIRED before login
- Response includes `email_verified` field
- User must verify email before they can authenticate

**Validation Rules**:

- `account_name`: 1-255 characters
- `account_slug`: 3-32 characters, alphanumeric + hyphens, starts with letter (optional, auto-generated from name)
- `email`: Valid email format
- `password`: Min 12 characters, must include uppercase, lowercase, number, and special character

**Password Strength Requirements**:
- Minimum 12 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one digit (0-9)
- At least one special character: `!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`

**Error Examples**:

```json
// Weak password
{
  "error": "Validation error",
  "details": [
    {
      "field": "password",
      "message": "Password must be at least 12 characters and include uppercase, lowercase, number, and special character"
    }
  ]
}

// Duplicate slug
{
  "error": "Conflict",
  "message": "Account slug 'acme' already exists"
}
```

---

### 2. Login

Authenticate with email, password, and account identifier.

**Endpoint**: `POST /api/v1/auth/login`

**Authentication**: None (public endpoint)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "account": "acme",
    "email": "admin@acme.com",
    "password": "SecurePass123!"
  }'
```

**Response** (200 OK):

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "account": {
    "id": "AB1234",
    "slug": "acme",
    "name": "Acme Corporation"
  },
  "user": {
    "id": "usr_abc123",
    "email": "admin@acme.com",
    "role": "admin"
  }
}
```

**Account Identifier Options**:
- Account slug: `"acme"`
- Account ID: `"AB1234"`

**Error Examples**:

```json
// Email not verified (401)
{
  "error": "Email not verified",
  "message": "Please verify your email before logging in",
  "redirect_url": "/api/v1/auth/send-verification"
}

// Invalid credentials (401)
{
  "error": "Authentication failed",
  "message": "Invalid credentials"
}

// Wrong authentication method (401)
{
  "error": "Wrong authentication method",
  "message": "This account uses OAuth authentication. Please use the OAuth login flow.",
  "auth_provider": "oauth",
  "auth_provider_name": "google",
  "redirect_url": "/api/v1/auth/oauth/google/authorize"
}
```

**Note**: All authentication failures return a generic 401 message (prevents user enumeration), except for email verification and wrong auth method which provide specific guidance.

---

### 3. Refresh Token

Get a new access token using a refresh token.

**Endpoint**: `POST /api/v1/auth/refresh`

**Authentication**: None (uses refresh token)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response** (200 OK):

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

**Notes**:
- Old refresh token is invalidated after successful refresh (token rotation)
- Access tokens expire in 1 hour (configurable)
- Refresh tokens expire in 7 days (configurable)

---

### 4. Get Current User

Get information about the authenticated user.

**Endpoint**: `GET /api/v1/auth/me`

**Authentication**: Required (Bearer token)

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response** (200 OK):

```json
{
  "user_id": "usr_abc123",
  "account_id": "AB1234",
  "email": "admin@acme.com",
  "role": "admin",
  "email_verified": true
}
```

---

## Email Verification

Email verification is required for new user registrations before they can log in.

### 1. Send Verification Email

Send a verification email to the current authenticated user.

**Endpoint**: `POST /api/v1/auth/send-verification`

**Authentication**: Required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/send-verification \
  -H "Authorization: Bearer <token>"
```

**Response** (200 OK):

```json
{
  "message": "Verification email sent successfully",
  "email": "admin@acme.com"
}
```

**Error Responses**:

```json
// Already verified
{
  "error": "Email already verified",
  "message": "Your email has already been verified"
}

// Rate limited
{
  "error": "Too many requests",
  "message": "Please wait before requesting another verification email"
}
```

---

### 2. Resend Verification Email

Resend a verification email (public endpoint for use after registration).

**Endpoint**: `POST /api/v1/auth/resend-verification`

**Authentication**: None (public)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "account": "acme"
  }'
```

**Response** (200 OK):

```json
{
  "message": "Verification email sent successfully",
  "email": "admin@acme.com"
}
```

---

### 3. Verify Email with Token

Verify email address using the token from the verification email.

**Endpoint**: `POST /api/v1/auth/verify-email`

**Authentication**: None (public)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{
    "token": "verify_token_abc123..."
  }'
```

**Response** (200 OK):

```json
{
  "message": "Email verified successfully",
  "user": {
    "id": "usr_abc123",
    "email": "admin@acme.com",
    "email_verified": true
  }
}
```

**Error Responses**:

```json
// Invalid/expired token
{
  "error": "Invalid or expired token",
  "message": "The verification token is invalid or has expired"
}
```

---

## Accounts Management

All account management endpoints require **Superadmin** access (user must belong to system account `SY0000`).

**System Account Details**:
- Account ID: `00000000-0000-0000-0000-000000000000` (UUID format for system-level configs)
- Account Code: `SY0000` (display format)

### 1. List Accounts

**Endpoint**: `GET /api/v1/accounts`

**Authentication**: Superadmin required

**Query Parameters**:

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `page` | int | 1 | >= 1 |
| `page_size` | int | 25 | >= 1, <= 100 |
| `sort_by` | str | "created_at" | id, account_code, slug, name, created_at |
| `sort_order` | str | "desc" | asc, desc |
| `search` | str | null | - |

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/accounts?page=1&page_size=25" \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "AB1234",
      "account_code": "AB1234",
      "slug": "acme",
      "name": "Acme Corporation",
      "created_at": "2025-12-24T22:00:00Z",
      "user_count": 5,
      "status": "active"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 25,
  "total_pages": 1
}
```

---

### 2. Get Account Details

**Endpoint**: `GET /api/v1/accounts/{account_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/accounts/AB1234 \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "id": "AB1234",
  "account_code": "AB1234",
  "slug": "acme",
  "name": "Acme Corporation",
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z",
  "user_count": 5,
  "collections_used": []
}
```

---

### 3. Create Account

**Endpoint**: `POST /api/v1/accounts`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Company LLC",
    "slug": "newcompany"
  }'
```

**Response** (201 Created):

```json
{
  "id": "AB1235",
  "account_code": "NE0001",
  "slug": "newcompany",
  "name": "New Company LLC",
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z",
  "user_count": 0,
  "collections_used": []
}
```

---

### 4. Update Account

**Endpoint**: `PUT /api/v1/accounts/{account_id}`

**Authentication**: Superadmin required

**Note**: Only the account `name` can be updated. Account ID and slug are immutable.

**Request**:

```bash
curl -X PUT http://localhost:8000/api/v1/accounts/AB1234 \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation Updated"
  }'
```

---

### 5. Delete Account

**Endpoint**: `DELETE /api/v1/accounts/{account_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X DELETE http://localhost:8000/api/v1/accounts/AB1234 \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response**: `204 No Content` (empty body)

**Note**: System account (`SY0000`) cannot be deleted.

---

### 6. Get Account Users

**Endpoint**: `GET /api/v1/accounts/{account_id}/users`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/accounts/AB1234/users?page=1&page_size=25" \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "usr_abc123",
      "email": "admin@acme.com",
      "role": "admin",
      "is_active": true,
      "created_at": "2025-12-24T22:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 25,
  "total_pages": 1
}
```

---

## Collections

All collection endpoints require **Superadmin** access.

### 1. List Collections

**Endpoint**: `GET /api/v1/collections/`

**Authentication**: Superadmin required

**Query Parameters**:

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `page` | int | 1 | >= 1 |
| `page_size` | int | 25 | >= 1, <= 100 |
| `sort_by` | str | "created_at" | - |
| `sort_order` | str | "desc" | asc, desc |
| `search` | str | null | - |

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/collections/?page=1&page_size=25" \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "col_xyz789",
      "name": "posts",
      "table_name": "col_posts",
      "fields_count": 5,
      "records_count": 42,
      "created_at": "2025-12-24T22:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 25,
  "total_pages": 1
}
```

---

### 2. Get Collection Names

**Endpoint**: `GET /api/v1/collections/names`

**Authentication**: Superadmin required

**Response** (200 OK):

```json
{
  "names": ["posts", "users", "products"],
  "total": 3
}
```

---

### 3. Get Single Collection

**Endpoint**: `GET /api/v1/collections/{collection_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/collections/col_xyz789 \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "id": "col_xyz789",
  "name": "posts",
  "table_name": "col_posts",
  "fields": [
    {
      "name": "title",
      "type": "text",
      "required": true,
      "default": null,
      "unique": false,
      "options": null,
      "pii": false
    },
    {
      "name": "content",
      "type": "text",
      "required": true,
      "pii": false
    },
    {
      "name": "author_id",
      "type": "reference",
      "collection": "users",
      "on_delete": "cascade",
      "required": false
    }
  ],
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z"
}
```

---

### 4. Create Collection

**Endpoint**: `POST /api/v1/collections/`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/collections/ \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "posts",
    "schema": [
      {
        "name": "title",
        "type": "text",
        "required": true
      },
      {
        "name": "content",
        "type": "text",
        "required": true
      },
      {
        "name": "published",
        "type": "boolean",
        "default": false
      },
      {
        "name": "views",
        "type": "number",
        "default": 0
      },
      {
        "name": "author_id",
        "type": "reference",
        "collection": "users",
        "on_delete": "cascade"
      },
      {
        "name": "status",
        "type": "text",
        "options": ["draft", "published", "archived"]
      },
      {
        "name": "email",
        "type": "email"
      },
      {
        "name": "website",
        "type": "url"
      },
      {
        "name": "metadata",
        "type": "json"
      },
      {
        "name": "social_security",
        "type": "text",
        "pii": true,
        "mask_type": "ssn"
      }
    ]
  }'
```

**Response** (201 Created):

```json
{
  "id": "col_xyz789",
  "name": "posts",
  "table_name": "col_posts",
  "fields": [...],
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z"
}
```

**Field Types**:

| Type | SQL Type | Description |
|------|----------|-------------|
| `text` | TEXT | String values |
| `number` | REAL | Numeric values (int or float, not bool) |
| `boolean` | INTEGER (0/1) | True/false |
| `datetime` | DATETIME | ISO 8601 datetime strings |
| `email` | TEXT | Email addresses (validated) |
| `url` | TEXT | URLs (validated, must start with http:// or https://) |
| `json` | TEXT | JSON objects |
| `reference` | TEXT | Foreign key to another collection |

**Field Options**:

- `required`: Boolean (default: false)
- `default`: Default value
- `unique`: Boolean (default: false)
- `options`: Array of allowed values (enum)
- `pii`: Boolean - Enable PII masking
- `mask_type`: For PII fields - email, ssn, phone, name, full, custom

**Auto-Added Fields**:
Every collection automatically includes:
- `id` (TEXT PRIMARY KEY) - Auto-generated UUID
- `account_id` (TEXT NOT NULL) - For multi-tenancy
- `created_at` (DATETIME) - ISO 8601 timestamp
- `created_by` (TEXT) - User ID who created the record
- `updated_at` (DATETIME) - ISO 8601 timestamp
- `updated_by` (TEXT) - User ID who last updated the record

**Physical Table Naming**:
Tables are prefixed with `col_` (e.g., collection "posts" becomes `col_posts`).

**Validation Rules**:
- Collection name: 3-64 chars, starts with letter, alphanumeric + underscores only
- Field names: Cannot use reserved names (id, account_id, created_at, created_by, updated_at, updated_by)
- Reference fields require `collection` and `on_delete` attributes

---

### 5. Update Collection

**Endpoint**: `PUT /api/v1/collections/{collection_id}`

**Authentication**: Superadmin required

**Constraints**:
- Cannot delete existing fields
- Cannot change field types
- Can only add new fields

**Request**:

```bash
curl -X PUT http://localhost:8000/api/v1/collections/col_xyz789 \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "schema": [
      {
        "name": "title",
        "type": "text",
        "required": true
      },
      {
        "name": "content",
        "type": "text",
        "required": true
      },
      {
        "name": "published",
        "type": "boolean",
        "default": false
      },
      {
        "name": "views",
        "type": "number",
        "default": 0
      },
      {
        "name": "category",
        "type": "text"
      }
    ]
  }'
```

---

### 6. Delete Collection

**Endpoint**: `DELETE /api/v1/collections/{collection_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X DELETE http://localhost:8000/api/v1/collections/col_xyz789 \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response**: `200 OK` with record count confirmation

---

## Records (CRUD)

**IMPORTANT**: All record operations use `/api/v1/records/{collection}`, NOT `/api/v1/{collection}`.

**Route Registration Order**: The `records_router` MUST be registered LAST in the FastAPI app to avoid capturing specific routes like `/invitations`, `/collections`, etc.

### 1. Create Record

**Endpoint**: `POST /api/v1/records/{collection}`

**Authentication**: Required

**Example - Create Post**:

```bash
curl -X POST http://localhost:8000/api/v1/records/posts \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Getting Started with SnackBase",
    "content": "SnackBase is an open-source Backend-as-a-Service...",
    "published": true,
    "author_id": "usr_abc123"
  }'
```

**Response** (201 Created):

```json
{
  "id": "rec_abc123",
  "title": "Getting Started with SnackBase",
  "content": "SnackBase is an open-source Backend-as-a-Service...",
  "published": true,
  "views": 0,
  "account_id": "AB1234",
  "created_at": "2025-12-24T22:00:00Z",
  "created_by": "usr_abc123",
  "updated_at": "2025-12-24T22:00:00Z",
  "updated_by": "usr_abc123"
}
```

**Superadmin Special Access**: Superadmin can create records for any account by passing `account_id` in the request body:

```bash
curl -X POST http://localhost:8000/api/v1/records/posts \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Post for another account",
    "content": "Content...",
    "account_id": "AB1235"
  }'
```

**Notes**:
- `account_id`, `created_at`, `created_by`, `updated_at`, `updated_by` are auto-set by built-in hooks
- Required fields must be provided
- Default values are applied for missing optional fields
- Reference values are validated for existence
- PII fields are automatically masked for users without `pii_access` group

---

### 2. List Records

**Endpoint**: `GET /api/v1/records/{collection}`

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `skip` | int | 0 | >= 0 |
| `limit` | int | 30 | >= 1, <= 100 |
| `sort` | str | "-created_at" | +/- prefix for asc/desc |
| `fields` | str | null | Comma-separated field list |
| `{field}` | any | - | Filter by field value |

**Example - List Posts**:

```bash
curl -X GET "http://localhost:8000/api/v1/records/posts?skip=0&limit=10&sort=-created_at" \
  -H "Authorization: Bearer <token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "rec_abc123",
      "title": "Getting Started with SnackBase",
      "content": "...",
      "published": true,
      "views": 42,
      "created_at": "2025-12-24T22:00:00Z"
    },
    {
      "id": "rec_def456",
      "title": "Advanced Features",
      "content": "...",
      "published": false,
      "views": 0,
      "created_at": "2025-12-24T21:00:00Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 10
}
```

**Example - Field Limiting**:

```bash
curl -X GET "http://localhost:8000/api/v1/records/posts?fields=id,title,created_at" \
  -H "Authorization: Bearer <token>"
```

**Response**:

```json
{
  "items": [
    {
      "id": "rec_abc123",
      "title": "Getting Started with SnackBase",
      "created_at": "2025-12-24T22:00:00Z"
    }
  ],
  "total": 1
}
```

**Example - Filtering**:

```bash
# Filter by field value (exact match only)
curl -X GET "http://localhost:8000/api/v1/records/posts?published=true" \
  -H "Authorization: Bearer <token>"

# Multiple filters (combined with AND)
curl -X GET "http://localhost:8000/api/v1/records/posts?published=true&status=draft" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Get Single Record

**Endpoint**: `GET /api/v1/records/{collection}/{id}`

**Authentication**: Required

**Example**:

```bash
curl -X GET http://localhost:8000/api/v1/records/posts/rec_abc123 \
  -H "Authorization: Bearer <token>"
```

**Response** (200 OK):

```json
{
  "id": "rec_abc123",
  "title": "Getting Started with SnackBase",
  "content": "SnackBase is an open-source Backend-as-a-Service...",
  "published": true,
  "views": 42,
  "account_id": "AB1234",
  "created_at": "2025-12-24T22:00:00Z",
  "created_by": "usr_abc123",
  "updated_at": "2025-12-24T22:00:00Z",
  "updated_by": "usr_abc123"
}
```

**Error** (404 Not Found):

```json
{
  "error": "Not found",
  "message": "Record not found"
}
```

---

### 4. Update Record (Full)

**Endpoint**: `PUT /api/v1/records/{collection}/{id}`

**Authentication**: Required

**Example**:

```bash
curl -X PUT http://localhost:8000/api/v1/records/posts/rec_abc123 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Getting Started with SnackBase (Updated)",
    "content": "Updated content...",
    "published": true,
    "views": 100
  }'
```

**Response** (200 OK):

```json
{
  "id": "rec_abc123",
  "title": "Getting Started with SnackBase (Updated)",
  "content": "Updated content...",
  "published": true,
  "views": 100,
  "updated_at": "2025-12-24T22:30:00Z",
  "updated_by": "usr_abc123"
}
```

**Note**: PUT replaces the entire record. All non-system fields must be provided.

---

### 5. Update Record (Partial)

**Endpoint**: `PATCH /api/v1/records/{collection}/{id}`

**Authentication**: Required

**Example**:

```bash
curl -X PATCH http://localhost:8000/api/v1/records/posts/rec_abc123 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "views": 150
  }'
```

**Response** (200 OK):

```json
{
  "id": "rec_abc123",
  "title": "Getting Started with SnackBase (Updated)",
  "content": "Updated content...",
  "published": true,
  "views": 150,
  "updated_at": "2025-12-24T22:35:00Z",
  "updated_by": "usr_abc123"
}
```

**Note**: PATCH updates only the provided fields.

---

### 6. Delete Record

**Endpoint**: `DELETE /api/v1/records/{collection}/{id}`

**Authentication**: Required

**Example**:

```bash
curl -X DELETE http://localhost:8000/api/v1/records/posts/rec_abc123 \
  -H "Authorization: Bearer <token>"
```

**Response** (204 No Content): Empty body

**Error - Foreign Key Restriction** (409 Conflict):

```json
{
  "error": "Conflict",
  "message": "Cannot delete record: it is referenced by other records"
}
```

---

## Roles & Permissions

### Roles Endpoints

All roles endpoints require **Superadmin** access.

#### 1. List Roles

**Endpoint**: `GET /api/v1/roles`

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/roles \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": 1,
      "name": "admin",
      "description": "Administrator with full access",
      "collections_count": 10
    },
    {
      "id": 2,
      "name": "user",
      "description": "Regular user with limited access",
      "collections_count": 5
    }
  ],
  "total": 2
}
```

---

#### 2. Create Role

**Endpoint**: `POST /api/v1/roles`

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/roles \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "editor",
    "description": "Can edit but not delete content"
  }'
```

**Response** (201 Created):

```json
{
  "id": 3,
  "name": "editor",
  "description": "Can edit but not delete content"
}
```

---

#### 3. Get Single Role

**Endpoint**: `GET /api/v1/roles/{role_id}`

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/roles/3 \
  -H "Authorization: Bearer <superadmin_token>"
```

---

#### 4. Update Role

**Endpoint**: `PUT /api/v1/roles/{role_id}`

**Request**:

```bash
curl -X PUT http://localhost:8000/api/v1/roles/3 \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "senior_editor",
    "description": "Senior editor with additional privileges"
  }'
```

---

#### 5. Delete Role

**Endpoint**: `DELETE /api/v1/roles/{role_id}`

**Note**: Default roles ("admin", "user") cannot be deleted.

---

#### 6. Get Role Permissions

**Endpoint**: `GET /api/v1/roles/{role_id}/permissions`

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/roles/3/permissions \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "role_id": 3,
  "role_name": "editor",
  "permissions": [
    {
      "collection": "posts",
      "permission_id": 10,
      "create": {"rule": "true", "fields": ["title", "content"]},
      "read": {"rule": "true", "fields": "*"},
      "update": {"rule": "@owns_record()", "fields": ["title", "content"]},
      "delete": null
    }
  ]
}
```

---

#### 7. Get Permissions Matrix

**Endpoint**: `GET /api/v1/roles/{role_id}/permissions/matrix`

**Purpose**: Returns permissions for ALL collections (including those without permissions set).

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/roles/3/permissions/matrix \
  -H "Authorization: Bearer <superadmin_token>"
```

---

#### 8. Bulk Update Permissions

**Endpoint**: `PUT /api/v1/roles/{role_id}/permissions/bulk`

**Request**:

```bash
curl -X PUT http://localhost:8000/api/v1/roles/3/permissions/bulk \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      {
        "collection": "posts",
        "operation": "create",
        "rule": "user.role == \"editor\"",
        "fields": ["title", "content"]
      },
      {
        "collection": "posts",
        "operation": "read",
        "rule": "true",
        "fields": "*"
      },
      {
        "collection": "posts",
        "operation": "update",
        "rule": "@owns_record() or @has_role(\"admin\")",
        "fields": ["title", "content", "status"]
      },
      {
        "collection": "posts",
        "operation": "delete",
        "rule": "@has_role(\"admin\")",
        "fields": "*"
      }
    ]
  }'
```

**Response** (200 OK):

```json
{
  "success_count": 4,
  "failure_count": 0,
  "errors": []
}
```

---

#### 9. Validate Rule

**Endpoint**: `POST /api/v1/roles/validate-rule`

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/roles/validate-rule \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rule": "@has_role(\"admin\") or @owns_record()"
  }'
```

**Response** (200 OK):

```json
{
  "valid": true,
  "error": null,
  "position": null
}
```

---

#### 10. Test Rule

**Endpoint**: `POST /api/v1/roles/test-rule`

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/roles/test-rule \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rule": "@has_role(\"admin\") or user.id == record.created_by",
    "context": {
      "user": {"id": "usr_123", "role": "editor"},
      "record": {"created_by": "usr_123"}
    }
  }'
```

**Response** (200 OK):

```json
{
  "allowed": true,
  "error": null,
  "evaluation_details": null
}
```

---

### Permission Rule Syntax

SnackBase uses a custom DSL for permission rules:

**Supported Syntax Examples**:

```python
# Always allow
"true"

# User-based checks
"user.id == record.owner_id"
"user.id == \"user_abc123\""

# Role checks
"@has_role(\"admin\")"

# Group membership
"@in_group(\"managers\")"

# Record ownership
"@owns_record()"

# Field comparisons
"status in [\"draft\", \"published\"]"
"priority > 5"

# Complex expressions
"@has_role(\"admin\") or @owns_record()"
"user.id == record.created_by and status != \"archived\""

# Macro execution
"@has_permission(\"read\", \"posts\")"
"@in_time_range(9, 17)"
```

**Permission Structure**:

```json
{
  "create": {
    "rule": "user.role == \"admin\"",
    "fields": ["title", "content"]
  },
  "read": {
    "rule": "true",
    "fields": "*"
  },
  "update": {
    "rule": "@owns_record()",
    "fields": ["title", "status"]
  },
  "delete": {
    "rule": "@has_role(\"admin\")",
    "fields": "*"
  }
}
```

**Operations**: `create`, `read`, `update`, `delete`
**Fields**: `"*"` for all fields, or list of specific field names

---

### Permissions Endpoints

All permissions endpoints require **Superadmin** access.

#### 1. Create Permission

**Endpoint**: `POST /api/v1/permissions`

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/permissions \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role_id": 3,
    "collection": "posts",
    "rules": {
      "create": {"rule": "true", "fields": ["title", "content"]},
      "read": {"rule": "true", "fields": "*"},
      "update": {"rule": "@owns_record()", "fields": ["title", "content"]},
      "delete": {"rule": "false", "fields": []}
    }
  }'
```

---

#### 2. List Permissions

**Endpoint**: `GET /api/v1/permissions`

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/permissions \
  -H "Authorization: Bearer <superadmin_token>"
```

---

#### 3. Get Single Permission

**Endpoint**: `GET /api/v1/permissions/{permission_id}`

---

#### 4. Delete Permission

**Endpoint**: `DELETE /api/v1/permissions/{permission_id}`

---

## Groups

Groups are account-isolated (not superadmin).

### 1. Create Group

**Endpoint**: `POST /api/v1/groups`

**Authentication**: Required (account-isolated)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/groups \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "managers",
    "description": "Manager group with elevated permissions"
  }'
```

**Response** (201 Created):

```json
{
  "id": "grp_abc123",
  "account_id": "AB1234",
  "account_code": "AB1234",
  "name": "managers",
  "description": "Manager group with elevated permissions",
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z"
}
```

---

### 2. List Groups

**Endpoint**: `GET /api/v1/groups`

**Query Parameters**:
- `skip`: Default 0
- `limit`: Default 100

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/groups?skip=0&limit=100" \
  -H "Authorization: Bearer <token>"
```

**Response** (200 OK):

```json
[
  {
    "id": "grp_abc123",
    "account_id": "AB1234",
    "account_code": "AB1234",
    "name": "managers",
    "description": "Manager group with elevated permissions",
    "created_at": "2025-12-24T22:00:00Z",
    "updated_at": "2025-12-24T22:00:00Z"
  }
]
```

---

### 3. Get Single Group

**Endpoint**: `GET /api/v1/groups/{group_id}`

---

### 4. Update Group

**Endpoint**: `PATCH /api/v1/groups/{group_id}`

**Request**:

```bash
curl -X PATCH http://localhost:8000/api/v1/groups/grp_abc123 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description"
  }'
```

---

### 5. Delete Group

**Endpoint**: `DELETE /api/v1/groups/{group_id}`

---

### 6. Add User to Group

**Endpoint**: `POST /api/v1/groups/{group_id}/users`

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/groups/grp_abc123/users \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_def456"
  }'
```

**Response** (201 Created):

```json
{
  "message": "User added to group"
}
```

---

### 7. Remove User from Group

**Endpoint**: `DELETE /api/v1/groups/{group_id}/users/{user_id}`

**Request**:

```bash
curl -X DELETE http://localhost:8000/api/v1/groups/grp_abc123/users/usr_def456 \
  -H "Authorization: Bearer <token>"
```

**Response**: `204 No Content`

---

## Users

All users endpoints require **Superadmin** access.

### 1. Create User

**Endpoint**: `POST /api/v1/users`

**Authentication**: Superadmin required

**Request** (Password Authentication):

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "account_id": "AB1234",
    "role_id": "2"
  }'
```

**Request** (OAuth/SAML Authentication - password auto-generated):

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "account_id": "AB1234",
    "role_id": "2",
    "auth_provider": "oauth",
    "auth_provider_name": "google"
  }'
```

**Response** (201 Created):

```json
{
  "id": "usr_xyz789",
  "email": "user@example.com",
  "role": {
    "id": 2,
    "name": "user"
  },
  "is_active": true,
  "email_verified": false,
  "auth_provider": "password",
  "auth_provider_name": null,
  "account_id": "AB1234",
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z"
}
```

**Authentication Provider Fields**:
- `auth_provider`: "password", "oauth", or "saml"
- `auth_provider_name`: Provider name (e.g., "google", "github", "azure_ad", "okta")
- For non-password auth, password is auto-generated and user cannot login with password

---

### 2. List Users

**Endpoint**: `GET /api/v1/users`

**Authentication**: Superadmin required

**Query Parameters**:

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `skip` | int | 0 | >= 0 |
| `limit` | int | 25 | >= 1, <= 100 |
| `account_id` | str | null | Filter by account |
| `role_id` | int | null | Filter by role |
| `is_active` | bool | null | Filter by active status |
| `search` | str | null | Search in email |
| `sort` | str | "created_at" | Field name (prefix with `-` for desc) |

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/users?skip=0&limit=25" \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "usr_abc123",
      "email": "admin@acme.com",
      "role": {
        "id": 1,
        "name": "admin"
      },
      "is_active": true,
      "email_verified": true,
      "auth_provider": "password",
      "auth_provider_name": null,
      "account_id": "AB1234",
      "account_code": "AB1234",
      "account_name": "Acme Corporation",
      "created_at": "2025-12-24T22:00:00Z",
      "updated_at": "2025-12-24T22:00:00Z",
      "last_login": null
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 25
}
```

---

### 3. Get Single User

**Endpoint**: `GET /api/v1/users/{user_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/users/usr_abc123 \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "id": "usr_abc123",
  "email": "admin@acme.com",
  "role": {
    "id": 1,
    "name": "admin",
    "description": "Administrator with full access"
  },
  "is_active": true,
  "email_verified": true,
  "auth_provider": "password",
  "auth_provider_name": null,
  "account_id": "AB1234",
  "account_code": "AB1234",
  "account_name": "Acme Corporation",
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z",
  "last_login": "2025-12-24T23:00:00Z",
  "groups": []
}
```

---

### 4. Update User

**Endpoint**: `PATCH /api/v1/users/{user_id}`

**Authentication**: Superadmin required

**Note**: Users cannot modify their own role or deactivate themselves.

**Request**:

```bash
curl -X PATCH http://localhost:8000/api/v1/users/usr_abc123 \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role_id": 2
  }'
```

**Response** (200 OK):

```json
{
  "id": "usr_abc123",
  "email": "admin@acme.com",
  "role": {
    "id": 2,
    "name": "user"
  },
  "is_active": true,
  "updated_at": "2025-12-24T22:30:00Z"
}
```

---

### 5. Reset User Password

**Endpoint**: `PUT /api/v1/users/{user_id}/password`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X PUT http://localhost:8000/api/v1/users/usr_abc123/password \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "NewSecurePass456!"
  }'
```

**Response** (200 OK):

```json
{
  "message": "Password reset successfully"
}
```

---

### 6. Deactivate User

**Endpoint**: `DELETE /api/v1/users/{user_id}`

**Authentication**: Superadmin required

**Note**: This is a soft delete. The user is marked as inactive but not removed from the database.

**Request**:

```bash
curl -X DELETE http://localhost:8000/api/v1/users/usr_abc123 \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response**: `204 No Content`

---

## Invitations

### 1. Create Invitation

Invite a user to your account.

**Endpoint**: `POST /api/v1/invitations`

**Authentication**: Required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/invitations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "role_id": "2"
  }'
```

**Response** (201 Created):

```json
{
  "id": "inv_xyz789",
  "account_id": "AB1234",
  "email": "newuser@example.com",
  "invited_by": "usr_abc123",
  "expires_at": "2025-12-26T22:00:00Z",
  "accepted_at": null,
  "created_at": "2025-12-24T22:00:00Z",
  "status": "pending"
}
```

**Note**: Token is not returned for security. It's sent via email (future feature). Invitations expire after 48 hours. The `role_id` field is currently reserved for future use - all invited users are assigned the "user" role by default.

---

### 2. List Invitations

**Endpoint**: `GET /api/v1/invitations`

**Query Parameters**:
- `status_filter`: "pending" | "accepted" | "expired" | "cancelled" (note: cancelled invitations are deleted from database, so this filter returns no results)

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/invitations?status_filter=pending" \
  -H "Authorization: Bearer <token>"
```

**Response** (200 OK):

```json
{
  "invitations": [
    {
      "id": "inv_xyz789",
      "account_id": "AB1234",
      "email": "newuser@example.com",
      "invited_by": "usr_abc123",
      "expires_at": "2025-12-26T22:00:00Z",
      "accepted_at": null,
      "created_at": "2025-12-24T22:00:00Z",
      "status": "pending"
    }
  ],
  "total": 1
}
```

---

### 3. Accept Invitation

**Endpoint**: `POST /api/v1/invitations/{token}/accept`

**Authentication**: None (public)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/invitations/inv_token_abc123/accept \
  -H "Content-Type: application/json" \
  -d '{
    "password": "SecurePass123!"
  }'
```

**Response** (200 OK):

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "account": {
    "id": "AB1234",
    "slug": "acme",
    "name": "Acme Corporation",
    "created_at": "2025-12-24T22:00:00Z"
  },
  "user": {
    "id": "usr_new123",
    "email": "newuser@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2025-12-24T22:00:00Z"
  }
}
```

---

### 4. Cancel Invitation

**Endpoint**: `DELETE /api/v1/invitations/{invitation_id}`

**Request**:

```bash
curl -X DELETE http://localhost:8000/api/v1/invitations/inv_xyz789 \
  -H "Authorization: Bearer <token>"
```

**Response**: `204 No Content`

---

## Macros

### 1. Create Macro

**Endpoint**: `POST /api/v1/macros/`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/macros/ \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "user_post_count",
    "sql_query": "SELECT COUNT(*) FROM col_posts WHERE created_by = :user_id",
    "parameters": ["user_id"],
    "description": "Count posts created by a user"
  }'
```

**Response** (201 Created):

```json
{
  "id": 1,
  "name": "user_post_count",
  "description": "Count posts created by a user",
  "sql_query": "SELECT COUNT(*) FROM col_posts WHERE created_by = :user_id",
  "parameters": ["user_id"],
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z",
  "created_by": "usr_abc123"
}
```

**SQL Validation Rules**:
- Must start with `SELECT`
- Forbidden keywords: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, GRANT, REVOKE
- Name must be valid Python identifier

---

### 2. List Macros

**Endpoint**: `GET /api/v1/macros/`

**Authentication**: Required (all authenticated users)

**Query Parameters**:
- `skip`: Default 0
- `limit`: Default 100

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/macros/?skip=0&limit=100" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Get Single Macro

**Endpoint**: `GET /api/v1/macros/{macro_id}`

**Authentication**: Required (all authenticated users)

---

### 4. Update Macro

**Endpoint**: `PUT /api/v1/macros/{macro_id}`

**Authentication**: Superadmin required

---

### 5. Test Macro

**Endpoint**: `POST /api/v1/macros/{macro_id}/test`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/macros/1/test \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": ["usr_abc123"]
  }'
```

**Response** (200 OK):

```json
{
  "result": "42",
  "execution_time": 12.5,
  "rows_affected": 0
}
```

**Note**: Executes in a transaction that is rolled back. 5-second timeout enforced.

---

### 6. Delete Macro

**Endpoint**: `DELETE /api/v1/macros/{macro_id}`

**Authentication**: Superadmin required

**Note**: Fails if macro is used in any active permission rules.

---

### Built-in Macros

These macros are executed directly by the macro engine:

| Macro | Description |
|-------|-------------|
| `@has_group(group_name)` | Check if user has a group |
| `@has_role(role_name)` | Check if user has a role |
| `@owns_record()` / `@is_creator()` | Check if user owns the record |
| `@in_time_range(start_hour, end_hour)` | Check if current time is in range |
| `@has_permission(action, collection)` | Check specific permission |

---

## OAuth Authentication

SnackBase supports OAuth 2.0 authentication for popular providers.

### Supported Providers

- `google` - Google OAuth 2.0
- `github` - GitHub OAuth App
- `microsoft` - Microsoft Azure AD
- `apple` - Sign in with Apple

### 1. Initiate OAuth Flow

**Endpoint**: `POST /api/v1/auth/oauth/{provider_name}/authorize`

**Authentication**: None (public)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/oauth/google/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "account": "acme",
    "redirect_uri": "http://localhost:3000/auth/callback",
    "state": "random_state_string"
  }'
```

**Response** (200 OK):

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...",
  "state": "random_state_string",
  "provider": "google"
}
```

**Query Parameters**:
- `account` (required): Account slug or ID
- `redirect_uri` (required): URL to redirect after authentication
- `state` (optional): CSRF protection token

---

### 2. OAuth Callback

**Endpoint**: `POST /api/v1/auth/oauth/{provider_name}/callback`

**Authentication**: None (public)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/oauth/google/callback \
  -H "Content-Type: application/json" \
  -d '{
    "code": "4/0AX4XfWh...",
    "state": "random_state_string",
    "redirect_uri": "http://localhost:3000/auth/callback"
  }'
```

**Response** (200 OK):

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "account": {
    "id": "AB1234",
    "slug": "acme",
    "name": "Acme Corporation",
    "created_at": "2025-12-24T22:00:00Z"
  },
  "user": {
    "id": "usr_oauth123",
    "email": "user@gmail.com",
    "role": "user",
    "is_active": true,
    "created_at": "2025-12-24T22:00:00Z"
  },
  "is_new_user": false,
  "is_new_account": false
}
```

**Note**: If `is_new_user` is true, a new user account is created. If `is_new_account` is true, both account and user are created.

---

## SAML Authentication

SnackBase supports SAML 2.0 for enterprise single sign-on (SSO).

### Supported Providers

- `azure` - Microsoft Azure AD
- `okta` - Okta Identity Cloud
- `generic` - Any SAML 2.0 compliant IdP

### 1. Initiate SAML SSO

**Endpoint**: `GET /api/v1/auth/saml/sso`

**Authentication**: None (public)

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/auth/saml/sso?account=acme&provider=azure" \
  -L
```

**Response**: Redirects to the Identity Provider's login page

**Query Parameters**:
- `account` (required): Account slug or ID
- `provider` (optional): SAML provider name (default: first configured)
- `relay_state` (optional): State to return after authentication

---

### 2. SAML Assertion Consumer Service (ACS)

**Endpoint**: `POST /api/v1/auth/saml/acs`

**Authentication**: None (public)

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/saml/acs \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "SAMLResponse=PHNhbWxwOlJlc3BvbnNlIHdpZGhOg...&RelayState=optional_state"
```

**Response** (200 OK):

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "account": {
    "id": "AB1234",
    "slug": "acme",
    "name": "Acme Corporation",
    "created_at": "2025-12-24T22:00:00Z"
  },
  "user": {
    "id": "usr_saml123",
    "email": "user@company.com",
    "role": "user",
    "is_active": true,
    "created_at": "2025-12-24T22:00:00Z"
  }
}
```

---

### 3. Download SAML Metadata

**Endpoint**: `GET /api/v1/auth/saml/metadata`

**Authentication**: None (public)

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/auth/saml/metadata?account=acme&provider=azure" \
  -o saml-metadata.xml
```

**Response**: XML metadata file for importing into your Identity Provider

**Query Parameters**:
- `account` (required): Account slug or ID
- `provider` (optional): SAML provider name (default: first configured)

---

## Files

File upload and download endpoints.

### 1. Upload File

**Endpoint**: `POST /api/v1/files/upload`

**Authentication**: Required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/document.pdf"
```

**Response** (200 OK):

```json
{
  "success": true,
  "file": {
    "filename": "document.pdf",
    "path": "uploads/AB1234/document_20250124_abc123.pdf",
    "size": 102400,
    "content_type": "application/pdf",
    "uploaded_at": "2025-12-24T22:00:00Z"
  },
  "message": "File uploaded successfully"
}
```

---

### 2. Download File

**Endpoint**: `GET /api/v1/files/{file_path:path}`

**Authentication**: Required

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/files/uploads/AB1234/document_20250124_abc123.pdf \
  -H "Authorization: Bearer <token>" \
  -o downloaded_document.pdf
```

**Response**: File content (appropriate Content-Type header)

---

## Admin Configuration

Admin API for managing system and account provider configurations.

### Configuration Management

All provider configurations (auth, email, storage) are managed through these endpoints.

#### 1. Get Configuration Statistics

**Endpoint**: `GET /api/v1/admin/configuration/stats`

**Authentication**: Superadmin required

**Response** (200 OK):

```json
{
  "system_configs": {
    "auth": 5,
    "oauth": 4,
    "email": 2,
    "total": 11
  },
  "account_configs": {
    "auth": 3,
    "oauth": 2,
    "total": 5
  }
}
```

---

#### 2. List System Configurations

**Endpoint**: `GET /api/v1/admin/configuration/system`

**Authentication**: Superadmin required

**Query Parameters**:
- `category`: Filter by category (auth, oauth, saml, email)

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/configuration/system?category=oauth" \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
[
  {
    "id": "config_abc123",
    "category": "oauth",
    "provider_name": "google",
    "display_name": "Google OAuth",
    "logo_url": null,
    "enabled": true,
    "priority": 1,
    "is_builtin": false,
    "created_at": "2025-12-24T22:00:00Z",
    "updated_at": "2025-12-24T22:00:00Z"
  }
]
```

---

#### 3. List Account Configurations

**Endpoint**: `GET /api/v1/admin/configuration/account`

**Authentication**: Superadmin required

**Query Parameters**:
- `account_id` (required): Account ID
- `category`: Filter by category

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/configuration/account?account_id=AB1234" \
  -H "Authorization: Bearer <superadmin_token>"
```

---

#### 4. Create Configuration

**Endpoint**: `POST /api/v1/admin/configuration`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/admin/configuration \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "oauth",
    "provider_name": "google",
    "display_name": "Google OAuth",
    "config": {
      "client_id": "your-client-id.apps.googleusercontent.com",
      "client_secret": "your-client-secret",
      "scope": "openid email profile"
    },
    "logo_url": "https://example.com/logo.png",
    "enabled": true,
    "priority": 1
  }'
```

**Response** (201 Created):

```json
{
  "id": "config_xyz789",
  "message": "Configuration created successfully"
}
```

---

#### 5. Update Configuration Values

**Endpoint**: `PATCH /api/v1/admin/configuration/{config_id}/values`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X PATCH http://localhost:8000/api/v1/admin/configuration/config_xyz789/values \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "new-client-id.apps.googleusercontent.com",
    "client_secret": "new-client-secret"
  }'
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "Configuration updated successfully"
}
```

---

#### 6. Get Configuration Values

**Endpoint**: `GET /api/v1/admin/configuration/{config_id}/values`

**Authentication**: Superadmin required

**Response** (200 OK):

```json
{
  "client_id": "your-client-id.apps.googleusercontent.com",
  "client_secret": "********",  // Masked for security
  "scope": "openid email profile"
}
```

**Note**: Sensitive values (secrets) are masked in the response.

---

#### 7. Enable/Disable Configuration

**Endpoint**: `PATCH /api/v1/admin/configuration/{config_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X PATCH http://localhost:8000/api/v1/admin/configuration/config_xyz789 \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

---

#### 8. Delete Configuration

**Endpoint**: `DELETE /api/v1/admin/configuration/{config_id}`

**Authentication**: Superadmin required

**Note**: Built-in configurations cannot be deleted, only disabled.

---

#### 9. List Provider Definitions

**Endpoint**: `GET /api/v1/admin/configuration/providers`

**Authentication**: Superadmin required

**Query Parameters**:
- `category`: Filter by category

**Response** (200 OK):

```json
[
  {
    "category": "oauth",
    "name": "google",
    "display_name": "Google OAuth 2.0",
    "description": "Authenticate users with Google",
    "logo_url": null
  }
]
```

---

#### 10. Get Provider Schema

**Endpoint**: `GET /api/v1/admin/configuration/schema/{category}/{provider_name}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/admin/configuration/schema/oauth/google \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "type": "object",
  "properties": {
    "client_id": {
      "type": "string",
      "title": "Client ID",
      "description": "OAuth client ID from Google Cloud Console"
    },
    "client_secret": {
      "type": "string",
      "title": "Client Secret",
      "format": "password",
      "secret": true
    },
    "scope": {
      "type": "string",
      "title": "OAuth Scope",
      "default": "openid email profile"
    }
  },
  "required": ["client_id", "client_secret"]
}
```

---

#### 11. Test Provider Connection

**Endpoint**: `POST /api/v1/admin/configuration/test-connection`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/admin/configuration/test-connection \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "oauth",
    "provider_name": "google",
    "config": {
      "client_id": "test-client-id",
      "client_secret": "test-client-secret"
    }
  }'
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "Connection test successful"
}
```

---

#### 12. Get Recent Configurations

**Endpoint**: `GET /api/v1/admin/configuration/recent`

**Authentication**: Superadmin required

**Query Parameters**:
- `limit`: Number of results (default: 10)

---

## Email Template Management

Admin API for managing email templates and viewing email logs.

### 1. List Email Templates

**Endpoint**: `GET /api/v1/admin/email/templates`

**Authentication**: Superadmin required

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | str | null | Filter by template type |
| `enabled` | bool | null | Filter by enabled status |
| `search` | str | null | Search in name/description |

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/email/templates" \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "email_verify_abc123",
      "type": "email_verification",
      "name": "Email Verification",
      "description": "Sent to users to verify their email address",
      "subject": "Verify Your Email Address",
      "enabled": true,
      "created_at": "2025-12-24T22:00:00Z",
      "updated_at": "2025-12-24T22:00:00Z"
    },
    {
      "id": "password_reset_def456",
      "type": "password_reset",
      "name": "Password Reset",
      "description": "Sent when user requests password reset",
      "subject": "Reset Your Password",
      "enabled": true,
      "created_at": "2025-12-24T22:00:00Z",
      "updated_at": "2025-12-24T22:00:00Z"
    }
  ],
  "total": 2
}
```

---

### 2. Get Single Email Template

**Endpoint**: `GET /api/v1/admin/email/templates/{template_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/admin/email/templates/email_verify_abc123 \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "id": "email_verify_abc123",
  "type": "email_verification",
  "name": "Email Verification",
  "description": "Sent to users to verify their email address",
  "subject": "Verify Your Email Address",
  "html_content": "<html><body><h1>Verify Your Email</h1>...</body></html>",
  "text_content": "Verify Your Email\n\nClick the link below...",
  "enabled": true,
  "variables": ["verification_link", "user_email", "account_name"],
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z"
}
```

---

### 3. Update Email Template

**Endpoint**: `PUT /api/v1/admin/email/templates/{template_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X PUT http://localhost:8000/api/v1/admin/email/templates/email_verify_abc123 \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Please Verify Your Email Address",
    "html_content": "<html><body><h1>Email Verification Required</h1>...</body></html>",
    "text_content": "Email Verification Required\n\nPlease click...",
    "enabled": true
  }'
```

**Response** (200 OK):

```json
{
  "id": "email_verify_abc123",
  "message": "Template updated successfully"
}
```

**Available Template Variables**:
- `email_verification`: `{{verification_link}}`, `{{user_email}}`, `{{account_name}}`
- `password_reset`: `{{reset_link}}`, `{{user_email}}`, `{{account_name}}`
- `invitation`: `{{invitation_link}}`, `{{inviter_email}}`, `{{account_name}}`

---

### 4. Render Template (Preview)

**Endpoint**: `POST /api/v1/admin/email/templates/render`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/admin/email/templates/render \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "email_verification",
    "variables": {
      "verification_link": "https://example.com/verify?token=abc123",
      "user_email": "user@example.com",
      "account_name": "Acme Corp"
    }
  }'
```

**Response** (200 OK):

```json
{
  "subject": "Verify Your Email Address",
  "html_content": "<html><body>...</html>",
  "text_content": "Verify Your Email\n\nClick: https://example.com/verify?token=abc123"
}
```

**Note**: This endpoint renders the template without sending an email.

---

### 5. Send Test Email

**Endpoint**: `POST /api/v1/admin/email/templates/{template_id}/test`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/admin/email/templates/email_verify_abc123/test \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_email": "test@example.com",
    "variables": {
      "verification_link": "https://example.com/verify?token=test123",
      "user_email": "test@example.com",
      "account_name": "Test Account"
    }
  }'
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "Test email sent successfully to test@example.com"
}
```

---

### 6. List Email Logs

**Endpoint**: `GET /api/v1/admin/email/logs`

**Authentication**: Superadmin required

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Results per page (max 100) |
| `template_type` | str | null | Filter by template type |
| `status` | str | null | Filter by status (sent, failed, pending) |
| `recipient_email` | str | null | Filter by recipient |
| `from_date` | datetime | null | ISO 8601 start date |
| `to_date` | datetime | null | ISO 8601 end date |

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/email/logs?skip=0&limit=50" \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "log_abc123",
      "template_id": "email_verify_abc123",
      "template_type": "email_verification",
      "recipient_email": "user@example.com",
      "account_id": "AB1234",
      "status": "sent",
      "error_message": null,
      "sent_at": "2025-12-24T22:00:00Z",
      "created_at": "2025-12-24T22:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

---

### 7. Get Single Email Log

**Endpoint**: `GET /api/v1/admin/email/logs/{log_id}`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/admin/email/logs/log_abc123 \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "id": "log_abc123",
  "template_id": "email_verify_abc123",
  "template_type": "email_verification",
  "template_name": "Email Verification",
  "recipient_email": "user@example.com",
  "subject": "Verify Your Email Address",
  "account_id": "AB1234",
  "account_name": "Acme Corporation",
  "status": "sent",
  "error_message": null,
  "sent_at": "2025-12-24T22:00:00Z",
  "created_at": "2025-12-24T22:00:00Z"
}
```

**Status Values**:
- `pending`: Queued for sending
- `sent`: Successfully sent
- `failed`: Failed to send (check `error_message`)

---

## Audit Logs

Audit logging for GxP compliance. Logs are immutable and PII is masked based on group membership.

### 1. List Audit Logs

**Endpoint**: `GET /api/v1/audit-logs`

**Authentication**: Superadmin required

**Query Parameters**:

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `skip` | int | 0 | >= 0 |
| `limit` | int | 50 | >= 1, <= 100 |
| `account_id` | str | null | Filter by account |
| `table_name` | str | null | Filter by table/collection |
| `record_id` | str | null | Filter by record ID |
| `user_id` | str | null | Filter by user |
| `operation` | str | null | Filter by operation |
| `from_date` | datetime | null | ISO 8601 format |
| `to_date` | datetime | null | ISO 8601 format |
| `sort_by` | str | "timestamp" | Field name |
| `sort_order` | str | "desc" | asc, desc |

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/audit-logs?skip=0&limit=50&sort_order=desc" \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": 1,
      "account_id": "AB1234",
      "table_name": "col_posts",
      "record_id": "rec_abc123",
      "operation": "UPDATE",
      "user_id": "usr_abc123",
      "user_email": "admin@acme.com",
      "old_values": {"title": "Old Title"},
      "new_values": {"title": "New Title"},
      "changed_fields": ["title"],
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2025-12-24T22:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

**Note**: PII fields are masked for users without `pii_access` group.

---

### 2. Get Single Audit Log

**Endpoint**: `GET /api/v1/audit-logs/{log_id}`

**Authentication**: Superadmin required

---

### 3. Export Audit Logs

**Endpoint**: `GET /api/v1/audit-logs/export`

**Authentication**: Superadmin required

**Query Parameters**:
- `format`: `csv` or `json` (default: `csv`)
- Same filters as list endpoint

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/audit-logs/export?format=csv&from_date=2025-12-01T00:00:00Z" \
  -H "Authorization: Bearer <superadmin_token>" \
  -o audit_logs_export.csv
```

**Response**: File download (CSV or JSON)

---

## Migrations

Database migration management using Alembic.

### 1. List Migrations

**Endpoint**: `GET /api/v1/migrations`

**Authentication**: Superadmin required

**Response** (200 OK):

```json
{
  "items": [
    {
      "revision": "abc123def456",
      "down_revision": null,
      "branch_labels": null,
      "depends_on": null,
      "message": "Initial migration",
      "is_head": true,
      "is_baseline": true,
      "is_branch_point": false,
      "migration_type": "upgrade"
    }
  ],
  "total": 1
}
```

---

### 2. Get Current Revision

**Endpoint**: `GET /api/v1/migrations/current`

**Authentication**: Superadmin required

**Response** (200 OK):

```json
{
  "current_revision": "abc123def456",
  "current_version": "1.0.0",
  "is_head": true
}
```

---

### 3. Get Migration History

**Endpoint**: `GET /api/v1/migrations/history`

**Authentication**: Superadmin required

**Response** (200 OK):

```json
{
  "history": [
    {
      "revision": "abc123def456",
      "message": "Initial migration",
      "applied_at": "2025-12-24T22:00:00Z",
      "duration_seconds": 0.5
    }
  ]
}
```

---

## Dashboard

### Get Dashboard Statistics

**Endpoint**: `GET /api/v1/dashboard/stats`

**Authentication**: Superadmin required

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/dashboard/stats \
  -H "Authorization: Bearer <superadmin_token>"
```

**Response** (200 OK):

```json
{
  "total_accounts": 10,
  "total_users": 45,
  "total_collections": 12,
  "total_records": 1523,
  "new_accounts_7d": 2,
  "new_users_7d": 8,
  "recent_registrations": [
    {
      "id": "usr_new123",
      "email": "user@example.com",
      "account_id": "AB1234",
      "account_code": "AB1234",
      "account_name": "Acme Corporation",
      "created_at": "2025-12-24T22:00:00Z"
    }
  ],
  "system_health": {
    "database_status": "connected",
    "storage_usage_mb": 45.2
  },
  "active_sessions": 15,
  "recent_audit_logs": []
}
```

---

## Health Checks

Health check endpoints have no authentication requirement.

### 1. Basic Health Check

**Endpoint**: `GET /health`

**Response** (200 OK):

```json
{
  "status": "healthy",
  "service": "SnackBase",
  "version": "0.1.0"
}
```

---

### 2. Readiness Check

**Endpoint**: `GET /ready`

**Response** (200 OK):

```json
{
  "status": "ready",
  "service": "SnackBase",
  "version": "0.1.0",
  "database": "connected"
}
```

**Error Response** (503 Service Unavailable):

```json
{
  "status": "not_ready",
  "service": "SnackBase",
  "version": "0.1.0",
  "database": "disconnected"
}
```

---

### 3. Liveness Check

**Endpoint**: `GET /live`

**Response** (200 OK):

```json
{
  "status": "alive",
  "service": "SnackBase",
  "version": "0.1.0"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning               | Example                    |
| ---- | --------------------- | -------------------------- |
| 200  | OK                    | Successful GET, PUT, PATCH |
| 201  | Created               | Successful POST            |
| 204  | No Content            | Successful DELETE          |
| 400  | Bad Request           | Validation error           |
| 401  | Unauthorized          | Missing or invalid token   |
| 403  | Forbidden             | Insufficient permissions   |
| 404  | Not Found             | Resource doesn't exist     |
| 409  | Conflict              | Duplicate resource         |
| 422  | Unprocessable Entity  | Invalid data format        |
| 500  | Internal Server Error | Server error               |

### Error Response Format

```json
{
  "error": "Error type",
  "message": "Error message describing what went wrong"
}
```

### Validation Error Response

```json
{
  "error": "Validation error",
  "details": [
    {
      "field": "password",
      "message": "Password must be at least 12 characters...",
      "code": "password_too_weak"
    }
  ]
}
```

### Field Access Denied Response

```json
{
  "error": "Field access denied",
  "message": "Permission denied to update fields: salary, ssn",
  "unauthorized_fields": ["salary", "ssn"],
  "allowed_fields": ["name", "email"],
  "field_type": "restricted"
}
```

---

## Best Practices

### 1. Always Use HTTPS in Production

```bash
# Bad (production)
http://api.yourdomain.com/api/v1/records/posts

# Good (production)
https://api.yourdomain.com/api/v1/records/posts
```

---

### 2. Store Tokens Securely

```javascript
// Bad - localStorage is vulnerable to XSS
localStorage.setItem("token", token);

// Good - httpOnly cookie (server-side)
// Or use secure session storage with proper CSP
```

---

### 3. Handle Token Expiration

```javascript
// Refresh token before expiration
async function makeRequest(url) {
  let token = getAccessToken();

  // Check if token is about to expire
  if (isTokenExpiringSoon(token)) {
    token = await refreshAccessToken();
  }

  return fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
```

---

### 4. Use Pagination for Large Datasets

```bash
# Bad - fetching too many records
curl -X GET http://localhost:8000/api/v1/records/posts?limit=1000

# Good - paginate results
curl -X GET "http://localhost:8000/api/v1/records/posts?skip=0&limit=30"
curl -X GET "http://localhost:8000/api/v1/records/posts?skip=30&limit=30"
```

---

### 5. Use Field Limiting

```bash
# Bad - fetching all fields when you only need a few
curl -X GET http://localhost:8000/api/v1/records/posts

# Good - limit to needed fields
curl -X GET "http://localhost:8000/api/v1/records/posts?fields=id,title,created_at"
```

---

### 6. Add Correlation IDs

```bash
# Add X-Correlation-ID for request tracing
curl -X POST http://localhost:8000/api/v1/records/posts \
  -H "Authorization: Bearer <token>" \
  -H "X-Correlation-ID: req_abc123" \
  -d '{...}'
```

---

### 7. Handle Errors Gracefully

```javascript
async function createPost(data) {
  try {
    const response = await fetch("/api/v1/records/posts", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || error.detail);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to create post:", error.message);
    // Show user-friendly error message
  }
}
```

---

### 8. Use Appropriate HTTP Methods

- `GET`: Retrieve data (idempotent, cacheable)
- `POST`: Create new resource
- `PUT`: Replace entire resource (idempotent)
- `PATCH`: Update partial resource
- `DELETE`: Remove resource (idempotent)

---

### 9. Remember Route Registration Order

**CRITICAL**: The `records_router` (for `/api/v1/records/{collection}`) MUST be registered LAST in your FastAPI app. This prevents it from capturing specific routes like `/invitations`, `/collections`, `/accounts`, etc.

```python
# Correct order in app.py
app.include_router(invitations_router, prefix="/api/v1/invitations", tags=["invitations"])
app.include_router(collections_router, prefix="/api/v1/collections", tags=["collections"])
app.include_router(accounts_router, prefix="/api/v1/accounts", tags=["accounts"])
# ... all other specific routers ...
app.include_router(records_router, prefix="/api/v1/records", tags=["records"])  # MUST BE LAST
```

---

### 10. Verify Emails Before Login

Always implement email verification in your registration flow:

1. User registers → NO TOKENS returned, just message
2. User receives verification email
3. User clicks verification link or enters token
4. Email verified → User can now login
5. Login checks `email_verified` field, returns 401 if not verified

---

## Rate Limiting (Future)

Rate limiting will be added in a future phase. Recommended limits:

- **Authenticated requests**: 1000 requests/hour
- **Unauthenticated requests**: 100 requests/hour
- **Burst limit**: 20 requests/second

---

## SDK Examples (Future)

Official SDKs will be provided in future releases:

- **JavaScript/TypeScript**: `@snackbase/client`
- **Python**: `snackbase-client`
- **Go**: `github.com/snackbase/client-go`

---

## Support

- **API Documentation**: http://localhost:8000/docs
- **GitHub Issues**: [repository]/issues
- **Community**: [community-link]
