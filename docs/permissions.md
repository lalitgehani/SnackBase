# Permissions & Authorization (V2)

SnackBase V2 uses a database-centric **Row-Level Security (RLS)** model inspired by Supabase and PocketBase. Access control is defined directly on collections using simple SQL-native expressions that compile to `WHERE` clauses.

## Core Concepts

### 5-Operation Model

Unlike traditional CRUD, SnackBase splits "Read" into two distinct operations for better control:

1.  **list**: Filter records returned in list/browse operations.
2.  **view**: Filter/validate access to a specific single record.
3.  **create**: Validate data and ownership during record creation.
4.  **update**: Filter which records can be updated and validate new data.
5.  **delete**: Filter which records can be deleted.

### Rule Storage

Rules are stored in the `collection_rules` table and are associated 1:1 with a collection. Each operation can be in one of three states:

| Rule State      | Meaning                        | Example                         |
| :-------------- | :----------------------------- | :------------------------------ |
| `null` (Locked) | Only superadmin can access.    | Internal config tables.         |
| `""` (Public)   | Anyone can access (no filter). | Blog posts, public profiles.    |
| `"expression"`  | SQL filter expression.         | `created_by = @request.auth.id` |

---

## Rule Syntax

Rules are written in a simple expression language that supports logical operators, comparisons, and context variables.

### Variables

| Variable          | Description                     | Fields                                                              |
| :---------------- | :------------------------------ | :------------------------------------------------------------------ |
| `@request.auth.*` | The authenticated user.         | `id`, `email`, `role`, `account_id`                                 |
| `@request.data.*` | Incoming request body data.     | Any field in the request body (create/update only).                 |
| `fieldname`       | Direct access to record fields. | Any field in the current collection (e.g., `status`, `created_by`). |

### Operators

| Category       | Operator  | Description             | Example                              |
| :------------- | :-------- | :---------------------- | :----------------------------------- | ---------- | ----------------------------- | --- | -------------- |
| **Comparison** | `=`       | Equal to                | `status = "active"`                  |
|                | `!=`      | Not equal to            | `status != "archived"`               |
|                | `~`       | LIKE (case-insensitive) | `title ~ "%important%"`              |
|                | `<` `>`   | Less/Greater than       | `score > 10`                         |
|                | `<=` `>=` | Less/Greater or equal   | `amount >= 100`                      |
| **Logical**    | `&&`      | Logical AND             | `status = "active" && public = true` |
|                | `         |                         | `                                    | Logical OR | `@request.auth.role = "admin" |     | public = true` |
|                | `!`       | Logical NOT             | `!is_locked`                         |

---

## Built-in Macros

Macros are reusable expression fragments that are expanded before SQL compilation.

### `@owns_record()`

Expands to: `created_by = @request.auth.id`
Use case: Grant access to the user who created the record.

### `@request.auth.role = "admin"`

While not a macro itself, check for the user's role directly in the expression.

---

## Field-Level Access Control

You can specify which fields are accessible for each of the 5 operations.

- **Wildcard (`*`)**: All fields are allowed.
- **Explicit List**: E.g., `["id", "title", "content"]`.
- **System Fields**: `id`, `created_at`, `updated_at`, `created_by`, `account_id` are always managed by the system and cannot be modified via rules.

---

## Performance & Caching

1.  **SQL-Native**: Rules are compiled into SQL `WHERE` clauses. If a user tries to list records, the database only returns the ones they are allowed to see.
2.  **No Python Post-Filtering**: Unlike V1, there is no performance penalty for fetching large datasets because the filtering happens at the database level.
3.  **Superadmin Bypass**: Superadmins (system account users) bypass all rules automatically.

---

## Migration Guide (V1 to V2)

SnackBase V2 is **not backward compatible** with V1 permissions. You must manually migrate your rules.

### Key Changes

| Aspect            | V1 (Old)                       | V2 (New)                                  |
| :---------------- | :----------------------------- | :---------------------------------------- |
| **Rule Location** | Per Role (`permissions` table) | Per Collection (`collection_rules` table) |
| **Evaluation**    | Python-based AST               | SQL-native `WHERE` clauses                |
| **Operations**    | 4 (CRUD)                       | 5 (list, view, create, update, delete)    |
| **Variables**     | `user.id`, `record.owner_id`   | `@request.auth.id`, `created_by`          |
| **Public access** | Complex rule                   | Empty string `""`                         |

### Translation Table

| Old Rule (V1)                  | New Rule (V2)                   |
| :----------------------------- | :------------------------------ |
| `user.role == "admin"`         | `@request.auth.role = "admin"`  |
| `@owns_record()`               | `created_by = @request.auth.id` |
| `user.id == record.owner_id`   | `created_by = @request.auth.id` |
| `record.status == "published"` | `status = "published"`          |
| `true`                         | `""` (Empty string)             |

### Migration Steps

1.  Upgrading to V2 will create the `collection_rules` table but will **NOT** automatically migrate data.
2.  Export your V1 rules via the API if needed for reference.
3.  For each collection, go to **Collection Settings > Rules** in the Admin UI and recreate your logic.
4.  Verify list/view/modify access.
5.  Run the deprecation migration to drop the old `permissions` table.

---

## API Endpoints

### Get Collection Rules

`GET /api/v1/collections/{name}/rules`

### Update Collection Rules

`PUT /api/v1/collections/{name}/rules`

**Request Body:**

```json
{
  "list_rule": "created_by = @request.auth.id",
  "view_rule": "",
  "create_rule": "@request.auth.id != ''",
  "list_fields": ["id", "title"]
}
```
