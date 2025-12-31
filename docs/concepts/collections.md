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
  "schema": {
    "fields": [
      { "name": "title", "type": "text", "required": true },
      { "name": "content", "type": "text", "required": false },
      { "name": "status", "type": "select", "options": ["draft", "published"] },
      { "name": "views", "type": "number", "default": 0 }
    ]
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

> **Screenshot Placeholder 2**
>
> **Description**: A JSON representation of a collection showing its structure with id, name, description, schema fields, and metadata.

### Components of a Collection

| Component | Purpose | Example |
|-----------|---------|---------|
| **name** | Unique identifier, becomes API endpoint | `posts` → `/api/v1/posts` |
| **description** | Human-readable description | "Blog posts and articles" |
| **schema** | Field definitions with types and validation | See field types below |
| **account_id** | Owner account (ignored for global collections) | `AB1001` |

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
2. **Table Creation**: Physical `posts` table created (if doesn't exist)
3. **API Generation**: `/api/v1/posts` endpoints registered
4. **Usage**: All accounts use the same physical table

```
collections table (metadata):
┌─────────────┬──────────────┬─────────────┐
│ id          │ name         │ account_id  │
├─────────────┼──────────────┼─────────────┤
│ col_abc123  │ posts        │ AB1001      │  ← Who created it
│ col_def456  │ products     │ XY2048      │
└─────────────┴──────────────┴─────────────┘

posts table (actual data - ONE table for ALL accounts):
┌─────────────┬─────────────┬───────────────┬─────────────┐
│ id          │ title       │ content       │ account_id  │
├─────────────┼─────────────┼───────────────┼─────────────┤
│ post_001    │ Hello       │ Welcome...    │ AB1001      │  ← AB1001's data
│ post_002    │ Acme News   │ Latest...     │ AB1001      │
│ post_003    │ Globex Post │ Update...     │ XY2048      │  ← XY2048's data
└─────────────┴─────────────┴───────────────┴─────────────┘
```

> **Screenshot Placeholder 5**
>
> **Description**: Side-by-side view of the collections table (schema metadata) and the posts table (actual data with account isolation).

### Why This Design?

| Approach | Pros | Cons | SnackBase |
|----------|------|------|-----------|
| **Table per Account** | Complete isolation | Thousands of tables, complex migrations | ❌ |
| **Database per Account** | Maximum isolation | Complex operations, resource intensive | ❌ |
| **Shared Table** | Simple, scalable, efficient | Requires account filtering | ✅ **Chosen** |

> **Screenshot Placeholder 6**
>
> **Description**: A comparison table showing three multi-tenancy approaches with pros/cons, highlighting the shared table choice.

---

## Field Types

Collections support multiple field types with built-in validation.

### Available Field Types

| Type | Description | Database Type | Example |
|------|-------------|---------------|---------|
| **text** | Single-line text | `VARCHAR` | Name, email |
| **number** | Numeric value | `NUMERIC` | Price, quantity |
| **email** | Email with validation | `VARCHAR` | user@example.com |
| **boolean** | True/false | `BOOLEAN` | is_published |
| **date** | Date/time | `TIMESTAMP` | created_at |
| **json** | JSON data | `JSONB` | metadata |
| **select** | Predefined options | `VARCHAR` | status (draft, published) |
| **relation** | Reference to another collection | `VARCHAR` (FK) | user_id |

> **Screenshot Placeholder 7**
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

#### Select Field
```json
{
  "name": "status",
  "type": "select",
  "required": true,
  "options": ["draft", "published", "archived"],
  "default": "draft"
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

> **Screenshot Placeholder 8**
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
   CREATE TABLE IF NOT EXISTS posts (
     id VARCHAR(50) PRIMARY KEY,
     account_id VARCHAR(10) NOT NULL,
     title VARCHAR NOT NULL,
     content TEXT,
     status VARCHAR,
     views NUMERIC DEFAULT 0,
     created_at TIMESTAMP DEFAULT NOW(),
     created_by VARCHAR(50),
     updated_at TIMESTAMP DEFAULT NOW(),
     FOREIGN KEY (account_id) REFERENCES accounts(id),
     FOREIGN KEY (created_by) REFERENCES users(id)
   );

4. System executes SQL via SQLAlchemy

5. System registers API routes
   GET    /api/v1/posts
   POST   /api/v1/posts
   GET    /api/v1/posts/:id
   PUT    /api/v1/posts/:id
   DELETE /api/v1/posts/:id
```

> **Screenshot Placeholder 9**
>
> **Description**: A flow diagram showing the step-by-step process from collection creation to table generation and API registration.

### Built-in Fields

Every collection table includes **automatic fields** you don't need to define:

| Field | Type | Description | Auto-Managed |
|-------|------|-------------|--------------|
| `id` | VARCHAR | Unique record ID | ✅ Auto-generated |
| `account_id` | VARCHAR(10) | Account isolation | ✅ Automatic |
| `created_at` | TIMESTAMP | Creation timestamp | ✅ Auto-set |
| `updated_at` | TIMESTAMP | Last update timestamp | ✅ Auto-updated |
| `created_by` | VARCHAR(50) | Creator user ID | ✅ Auto-set |

> **Screenshot Placeholder 10**
>
> **Description**: A table showing built-in fields that are automatically added to every collection, with auto-managed indicators.

### Indexes and Constraints

SnackBase automatically creates:

```sql
-- Primary key
PRIMARY KEY (id)

-- Account isolation index
INDEX idx_posts_account_id ON posts(account_id);

-- Unique constraints (if specified)
UNIQUE (title)  -- if field.unique = true

-- Foreign keys
FOREIGN KEY (account_id) REFERENCES accounts(id)
FOREIGN KEY (created_by) REFERENCES users(id)
```

> **Screenshot Placeholder 11**
>
> **Description**: A code snippet showing the automatically created indexes and constraints when a collection table is generated.

---

## Auto-Generated APIs

Each collection automatically gets a complete REST API.

### Generated Endpoints

For a collection named `posts`:

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/v1/posts` | List all records (with filtering) | `posts:read` |
| POST | `/api/v1/posts` | Create a new record | `posts:create` |
| GET | `/api/v1/posts/:id` | Get single record | `posts:read` |
| PUT | `/api/v1/posts/:id` | Update record | `posts:update` |
| DELETE | `/api/v1/posts/:id` | Delete record | `posts:delete` |
| POST | `/api/v1/posts/bulk` | Bulk operations | `posts:create`/`update`/`delete` |

> **Screenshot Placeholder 12**
>
> **Description**: A table showing all auto-generated API endpoints for a collection with their HTTP methods, paths, descriptions, and required permissions.

### API Usage Examples

```bash
# Create a record
POST /api/v1/posts
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "My First Post",
  "content": "This is the content",
  "status": "published",
  "views": 0
}

# Response
{
  "id": "post_abc123",
  "title": "My First Post",
  "content": "This is the content",
  "status": "published",
  "views": 0,
  "account_id": "AB1001",
  "created_at": "2025-01-01T00:00:00Z",
  "created_by": "user_xyz789",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

> **Screenshot Placeholder 13**
>
> **Description**: A code example showing a POST request to create a record and the JSON response with auto-generated fields.

### Query Filtering

List endpoints support powerful filtering:

```bash
# Basic filtering
GET /api/v1/posts?status=published

# Multiple filters
GET /api/v1/posts?status=published&views.gt=100

# Sorting
GET /api/v1/posts?sort=-created_at

# Pagination
GET /api/v1/posts?page=1&limit=20

# Full text search (if configured)
GET /api/v1/posts?q=hello
```

> **Screenshot Placeholder 14**
>
> **Description**: A code example showing various query parameters for filtering, sorting, pagination, and search on the list endpoint.

---

## Schema Evolution

Collections can evolve over time with schema updates.

### Supported Changes

| Change | Supported | Notes |
|--------|-----------|-------|
| Add new field | ✅ Yes | New field added to table |
| Remove field | ✅ Yes | Column dropped (data lost!) |
| Rename field | ⚠️ Caution | Drop + recreate (data lost) |
| Change type | ⚠️ Caution | May require data migration |
| Add options to select | ✅ Yes | New options added |
| Remove options from select | ⚠️ Caution | Existing records may have invalid values |

> **Screenshot Placeholder 15**
>
> **Description**: A table showing supported schema changes with traffic light indicators (green for safe, yellow for caution, red for data loss).

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
   - No breaking changes (if enforced)

3. System generates ALTER TABLE statements
   ALTER TABLE posts ADD COLUMN category TEXT;
   ALTER TABLE posts DROP COLUMN old_field;

4. System executes SQL

5. Updated schema applies immediately
   - New API validation
   - Updated forms in UI
```

> **Screenshot Placeholder 16**
>
> **Description**: A flow diagram showing the schema update process from API request to validation to SQL generation to execution.

### Data Loss Warning

⚠️ **Removing fields or changing types can cause data loss!**

```json
// Before: Collection has "summary" field
{
  "name": "posts",
  "schema": {
    "fields": [
      { "name": "title", "type": "text" },
      { "name": "summary", "type": "text" }  // ← This field exists
    ]
  }
}

// After: "summary" field removed
{
  "name": "posts",
  "schema": {
    "fields": [
      { "name": "title", "type": "text" }
      // "summary" removed - ALL DATA IN THIS COLUMN IS LOST!
    ]
  }
}
```

> **Screenshot Placeholder 17**
>
> **Description**: A warning dialog UI showing a confirmation message when removing a field, with a clear warning about data loss.

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

> **Screenshot Placeholder 18**
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

> **Screenshot Placeholder 19**
>
> **Description**: Code examples showing good (snake_case) and bad (mixed case, hyphens) field naming practices.

### 3. Use Select Fields for Fixed Values

For fields with limited options, use `select` type:

```json
{
  "name": "status",
  "type": "select",
  "options": ["draft", "published", "archived"]
}
```

This provides:
- Built-in validation
- UI dropdowns
- Type safety

> **Screenshot Placeholder 20**
>
> **Description**: A UI screenshot showing a select field in a form with a dropdown menu displaying the predefined options.

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

> **Screenshot Placeholder 21**
>
> **Description**: Code example showing a JSON field storing complex nested data with various data types.

### 5. Plan Schema Evolution

Design schemas with evolution in mind:

- Add new fields rather than modifying existing ones
- Use `required: false` for fields that might be optional later
- Document breaking changes
- Test schema updates in development first

> **Screenshot Placeholder 22**
>
> **Description**: A checklist or flowchart showing considerations for schema evolution planning.

### 6. Avoid Too Many Collections

Each collection creates a table. Consider:

- Can related data be in the same collection?
- Would JSON fields work better for varying schemas?
- Do you really need separate tables?

**Example**: Instead of `blog_posts` and `news_posts`, use `posts` with a `category` field.

> **Screenshot Placeholder 23**
>
> **Description**: A decision tree diagram showing when to create separate collections vs using a single collection with categorization.

---

## Summary

| Concept | Key Takeaway |
|---------|--------------|
| **Collection Definition** | Named schema with fields, stored in `collections` table |
| **Collection vs Table** | Collections are metadata; ONE shared table per collection for ALL accounts |
| **Field Types** | 8 types available (text, number, email, boolean, date, json, select, relation) |
| **Dynamic Tables** | Tables created/modified automatically based on schema |
| **Auto-Generated APIs** | REST endpoints generated automatically for each collection |
| **Schema Evolution** | Schemas can evolve; be cautious of data loss when removing fields |
| **Best Practices** | Use lowercase plurals, snake_case fields, plan for evolution |

---

## Related Documentation

- [Multi-Tenancy Model](./multi-tenancy.md) - How collections work with account isolation
- [API Examples](../api-examples.md) - Working with collection APIs
- [Architecture](../architecture.md) - Overall system architecture

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
