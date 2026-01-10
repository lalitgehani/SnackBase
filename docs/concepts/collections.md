# Collections Model

SnackBase's **Collections** are the core abstraction for defining data schemas and generating APIs. This guide explains how collections work, the dynamic table system, and implications for developers.

---

## Table of Contents

- [Overview](#overview)
- [What is a Collection?](#what-is-a-collection)
- [Collection vs Table](#collection-vs-table)
- [Field Types](#field-types)
- [Dynamic Table Generation](#dynamic-table-generation)
- [Auto-Generated APIs](#auto-generated-apis)
- [PII Masking](#pii-masking)
- [Reference Fields](#reference-fields)
- [Schema Evolution](#schema-evolution)
- [Best Practices](#best-practices)

---

## Overview

In traditional databases, you define tables with schemas. In SnackBase, you define **Collections**, which:

1. Store schema metadata in the `collections` table
2. Create/update physical tables dynamically
3. Auto-generate REST API endpoints
4. Provide validation and type safety
5. Support relationships between collections
6. Protect sensitive data with PII masking

> **Screenshot Placeholder 1**
>
> **Description**: A high-level diagram showing the flow: Define Collection → Schema Stored → Table Created → API Generated → Ready to Use.

---

## What is a Collection?

A **Collection** is a named data schema with fields, types, and configuration options.

### Collection Structure

```json
{
  "id": "col_abc123",
  "name": "posts",
  "description": "Blog posts and articles",
  "account_id": "AB1001",
  "migration_revision": "20250101_create_posts",
  "schema": {
    "fields": [
      { "name": "title", "type": "text", "required": true },
      { "name": "content", "type": "text", "required": false },
      { "name": "status", "type": "text", "default": "draft" },
      { "name": "views", "type": "number", "default": 0 },
      { "name": "published_at", "type": "datetime" },
      { "name": "author_email", "type": "email" },
      { "name": "cover_image", "type": "url" },
      { "name": "metadata", "type": "json" }
    ]
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

> **Screenshot Placeholder 2**
>
> **Description**: A JSON representation of a collection showing its structure with id, name, description, migration revision, schema fields, and metadata.

### Components of a Collection

| Component | Purpose | Example |
|-----------|---------|---------|
| **name** | Unique identifier, becomes table name | `posts` → `col_posts` table |
| **description** | Human-readable description | "Blog posts and articles" |
| **schema** | Field definitions with types and validation | See field types below |
| **account_id** | Owner account (for collection management) | `AB1001` |
| **migration_revision** | Tracks which migration created/modified the collection | `20250101_create_posts` |

> **Screenshot Placeholder 3**
>
> **Description**: The Collection Builder UI showing a collection being created with name, description, and fields in a form interface.

---

## Collection vs Table

Understanding the distinction is critical:

### The Confusion

```
❌ Common Misconception:
"Creating a collection creates a separate table for each account"

✓ Reality:
"Creating a collection creates ONE shared table for ALL accounts"
```

> **Screenshot Placeholder 4**
>
> **Description**: A comparison diagram showing the misconception (separate tables per account) vs reality (one shared table with account_id).

### How It Actually Works

When you create a collection named `posts`:

1. **Schema Definition**: Stored in `collections` table (metadata)
2. **Table Creation**: Physical `col_posts` table created (if doesn't exist)
3. **API Generation**: `/api/v1/records/posts` endpoints registered
4. **Usage**: All accounts use the same physical table

```
collections table (metadata):
┌─────────────┬──────────────┬─────────────┬────────────────────────┐
│ id          │ name         │ account_id  │ migration_revision     │
├─────────────┼──────────────┼─────────────┼────────────────────────┤
│ col_abc123  │ posts        │ AB1001      │ 20250101_create_posts  │  ← Who created it
│ col_def456  │ products     │ XY2048      │ 20250102_products      │
└─────────────┴──────────────┴─────────────┴────────────────────────┘

col_posts table (actual data - ONE table for ALL accounts):
┌─────────────┬─────────────┬───────────────┬─────────────┬───────────────┬─────────────┐
│ id          │ title       │ content       │ account_id  │ created_at    │ updated_by  │
├─────────────┼─────────────┼───────────────┼─────────────┼───────────────┼─────────────┤
│ post_001    │ Hello       │ Welcome...    │ AB1001      │ 2025-01-01... │ user_123    │  ← AB1001's data
│ post_002    │ Acme News   │ Latest...     │ AB1001      │ 2025-01-02... │ user_456    │
│ post_003    │ Globex Post │ Update...     │ XY2048      │ 2025-01-03... │ user_789    │  ← XY2048's data
└─────────────┴─────────────┴───────────────┴─────────────┴───────────────┴─────────────┘
```

> **Screenshot Placeholder 5**
>
> **Description**: Side-by-side view of the collections table (schema metadata) and the col_posts table (actual data with account isolation).

### Table Naming Convention

**Critical**: Collection tables are prefixed with `col_` to avoid conflicts with system tables.

| Collection Name | Physical Table Name |
|----------------|---------------------|
| `posts` | `col_posts` |
| `products` | `col_products` |
| `users` | `col_users` |

> **Screenshot Placeholder 6**
>
> **Description**: A table showing collection names and their corresponding physical table names with the col_ prefix.

### Why This Design?

| Approach | Pros | Cons | SnackBase |
|----------|------|------|-----------|
| **Table per Account** | Complete isolation | Thousands of tables, complex migrations | ❌ |
| **Database per Account** | Maximum isolation | Complex operations, resource intensive | ❌ |
| **Shared Table** | Simple, scalable, efficient | Requires account filtering | ✅ **Chosen** |

> **Screenshot Placeholder 7**
>
> **Description**: A comparison table showing three multi-tenancy approaches with pros/cons, highlighting the shared table choice.

---

## Field Types

Collections support multiple field types with built-in validation.

### Available Field Types

| Type | Description | Database Type | Example |
|------|-------------|---------------|---------|
| **text** | Single-line text | `VARCHAR` | Name, title |
| **number** | Numeric value | `NUMERIC` | Price, quantity |
| **boolean** | True/false | `BOOLEAN` | is_published |
| **datetime** | Date/time with validation | `TIMESTAMP` | published_at, created_at |
| **email** | Email with validation | `VARCHAR` | user@example.com |
| **url** | URL with validation | `VARCHAR` | https://example.com |
| **json** | JSON data | `JSONB` | metadata |
| **reference** | Reference to another collection | `VARCHAR` (FK) | user_id |
| **file** | File upload reference | `VARCHAR` | avatar_url |

> **Screenshot Placeholder 8**
>
> **Description**: A table showing all available field types with their descriptions, underlying database types, and usage examples.

### Field Configuration

Each field type has specific configuration options:

#### Text Field
```json
{
  "name": "title",
  "type": "text",
  "required": true,
  "default": null,
  "unique": false
}
```

#### Number Field
```json
{
  "name": "price",
  "type": "number",
  "required": true,
  "default": 0,
  "min": 0,
  "max": 1000000
}
```

#### DateTime Field
```json
{
  "name": "published_at",
  "type": "datetime",
  "required": false,
  "default": null
}
```

#### Email Field
```json
{
  "name": "author_email",
  "type": "email",
  "required": true,
  "unique": true
}
```

#### URL Field
```json
{
  "name": "website",
  "type": "url",
  "required": false
}
```

#### JSON Field
```json
{
  "name": "metadata",
  "type": "json",
  "required": false,
  "default": "{}"
}
```

#### Reference Field
```json
{
  "name": "author_id",
  "type": "reference",
  "target_collection": "users",
  "on_delete": "set_null",
  "required": false
}
```

#### File Field
```json
{
  "name": "attachment",
  "type": "file",
  "required": false,
  "max_size": 10485760
}
```

> **Screenshot Placeholder 9**
>
> **Description**: Code examples showing JSON configuration for different field types with their options highlighted.

---

## Dynamic Table Generation

SnackBase dynamically creates and modifies database tables based on collection schemas.

### Table Creation Flow

```
1. User creates collection via UI or API
   POST /api/v1/collections
   {
     "name": "posts",
     "schema": { "fields": [...] }
   }

2. System validates collection name
   - Must be alphanumeric with underscores
   - Cannot conflict with system tables
   - Cannot conflict with existing collections

3. System generates SQL
   CREATE TABLE IF NOT EXISTS col_posts (
     id VARCHAR(50) PRIMARY KEY,
     account_id VARCHAR(10) NOT NULL,
     title VARCHAR NOT NULL,
     content TEXT,
     status VARCHAR,
     views NUMERIC DEFAULT 0,
     published_at TIMESTAMP,
     author_email VARCHAR,
     cover_image VARCHAR,
     metadata JSONB,
     created_at TIMESTAMP DEFAULT NOW(),
     created_by VARCHAR(50),
     updated_at TIMESTAMP DEFAULT NOW(),
     updated_by VARCHAR(50),
     FOREIGN KEY (account_id) REFERENCES accounts(id),
     FOREIGN KEY (created_by) REFERENCES users(id),
     FOREIGN KEY (updated_by) REFERENCES users(id)
   );

4. System executes SQL via SQLAlchemy

5. System registers API routes
   GET    /api/v1/records/posts
   POST   /api/v1/records/posts
   GET    /api/v1/records/posts/:id
   PUT    /api/v1/records/posts/:id
   DELETE /api/v1/records/posts/:id
```

> **Screenshot Placeholder 10**
>
> **Description**: A flow diagram showing the step-by-step process from collection creation to table generation and API registration.

### Built-in Fields

Every collection table includes **automatic fields** you don't need to define:

| Field | Type | Description | Auto-Managed |
|-------|------|-------------|--------------|
| `id` | VARCHAR | Unique record ID | ✅ Auto-generated |
| `account_id` | VARCHAR(10) | Account isolation | ✅ Automatic |
| `created_at` | TIMESTAMP | Creation timestamp | ✅ Auto-set |
| `created_by` | VARCHAR(50) | Creator user ID | ✅ Auto-set |
| `updated_at` | TIMESTAMP | Last update timestamp | ✅ Auto-updated |
| `updated_by` | VARCHAR(50) | Last updater user ID | ✅ Auto-updated |

> **Screenshot Placeholder 11**
>
> **Description**: A table showing built-in fields that are automatically added to every collection, with auto-managed indicators.

### Indexes and Constraints

SnackBase automatically creates:

```sql
-- Primary key
PRIMARY KEY (id)

-- Account isolation index
INDEX idx_col_posts_account_id ON col_posts(account_id);

-- Timestamp indexes
INDEX idx_col_posts_created_at ON col_posts(created_at);
INDEX idx_col_posts_updated_at ON col_posts(updated_at);

-- Unique constraints (if specified)
UNIQUE (title)  -- if field.unique = true

-- Foreign keys
FOREIGN KEY (account_id) REFERENCES accounts(id)
FOREIGN KEY (created_by) REFERENCES users(id)
FOREIGN KEY (updated_by) REFERENCES users(id)
```

> **Screenshot Placeholder 12**
>
> **Description**: A code snippet showing the automatically created indexes and constraints when a collection table is generated.

---

## Auto-Generated APIs

Each collection automatically gets a complete REST API.

### Generated Endpoints

For a collection named `posts`:

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/v1/records/posts` | List all records (with filtering) | `posts:read` |
| POST | `/api/v1/records/posts` | Create a new record | `posts:create` |
| GET | `/api/v1/records/posts/:id` | Get single record | `posts:read` |
| PATCH | `/api/v1/records/posts/:id` | Partial update record | `posts:update` |
| PUT | `/api/v1/records/posts/:id` | Full update record | `posts:update` |
| DELETE | `/api/v1/records/posts/:id` | Delete record | `posts:delete` |
| POST | `/api/v1/records/posts/bulk` | Bulk operations | `posts:create`/`update`/`delete` |

> **Screenshot Placeholder 13**
>
> **Description**: A table showing all auto-generated API endpoints for a collection with their HTTP methods, paths, descriptions, and required permissions.

### API Usage Examples

```bash
# Create a record
POST /api/v1/records/posts
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "My First Post",
  "content": "This is the content",
  "status": "published",
  "views": 0,
  "author_email": "author@example.com",
  "cover_image": "https://example.com/image.jpg",
  "metadata": {
    "seo_title": "SEO Title",
    "tags": ["tag1", "tag2"]
  }
}

# Response
{
  "id": "post_abc123",
  "title": "My First Post",
  "content": "This is the content",
  "status": "published",
  "views": 0,
  "author_email": "author@example.com",
  "cover_image": "https://example.com/image.jpg",
  "metadata": {
    "seo_title": "SEO Title",
    "tags": ["tag1", "tag2"]
  },
  "account_id": "AB1001",
  "created_at": "2025-01-01T00:00:00Z",
  "created_by": "user_xyz789",
  "updated_at": "2025-01-01T00:00:00Z",
  "updated_by": "user_xyz789"
}
```

> **Screenshot Placeholder 14**
>
> **Description**: A code example showing a POST request to create a record and the JSON response with auto-generated fields.

### Query Filtering

List endpoints support powerful filtering:

```bash
# Basic filtering
GET /api/v1/records/posts?status=published

# Multiple filters
GET /api/v1/records/posts?status=published&views.gt=100

# Sorting
GET /api/v1/records/posts?sort=-created_at

# Pagination
GET /api/v1/records/posts?page=1&limit=20

# Full text search (if configured)
GET /api/v1/records/posts?q=hello

# Date range filtering
GET /api/v1/records/posts?created_at.gte=2025-01-01T00:00:00Z
```

> **Screenshot Placeholder 15**
>
> **Description**: A code example showing various query parameters for filtering, sorting, pagination, and search on the list endpoint.

---

## PII Masking

SnackBase provides **automatic PII (Personally Identifiable Information) masking** to protect sensitive user data. This is a critical privacy feature for compliance with regulations like GDPR, CCPA, and HIPAA.

### How PII Masking Works

PII fields are automatically masked for users who don't have the `pii_access` group membership:

```json
// User without pii_access sees:
{
  "id": "user_123",
  "email": "j***@example.com",      // Masked
  "phone": "***-***-1234",          // Masked
  "ssn": "***-**-****",             // Masked
  "name": "John D."                 // Masked
}

// User with pii_access sees:
{
  "id": "user_123",
  "email": "john.doe@example.com",  // Full value
  "phone": "555-123-4567",          // Full value
  "ssn": "123-45-6789",             // Full value
  "name": "John Doe"                // Full value
}
```

> **Screenshot Placeholder 16**
>
> **Description**: Side-by-side comparison showing masked vs unmasked data for users with and without pii_access.

### PII Mask Types

| Mask Type | Description | Example |
|-----------|-------------|---------|
| **email** | Shows first character and domain | `j***@example.com` |
| **ssn** | Shows only format | `***-**-****` |
| **phone** | Shows last 4 digits | `***-***-1234` |
| **name** | Shows first name initial and last initial | `John D.` |
| **full** | Completely hides value | `******` |
| **custom** | Custom mask pattern | Configurable |

> **Screenshot Placeholder 17**
>
> **Description**: A table showing all available PII mask types with examples of how each type masks data.

### Configuring PII Fields

To enable PII masking on a field, use the `pii_mask` configuration:

```json
{
  "fields": [
    {
      "name": "email",
      "type": "email",
      "pii_mask": {
        "enabled": true,
        "mask_type": "email"
      }
    },
    {
      "name": "ssn",
      "type": "text",
      "pii_mask": {
        "enabled": true,
        "mask_type": "ssn"
      }
    },
    {
      "name": "phone",
      "type": "text",
      "pii_mask": {
        "enabled": true,
        "mask_type": "phone"
      }
    }
  ]
}
```

> **Screenshot Placeholder 18**
>
> **Description**: JSON configuration example showing how to enable PII masking on different field types.

### Granting PII Access

PII access is controlled via group membership:

```python
# Add user to pii_access group
await group_service.add_user_to_group(
    user_id="user_123",
    group_name="pii_access",
    account_id="AB1001"
)
```

Users in the `pii_access` group can view unmasked PII data. All other users see masked values.

> **Screenshot Placeholder 19**
>
> **Description**: UI screenshot showing group management with the pii_access group and member list.

---

## Reference Fields

Reference fields allow you to create relationships between collections using foreign keys.

### Reference Field Configuration

```json
{
  "name": "author_id",
  "type": "reference",
  "target_collection": "users",
  "on_delete": "set_null",
  "required": false
}
```

> **Screenshot Placeholder 20**
>
> **Description**: JSON configuration for a reference field showing all available options.

### on_delete Actions

| Action | Description | Use Case |
|--------|-------------|----------|
| **cascade** | Delete referenced record when target is deleted | Dependent data (order items → orders) |
| **set_null** | Set field to NULL when target is deleted | Optional relationships |
| **restrict** | Prevent deletion if referenced | Critical references (users → orders) |

> **Screenshot Placeholder 21**
>
> **Description**: A table showing the three on_delete actions with descriptions and typical use cases.

### Reference Field Example

```json
// Posts collection with author reference
{
  "name": "posts",
  "schema": {
    "fields": [
      { "name": "title", "type": "text" },
      {
        "name": "author_id",
        "type": "reference",
        "target_collection": "users",
        "on_delete": "set_null",
        "required": false
      }
    ]
  }
}
```

This creates a foreign key constraint:

```sql
ALTER TABLE col_posts
ADD CONSTRAINT fk_posts_author
FOREIGN KEY (author_id)
REFERENCES col_users(id)
ON DELETE SET NULL;
```

> **Screenshot Placeholder 22**
>
> **Description**: A diagram showing the relationship between posts and users collections with a foreign key.

### Reference Validation

When creating or updating records with reference fields:

```bash
# Valid reference
POST /api/v1/records/posts
{
  "title": "My Post",
  "author_id": "user_abc123"  # ✅ Exists in users collection
}

# Invalid reference
POST /api/v1/records/posts
{
  "title": "My Post",
  "author_id": "user_xyz999"  # ❌ Does not exist - 400 Bad Request
}
```

> **Screenshot Placeholder 23**
>
> **Description**: Code examples showing valid and invalid reference field values with API responses.

---

## Schema Evolution

Collections can evolve over time with schema updates.

### Supported Changes

| Change | Supported | Notes |
|--------|-----------|-------|
| Add new field | ✅ Yes | New field added to table |
| Remove field | ❌ **No** | Field deletion is NOT allowed |
| Rename field | ❌ **No** | Must create new field instead |
| Change type | ❌ **No** | Type changes are NOT allowed |
| Modify field options | ✅ Yes | Adding options is supported |

> **Screenshot Placeholder 24**
>
> **Description**: A table showing supported schema changes with traffic light indicators (green for allowed, red for not allowed).

### Schema Update Flow

```
1. User updates collection schema
   PUT /api/v1/collections/:id
   {
     "schema": { "fields": [...] }
   }

2. System validates changes
   - Field names are unique
   - Types are valid
   - No field deletions
   - No type changes

3. System generates ALTER TABLE statements
   ALTER TABLE col_posts ADD COLUMN category TEXT;

4. System executes SQL

5. Updated schema applies immediately
   - New API validation
   - Updated forms in UI
```

> **Screenshot Placeholder 25**
>
> **Description**: A flow diagram showing the schema update process from API request to validation to SQL generation to execution.

### Schema Evolution Rules

**Field Addition** (Only supported operation):

```json
// Before: Collection with 3 fields
{
  "name": "posts",
  "schema": {
    "fields": [
      { "name": "title", "type": "text" },
      { "name": "content", "type": "text" },
      { "name": "status", "type": "text" }
    ]
  }
}

// After: Add new field "category"
{
  "name": "posts",
  "schema": {
    "fields": [
      { "name": "title", "type": "text" },
      { "name": "content", "type": "text" },
      { "name": "status", "type": "text" },
      { "name": "category", "type": "text" }  // ✅ New field added
    ]
  }
}
```

**Field Deletion** (NOT allowed):

```json
// Attempting to remove "status" field
{
  "name": "posts",
  "schema": {
    "fields": [
      { "name": "title", "type": "text" },
      { "name": "content", "type": "text" }
      // "status" removed - ❌ NOT ALLOWED
    ]
  }
}

// System response: 400 Bad Request
{
  "error": "Cannot remove fields from schema",
  "detail": "Field removal is not supported. Fields can only be added."
}
```

**Type Changes** (NOT allowed):

```json
// Attempting to change field type
{
  "fields": [
    { "name": "views", "type": "text" }  // ❌ Was "number", now "text"
  ]
}

// System response: 400 Bad Request
{
  "error": "Cannot change field types",
  "detail": "Type changes are not supported. Create a new field instead."
}
```

> **Screenshot Placeholder 26**
>
> **Description**: A warning dialog UI showing error messages when attempting unsupported schema changes.

### Migration Revision Tracking

Collections include a `migration_revision` field to track which migration created or modified them:

```json
{
  "id": "col_abc123",
  "name": "posts",
  "migration_revision": "20250101_create_posts",
  "schema": { "fields": [...] }
}
```

This helps with:
- Tracking schema changes over time
- Rolling back to specific revisions
- Auditing collection modifications
- Understanding the evolution of your data model

> **Screenshot Placeholder 27**
>
> **Description**: A timeline diagram showing collection revisions over time with migration markers.

---

## Best Practices

### 1. Naming Conventions

Use **lowercase, plural** names for collections:

| Good | Bad |
|------|-----|
| `posts` | `Posts` |
| `users` | `user` |
| `blog_posts` | `BlogPosts` |
| `order_items` | `order-items` |

> **Screenshot Placeholder 28**
>
> **Description**: A comparison table showing good vs bad collection naming conventions with checkmarks and X marks.

### 2. Field Naming

Use **snake_case** for field names:

```json
{
  "fields": [
    { "name": "first_name", "type": "text" },   // ✅ Good
    { "name": "lastName", "type": "text" },     // ❌ Bad
    { "name": "Email-Address", "type": "email" } // ❌ Bad
  ]
}
```

> **Screenshot Placeholder 29**
>
> **Description**: Code examples showing good (snake_case) and bad (mixed case, hyphens) field naming practices.

### 3. Use Appropriate Field Types

Choose the most specific type for your data:

```json
{
  "fields": [
    { "name": "email", "type": "email" },      // ✅ Specific type
    { "name": "published_at", "type": "datetime" },  // ✅ With validation
    { "name": "website", "type": "url" },      // ✅ URL validation
    { "name": "metadata", "type": "json" }     // ✅ Flexible data
  ]
}
```

> **Screenshot Placeholder 30**
>
> **Description**: Code examples showing appropriate field type selection for different use cases.

### 4. Use JSON for Flexible Data

For metadata or varying structures:

```json
{
  "name": "metadata",
  "type": "json"
}
```

Store arbitrary data:
```json
{
  "metadata": {
    "seo_title": "SEO Title",
    "seo_description": "Description",
    "tags": ["tag1", "tag2"],
    "custom_field": "any value"
  }
}
```

> **Screenshot Placeholder 31**
>
> **Description**: Code example showing a JSON field storing complex nested data with various data types.

### 5. Plan Schema Evolution

Design schemas with evolution in mind:

- Only add new fields (deletion and type changes are not allowed)
- Use `required: false` for fields that might be optional later
- Document schema changes in migration revisions
- Test schema updates in development first

> **Screenshot Placeholder 32**
>
> **Description**: A checklist or flowchart showing considerations for schema evolution planning.

### 6. Use PII Masking for Sensitive Data

Protect user privacy with automatic PII masking:

```json
{
  "name": "email",
  "type": "email",
  "pii_mask": {
    "enabled": true,
    "mask_type": "email"
  }
}
```

This ensures compliance with privacy regulations by default.

> **Screenshot Placeholder 33**
>
> **Description**: Code example showing PII masking configuration with a security shield icon.

### 7. Choose Appropriate on_delete Actions

Select the right action for reference fields:

| Scenario | Action |
|----------|--------|
| Optional relationships (posts → authors) | `set_null` |
| Dependent data (order items → orders) | `cascade` |
| Critical references (prevent deletion) | `restrict` |

> **Screenshot Placeholder 34**
>
> **Description**: A decision tree diagram showing how to choose the appropriate on_delete action.

### 8. Avoid Too Many Collections

Each collection creates a table. Consider:

- Can related data be in the same collection?
- Would JSON fields work better for varying schemas?
- Do you really need separate tables?

**Example**: Instead of `blog_posts` and `news_posts`, use `posts` with a `category` field.

> **Screenshot Placeholder 35**
>
> **Description**: A decision tree diagram showing when to create separate collections vs using a single collection with categorization.

---

## Summary

| Concept | Key Takeaway |
|---------|--------------|
| **Collection Definition** | Named schema with fields, stored in `collections` table |
| **Collection vs Table** | Collections are metadata; ONE shared table per collection for ALL accounts |
| **Table Naming** | Tables prefixed with `col_` (e.g., `col_posts`) |
| **Field Types** | 9 types available (text, number, boolean, datetime, email, url, json, reference, file) |
| **Dynamic Tables** | Tables created/modified automatically based on schema |
| **Auto-Generated APIs** | REST endpoints at `/api/v1/records/{collection}` |
| **PII Masking** | Automatic masking for sensitive data (email, ssn, phone, name) |
| **Reference Fields** | Foreign key relationships with on_delete actions |
| **Schema Evolution** | Only adding fields is allowed; deletion and type changes are NOT supported |
| **Migration Tracking** | `migration_revision` field tracks schema changes |
| **Best Practices** | Use lowercase plurals, snake_case fields, plan for evolution |

---

## Related Documentation

- [Multi-Tenancy Model](./multi-tenancy.md) - How collections work with account isolation
- [API Examples](../api-examples.md) - Working with collection APIs
- [Architecture](../architecture.md) - Overall system architecture
- [Authentication](./authentication.md) - User access and permissions

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
