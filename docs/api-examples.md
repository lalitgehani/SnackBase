# SnackBase API Examples

Complete guide to using the SnackBase REST API with practical examples.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Collections](#collections)
- [Records (CRUD)](#records-crud)
- [Invitations](#invitations)
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
  "token_type": "bearer",
  "account": {
    "id": "AC1234",
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

- `account_name`: 3-64 characters
- `account_slug`: 3-32 characters, alphanumeric + hyphens, starts with letter (optional, auto-generated from name)
- `email`: Valid email format
- `password`: Min 12 characters, must include uppercase, lowercase, number, and special character

**Error Examples**:

```bash
# Weak password
{
  "detail": "Password must be at least 12 characters and include uppercase, lowercase, number, and special character"
}

# Duplicate slug
{
  "detail": "Account slug 'acme' already exists"
}

# Invalid email
{
  "detail": "Invalid email format"
}
```

---

### 2. Login

Authenticate with email, password, and account identifier.

**Endpoint**: `POST /api/v1/auth/login`

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "account_identifier": "acme",
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
  "token_type": "bearer",
  "account": {
    "id": "AC1234",
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
- Account ID: `"AC1234"`

**Error Examples**:

```bash
# Invalid credentials (401)
{
  "detail": "Invalid credentials"
}

# Inactive user (401)
{
  "detail": "User account is inactive"
}
```

---

### 3. Refresh Token

Get a new access token using a refresh token.

**Endpoint**: `POST /api/v1/auth/refresh`

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
  "expires_in": 3600,
  "token_type": "bearer"
}
```

**Notes**:

- Old refresh token is invalidated after successful refresh
- Access tokens expire in 1 hour (configurable)
- Refresh tokens expire in 7 days (configurable)

---

### 4. Get Current User

Get information about the authenticated user.

**Endpoint**: `GET /api/v1/auth/me`

**Request**:

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response** (200 OK):

```json
{
  "id": "usr_abc123",
  "email": "admin@acme.com",
  "role": "admin",
  "account_id": "AC1234",
  "is_active": true,
  "created_at": "2025-12-24T22:00:00Z",
  "last_login": "2025-12-24T22:30:00Z"
}
```

---

## Collections

### 1. Create Collection

Create a new dynamic collection with a custom schema.

**Endpoint**: `POST /api/v1/collections`

**Authentication**: Requires superadmin role

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/collections \
  -H "Authorization: Bearer <token>" \
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
      }
    ]
  }'
```

**Response** (201 Created):

```json
{
  "id": "col_xyz789",
  "name": "posts",
  "schema": [...],
  "created_at": "2025-12-24T22:00:00Z",
  "updated_at": "2025-12-24T22:00:00Z"
}
```

**Field Types**:

- `text`: String values
- `number`: Numeric values (int or float)
- `boolean`: True/false
- `datetime`: ISO 8601 datetime strings
- `email`: Email addresses (validated)
- `url`: URLs (validated)
- `json`: JSON objects
- `reference`: Foreign key to another collection

**Field Options**:

- `required`: Boolean (default: false)
- `default`: Default value
- `unique`: Boolean (default: false)
- `options`: Array of allowed values (enum)

**Auto-Added Fields**:
Every collection automatically includes:

- `id` (TEXT PRIMARY KEY)
- `account_id` (TEXT, for multi-tenancy)
- `created_at` (DATETIME)
- `created_by` (TEXT, user ID)
- `updated_at` (DATETIME)
- `updated_by` (TEXT, user ID)

**Example with All Field Types**:

```json
{
  "name": "products",
  "schema": [
    {
      "name": "name",
      "type": "text",
      "required": true
    },
    {
      "name": "description",
      "type": "text"
    },
    {
      "name": "price",
      "type": "number",
      "required": true
    },
    {
      "name": "in_stock",
      "type": "boolean",
      "default": true
    },
    {
      "name": "release_date",
      "type": "datetime"
    },
    {
      "name": "contact_email",
      "type": "email"
    },
    {
      "name": "product_url",
      "type": "url"
    },
    {
      "name": "metadata",
      "type": "json"
    },
    {
      "name": "category_id",
      "type": "reference",
      "collection": "categories",
      "on_delete": "set_null"
    },
    {
      "name": "status",
      "type": "text",
      "options": ["draft", "published", "archived"]
    }
  ]
}
```

---

## Records (CRUD)

All record operations are performed on dynamic collection endpoints: `/api/v1/{collection}`

### 1. Create Record

**Endpoint**: `POST /api/v1/{collection}`

**Example - Create Post**:

```bash
curl -X POST http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Getting Started with SnackBase",
    "content": "SnackBase is an open-source Backend-as-a-Service...",
    "published": true
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
  "account_id": "AC1234",
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

---

### 2. List Records

**Endpoint**: `GET /api/v1/{collection}`

**Query Parameters**:

- `skip`: Offset for pagination (default: 0)
- `limit`: Number of records to return (default: 30, max: 100)
- `sort`: Sort field with +/- prefix (e.g., `+created_at`, `-views`)
- `fields`: Comma-separated list of fields to return

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

---

### 3. Get Single Record

**Endpoint**: `GET /api/v1/{collection}/{id}`

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
  "account_id": "AC1234",
  "created_at": "2025-12-24T22:00:00Z",
  "created_by": "usr_abc123",
  "updated_at": "2025-12-24T22:00:00Z",
  "updated_by": "usr_abc123"
}
```

**Error** (404 Not Found):

```json
{
  "detail": "Record not found"
}
```

**Note**: Returns 404 for both non-existent records and records from other accounts (security).

---

### 4. Update Record (Full)

**Endpoint**: `PUT /api/v1/{collection}/{id}`

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
  "account_id": "AC1234",
  "created_at": "2025-12-24T22:00:00Z",
  "created_by": "usr_abc123",
  "updated_at": "2025-12-24T22:30:00Z",
  "updated_by": "usr_abc123"
}
```

**Note**: PUT replaces the entire record. All required fields must be provided.

---

### 5. Update Record (Partial)

**Endpoint**: `PATCH /api/v1/{collection}/{id}`

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

**Note**: PATCH updates only the provided fields. Other fields remain unchanged.

---

### 6. Delete Record

**Endpoint**: `DELETE /api/v1/{collection}/{id}`

**Example**:

```bash
curl -X DELETE http://localhost:8000/api/v1/posts/rec_abc123 \
  -H "Authorization: Bearer <token>"
```

**Response** (204 No Content):

```
(Empty body)
```

**Error - Foreign Key Restriction** (409 Conflict):

```json
{
  "detail": "Cannot delete record: foreign key constraint violation"
}
```

---

## Invitations

### 1. Create Invitation

Invite a user to your account.

**Endpoint**: `POST /api/v1/invitations`

**Request**:

```bash
curl -X POST http://localhost:8000/api/v1/invitations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "role_id": "role_user"
  }'
```

**Response** (201 Created):

```json
{
  "id": "inv_xyz789",
  "email": "newuser@example.com",
  "account_id": "AC1234",
  "invited_by": "usr_abc123",
  "expires_at": "2025-12-26T22:00:00Z",
  "status": "pending",
  "created_at": "2025-12-24T22:00:00Z"
}
```

**Note**: Token is not returned for security. It's sent via email (future feature).

---

### 2. List Invitations

**Endpoint**: `GET /api/v1/invitations`

**Query Parameters**:

- `status`: Filter by status (pending, accepted, expired, cancelled)

**Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/invitations?status=pending" \
  -H "Authorization: Bearer <token>"
```

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "inv_xyz789",
      "email": "newuser@example.com",
      "status": "pending",
      "expires_at": "2025-12-26T22:00:00Z",
      "created_at": "2025-12-24T22:00:00Z"
    }
  ],
  "total": 1
}
```

---

### 3. Accept Invitation

**Endpoint**: `POST /api/v1/invitations/{token}/accept`

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
  "user": {
    "id": "usr_new123",
    "email": "newuser@example.com",
    "role": "user"
  }
}
```

---

### 4. Cancel Invitation

**Endpoint**: `DELETE /api/v1/invitations/{id}`

**Request**:

```bash
curl -X DELETE http://localhost:8000/api/v1/invitations/inv_xyz789 \
  -H "Authorization: Bearer <token>"
```

**Response** (204 No Content):

```
(Empty body)
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
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**401 Unauthorized**:

```bash
# Missing token
curl -X GET http://localhost:8000/api/v1/posts
# Response: {"detail": "Not authenticated"}

# Invalid token
curl -X GET http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer invalid_token"
# Response: {"detail": "Could not validate credentials"}
```

**400 Bad Request**:

```bash
# Missing required field
curl -X POST http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Missing title"}'
# Response: {"detail": "Field 'title' is required"}
```

**403 Forbidden**:

```bash
# Non-superadmin trying to create collection
curl -X POST http://localhost:8000/api/v1/collections \
  -H "Authorization: Bearer <user_token>" \
  -d '{...}'
# Response: {"detail": "Superadmin access required"}
```

**409 Conflict**:

```bash
# Duplicate account slug
curl -X POST http://localhost:8000/api/v1/auth/register \
  -d '{"account_slug": "acme", ...}'
# Response: {"detail": "Account slug 'acme' already exists"}
```

---

## Best Practices

### 1. Always Use HTTPS in Production

```bash
# ❌ Bad (production)
http://api.yourdomain.com/api/v1/posts

# ✅ Good (production)
https://api.yourdomain.com/api/v1/posts
```

### 2. Store Tokens Securely

```javascript
// ❌ Bad - localStorage is vulnerable to XSS
localStorage.setItem("token", token);

// ✅ Good - httpOnly cookie (server-side)
// Or use secure session storage with proper CSP
```

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

### 4. Use Pagination for Large Datasets

```bash
# ❌ Bad - fetching all records
curl -X GET http://localhost:8000/api/v1/posts?limit=1000

# ✅ Good - paginate results
curl -X GET "http://localhost:8000/api/v1/posts?skip=0&limit=30"
curl -X GET "http://localhost:8000/api/v1/posts?skip=30&limit=30"
```

### 5. Use Field Limiting

```bash
# ❌ Bad - fetching all fields when you only need a few
curl -X GET http://localhost:8000/api/v1/posts

# ✅ Good - limit to needed fields
curl -X GET "http://localhost:8000/api/v1/posts?fields=id,title,created_at"
```

### 6. Add Correlation IDs

```bash
# Add X-Correlation-ID for request tracing
curl -X POST http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer <token>" \
  -H "X-Correlation-ID: req_abc123" \
  -d '{...}'
```

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
      throw new Error(error.detail);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to create post:", error.message);
    // Show user-friendly error message
  }
}
```

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

Headers (future):

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640390400
```

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
