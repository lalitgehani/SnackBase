# SnackBase API Examples

Complete guide to using the SnackBase REST API with practical examples.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Accounts Management](#accounts-management)
- [Collections](#collections)
- [Records (CRUD)](#records-crud)
- [Roles & Permissions](#roles--permissions)
- [Groups](#groups)
- [Invitations](#invitations)
- [Macros](#macros)
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
http://localhost:8000/api/v1/posts
```

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
    "id": "usr_abc123",
    "email": "admin@acme.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-12-24T22:00:00Z"
  }
}
```

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
// Invalid credentials (401)
{
  "error": "Authentication failed",
  "message": "Invalid credentials"
}
```

**Note**: All authentication failures return a generic 401 message (prevents user enumeration).

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
  "role": "admin"
}
```

---

## Accounts Management

All account management endpoints require **Superadmin** access (user must belong to system account `SY0000`).

### 1. List Accounts

**Endpoint**: `GET /api/v1/accounts`

**Authentication**: Superadmin required

**Query Parameters**:

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `page` | int | 1 | >= 1 |
| `page_size` | int | 25 | >= 1, <= 100 |
| `sort_by` | str | "created_at" | id, slug, name, created_at |
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

All record operations are performed on dynamic collection endpoints: `/api/v1/{collection}`

### 1. Create Record

**Endpoint**: `POST /api/v1/{collection}`

**Authentication**: Required

**Example - Create Post**:

```bash
curl -X POST http://localhost:8000/api/v1/posts \
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

**Notes**:
- `account_id`, `created_at`, `created_by`, `updated_at`, `updated_by` are auto-set by built-in hooks
- Required fields must be provided
- Default values are applied for missing optional fields
- Reference values are validated for existence
- PII fields are automatically masked for users without `pii_access` group

---

### 2. List Records

**Endpoint**: `GET /api/v1/{collection}`

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
curl -X GET "http://localhost:8000/api/v1/posts?skip=0&limit=10&sort=-created_at" \
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
curl -X GET "http://localhost:8000/api/v1/posts?fields=id,title,created_at" \
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
# Filter by field value
curl -X GET "http://localhost:8000/api/v1/posts?published=true" \
  -H "Authorization: Bearer <token>"

# Multiple filters
curl -X GET "http://localhost:8000/api/v1/posts?published=true&views_gt=10" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Get Single Record

**Endpoint**: `GET /api/v1/{collection}/{id}`

**Authentication**: Required

**Example**:

```bash
curl -X GET http://localhost:8000/api/v1/posts/rec_abc123 \
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

**Endpoint**: `PUT /api/v1/{collection}/{id}`

**Authentication**: Required

**Example**:

```bash
curl -X PUT http://localhost:8000/api/v1/posts/rec_abc123 \
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

**Endpoint**: `PATCH /api/v1/{collection}/{id}`

**Authentication**: Required

**Example**:

```bash
curl -X PATCH http://localhost:8000/api/v1/posts/rec_abc123 \
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

**Endpoint**: `DELETE /api/v1/{collection}/{id}`

**Authentication**: Required

**Example**:

```bash
curl -X DELETE http://localhost:8000/api/v1/posts/rec_abc123 \
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

**Note**: Token is not returned for security. It's sent via email (future feature). Invitations expire after 48 hours.

---

### 2. List Invitations

**Endpoint**: `GET /api/v1/invitations`

**Query Parameters**:
- `status_filter`: "pending" | "accepted" | "expired" | "cancelled"

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
http://api.yourdomain.com/api/v1/posts

# Good (production)
https://api.yourdomain.com/api/v1/posts
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
curl -X GET http://localhost:8000/api/v1/posts?limit=1000

# Good - paginate results
curl -X GET "http://localhost:8000/api/v1/posts?skip=0&limit=30"
curl -X GET "http://localhost:8000/api/v1/posts?skip=30&limit=30"
```

---

### 5. Use Field Limiting

```bash
# Bad - fetching all fields when you only need a few
curl -X GET http://localhost:8000/api/v1/posts

# Good - limit to needed fields
curl -X GET "http://localhost:8000/api/v1/posts?fields=id,title,created_at"
```

---

### 6. Add Correlation IDs

```bash
# Add X-Correlation-ID for request tracing
curl -X POST http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer <token>" \
  -H "X-Correlation-ID: req_abc123" \
  -d '{...}'
```

---

### 7. Handle Errors Gracefully

```javascript
async function createPost(data) {
  try {
    const response = await fetch("/api/v1/posts", {
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
