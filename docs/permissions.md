# Permissions & Authorization

SnackBase uses a powerful expression language for defining granular access control rules. This guide covers the syntax, available variables, operations, caching, and common patterns for securing your data.

## Overview

Permissions are defined per **Role** and **Collection**. Each permission rule consists of:

1. **Operation**: `create`, `read`, `update`, `delete`
2. **Rule Expression**: A logic string that evaluates to `true` (allow) or `false` (deny)
3. **Allowed Fields**: A list of fields (or `*`) that are accessible

### Permission Resolution Order

SnackBase resolves permissions in the following order:

1. **Role-Specific Rules**: Rules for the user's role on the specific collection
2. **Wildcard Collection Rules**: Rules for the `*` collection apply if no specific collection rule matches
3. **Deny by Default**: If no rule matches, access is denied

If multiple permissions match (e.g., role + wildcard), they are combined with **OR** logic. If any rule evaluates to `true`, access is granted.

### Superadmin Bypass

Users with `account_id == "00000000-0000-0000-0000-000000000000"` (superadmins) bypass **ALL** permission checks. Superadmins automatically get:

- Full access to all collections
- All field-level access
- Bypass of rule evaluation

This is the system account identifier and is hardcoded for security.

---

## Rule Syntax

Rules are written in a simple expression language similar to Python or SQL.

### Variables

You can access the following context variables in your rules:

| Variable  | Description                                        | Fields                                               |
| :-------- | :------------------------------------------------- | :--------------------------------------------------- |
| `user`    | The currently authenticated user                   | `id`, `email`, `role`, `account_id`, `groups`        |
| `record`  | The record being accessed (for read/update/delete) | All record fields (e.g., `id`, `owner_id`, `status`) |
| `account` | The current account context                        | `id`                                                 |

**Note**: For `create` operations, the `record` variable represents the data being submitted.

### Operators

| Category       | Operator  | Description           | Example                                 |
| :------------- | :-------- | :-------------------- | :-------------------------------------- |
| **Comparison** | `==`      | Equal to              | `user.id == record.owner_id`            |
|                | `!=`      | Not equal to          | `record.status != "archived"`           |
|                | `<` `>`   | Less/Greater than     | `record.score > 10`                     |
|                | `<=` `>=` | Less/Greater or equal | `record.amount >= 100`                  |
|                | `in`      | Membership check      | `"admin" in user.groups`                |
| **Logical**    | `and`     | Logical AND           | `user.isActive and record.public`       |
|                | `or`      | Logical OR            | `user.role == "admin" or record.public` |
|                | `not`     | Logical NOT           | `not record.is_locked`                  |

### Functions

| Function                   | Description                  | Example                                 |
| :------------------------- | :--------------------------- | :-------------------------------------- |
| `contains(list, item)`     | Checks if list contains item | `contains(user.groups, "manager")`      |
| `starts_with(str, prefix)` | Checks string prefix         | `starts_with(record.sku, "PROD-")`      |
| `ends_with(str, suffix)`   | Checks string suffix         | `ends_with(user.email, "@company.com")` |

### Literals

- **Strings**: `"text"` or `'text'`
- **Numbers**: `123`, `45.67`
- **Booleans**: `true`, `false`
- **Null/None**: `null`
- **Lists**: `['a', 'b', 'c']`

---

## Built-in Macros

Built-in macros are predefined functions that simplify common permission patterns. They are always available and don't need to be created.

### @has_group(group_name)

Check if the user belongs to a specific group.

```python
# Allow access to managers only
@has_group("managers")

# Alternative syntax
"managers" in user.groups
```

### @has_role(role_name)

Check if the user has a specific role.

```python
# Allow access to admins only
@has_role("admin")

# Alternative syntax
user.role == "admin"
```

### @owns_record() / @is_creator()

Check if the user owns the record (compares `user.id` with `record.owner_id`).

```python
# Allow users to manage their own records
@owns_record()

# Alternative syntax
user.id == record.owner_id

# Note: For records created via SnackBase, you can also use created_by
user.id == record.created_by
```

### @in_time_range(start_hour, end_hour)

Check if the current time is within a specific hour range (24-hour format).

```python
# Allow access only during business hours (9 AM - 5 PM)
@in_time_range(9, 17)

# Night shift access (10 PM - 6 AM)
@in_time_range(22, 6)
```

### @has_permission(operation, collection)

Check if the user has a specific permission on a collection.

```python
# Allow users who can delete posts to also manage comments
@has_permission("delete", "posts")
```

---

## SQL Macros

SQL macros allow you to create custom permission logic using SQL queries. They are stored in the database and can be reused across permissions.

### Creating SQL Macros

SQL macros are created via the API:

```bash
POST /api/v1/macros
{
  "name": "is_department_head",
  "description": "Check if user is department head",
  "parameters": ["department_id"],
  "sql_query": "SELECT EXISTS(SELECT 1 FROM department_members WHERE user_id = :user_id AND department_id = :department_id AND role = 'head')"
}
```

### Using SQL Macros

Use SQL macros in permission rules just like built-in macros:

```python
@is_department_header("dept_123")
```

### SQL Macro Features

- **Parameter Binding**: Parameters are bound safely to prevent SQL injection
- **5-Second Timeout**: Queries are automatically terminated after 5 seconds
- **Error Handling**: Query errors return `false` (deny) for security
- **Result Caching**: Results are cached per-request for performance
- **Return Values**: Should return a boolean value (true/false)

### SQL Macro Examples

```sql
-- Check if user has enough balance
SELECT balance >= :amount FROM accounts WHERE user_id = :user_id

-- Check if record is in user's region
SELECT EXISTS(
  SELECT 1 FROM user_regions
  WHERE user_id = :user_id
  AND region_id = :region_id
)

-- Complex business logic
SELECT CASE
  WHEN :user_id IN (SELECT manager_id FROM departments WHERE id = :dept_id) THEN true
  WHEN :user_id IN (SELECT user_id FROM department_members WHERE department_id = :dept_id AND role = 'admin') THEN true
  ELSE false
END
```

---

## System Fields

System fields are automatically managed by SnackBase and cannot be written via the API. They are **always readable** but **never writable**.

### System Fields List

| Field        | Description                              |
| :----------- | :--------------------------------------- |
| `id`         | Auto-generated record identifier         |
| `account_id` | Account/tenant identifier (auto-set)     |
| `created_at` | Record creation timestamp (auto-set)     |
| `updated_at` | Record update timestamp (auto-set)       |
| `created_by` | User ID who created the record (auto-set)|
| `updated_by` | User ID who last updated the record      |

### System Field Behavior

- **Request Validation**: Any attempt to include system fields in a request body will result in a 422 error
- **Response Filtering**: System fields are always included in responses regardless of field filtering
- **Automatic Setting**: These fields are automatically set by the system during create/update operations

### Error Example

```json
// Request
POST /api/v1/posts
{
  "id": "custom_id",  // Error: cannot write system field
  "title": "My Post"
}

// Response (422)
{
  "error": "Field access denied",
  "message": "Cannot create system fields via API: id",
  "unauthorized_fields": ["id"],
  "field_type": "system"
}
```

---

## Field-Level Access Control

Field-level access control allows you to restrict which fields users can read or write.

### Allowed Fields

Each permission rule can specify allowed fields:

```json
{
  "operation": "read",
  "rule": "true",
  "fields": ["id", "title", "status"]  // Only these fields
}
```

### Wildcard Fields

Use `*` to allow all fields (except system fields, which are always read-only):

```json
{
  "operation": "read",
  "rule": "true",
  "fields": "*"  // All non-system fields
}
```

### Field Filtering Behavior

Field filtering is applied differently to requests and responses:

| Context    | System Fields | Behavior                                      |
| :--------- | :------------ | :-------------------------------------------- |
| **Request** | Excluded      | Only allowed fields can be written           |
| **Response** | Always Included | Allowed fields + system fields are returned |

### Example: Salary Restriction

**Role: `employee`**

```json
{
  "operation": "read",
  "rule": "user.id == record.user_id",
  "fields": ["id", "name", "department"]
}
```

**Role: `hr_manager`**

```json
{
  "operation": "read",
  "rule": "true",
  "fields": "*"
}
```

With this setup:
- Employees can only see their own basic info (no salary)
- HR managers can see all fields including salary
- System fields (id, created_at, etc.) are visible to both

---

## Permission Caching

SnackBase uses a high-performance permission cache to avoid repeated database queries.

### Cache Configuration

- **Default TTL**: 5 minutes (300 seconds)
- **Configurable**: Set via `SNACKBASE_PERMISSION_CACHE_TTL_SECONDS` environment variable
- **Thread-Safe**: Uses reentrant locks for concurrent access
- **Automatic Invalidation**: Cache is cleared when permissions change

### Cache Key Format

```
{user_id}:{collection}:{operation}
```

Example: `user_123:posts:read`

### Cache Invalidation

The cache is automatically invalidated when:

1. **Permission Created**: All entries for that collection are cleared
2. **Permission Deleted**: All entries for that collection are cleared
3. **Permission Updated**: All entries for that collection are cleared
4. **TTL Expiration**: Entries expire after the configured TTL

### Manual Cache Invalidation

You can manually invalidate cache entries:

```python
# Invalidate all permissions for a user
permission_cache.invalidate_user(user_id)

# Invalidate all permissions for a collection
permission_cache.invalidate_collection(collection_name)

# Clear entire cache
permission_cache.invalidate_all()
```

### Performance Impact

Without caching, every API request would require:
- Database query to fetch user's role
- Database query to fetch permissions
- Rule evaluation for each operation

With caching (after first request):
- Single in-memory lookup
- No database queries
- Sub-millisecond response time

---

## Authorization Middleware

The authorization middleware provides the core permission checking functions.

### check_collection_permission()

Main permission check function.

```python
async def check_collection_permission(
    auth_context: AuthorizationContext,
    collection: str,
    operation: str,
    session: AsyncSession,
    record: dict[str, Any] | None = None,
) -> tuple[bool, list[str] | str]:
    """Check if user has permission for collection operation.

    Returns:
        Tuple of (allowed: bool, fields: list[str] | "*")

    Raises:
        HTTPException: 403 if permission denied
    """
```

**Process:**
1. Check if user is superadmin (bypass all checks)
2. Check cache for existing permission result
3. Resolve permission via PermissionResolver
4. Cache the result
5. Raise 403 if denied, return (True, fields) if allowed

### validate_request_fields()

Validate request body fields against allowed fields.

```python
def validate_request_fields(
    data: dict[str, Any],
    allowed_fields: list[str] | str,
    operation: str,
) -> None:
    """Validate that request body only contains allowed fields.

    Raises:
        HTTPException: 422 if validation fails
    """
```

**Checks:**
1. No system fields in request body
2. All fields are in allowed list (if not wildcard)

### apply_field_filter()

Apply field-level filtering to data.

```python
def apply_field_filter(
    data: dict[str, Any],
    allowed_fields: list[str] | str,
    is_request: bool = False,
) -> dict[str, Any]:
    """Apply field-level filtering to data.

    Returns:
        Filtered data dictionary
    """
```

**Behavior:**
- **Request mode** (`is_request=True`): Only allowed fields (no system fields)
- **Response mode** (`is_request=False`): Allowed fields + system fields

---

## API Endpoints

SnackBase provides REST API endpoints for managing permissions.

### Create Permission

```http
POST /api/v1/permissions
```

**Request Body:**
```json
{
  "role_id": 123,
  "collection": "posts",
  "rules": {
    "create": {
      "rule": "user.role == 'admin'",
      "fields": ["title", "content"]
    },
    "read": {
      "rule": "true",
      "fields": "*"
    },
    "update": {
      "rule": "user.id == record.created_by",
      "fields": ["title", "content"]
    },
    "delete": {
      "rule": "user.role == 'admin'",
      "fields": "*"
    }
  }
}
```

**Response:** `201 Created`
```json
{
  "id": 456,
  "role_id": 123,
  "collection": "posts",
  "rules": { ... },
  "created_at": "2024-01-10T10:00:00Z",
  "updated_at": "2024-01-10T10:00:00Z"
}
```

**Note:** Automatically invalidates permission cache for the collection.

### List Permissions

```http
GET /api/v1/permissions
```

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": 456,
      "role_id": 123,
      "collection": "posts",
      "rules": { ... },
      "created_at": "2024-01-10T10:00:00Z",
      "updated_at": "2024-01-10T10:00:00Z"
    }
  ],
  "total": 1
}
```

### Get Permission

```http
GET /api/v1/permissions/{permission_id}
```

**Response:** `200 OK`
```json
{
  "id": 456,
  "role_id": 123,
  "collection": "posts",
  "rules": { ... },
  "created_at": "2024-01-10T10:00:00Z",
  "updated_at": "2024-01-10T10:00:00Z"
}
```

### Delete Permission

```http
DELETE /api/v1/permissions/{permission_id}
```

**Response:** `204 No Content`

**Note:** Automatically invalidates permission cache for the collection.

---

## Common Patterns

### 1. Public Read Access

Allow anyone to read records, but only admins to modify.

| Operation              | Rule                   |
| :--------------------- | :--------------------- |
| `read`                 | `true`                 |
| `create/update/delete` | `user.role == "admin"` |

### 2. Owner-Only Access

Users can only manage their own data.

| Operation             | Rule                                    |
| :-------------------- | :-------------------------------------- |
| `create`              | `true` (ID is auto-assigned to creator) |
| `read/update/delete`  | `user.id == record.created_by`          |
| **Alternative Macro** | `@is_creator()`                         |

### 3. Group-Based Access

Allow access if the user belongs to a specific group.

| Operation             | Rule                        |
| :-------------------- | :-------------------------- |
| `read`                | `"managers" in user.groups` |
| **Alternative Macro** | `@has_group("managers")`    |

### 4. Status-Based Workflow

Only allow updates if the record is in a specific state.

```python
# Allow update strictly if status is 'draft' OR user is admin
(record.status == 'draft' and user.id == record.created_by) or user.role == 'admin'
```

### 5. Multi-Tenant Isolation

**Note**: SnackBase enforces Account ID isolation automatically via `account_id` filtering. You generally do not need to write rules for account isolation unless you are doing cross-account operations (which are restricted by default).

### 6. Field-Level Restrictions

Restrict sensitive fields (like `salary`) to specific roles.

**Role: `employee`**

- **Operation**: `read`
- **Rule**: `user.id == record.user_id`
- **Allowed Fields**: `["id", "name", "department"]` (Exclude `salary`)

**Role: `hr_manager`**

- **Operation**: `read`
- **Rule**: `true`
- **Allowed Fields**: `*` (All fields)

### 7. Time-Based Access

Allow access only during business hours (e.g., 9 AM - 5 PM).

```python
@in_time_range(9, 17)
```

### 8. Hierarchical Access

Allow managers to access their department's data.

```python
# SQL Macro
@is_in_department(user.id, record.department_id)
```

---

## Best Practices

### 1. Deny by Default

If no rule is defined, access is denied. Only define allow rules.

### 2. Use Macros for Reusability

For complex logic repeated across collections, wrap it in a SQL Macro.

### 3. Keep Rules Simple

Complex rules impact performance. Break complex logic into SQL Macros if needed.

### 4. Always Use Field Filtering

Always use field limiting for sensitive data sets. Don't rely solely on UI hiding.

### 5. Test Your Rules

Use the admin UI's rule tester or create test records to verify your rules.

Remember:
- `create` rules validate against the _incoming data_
- `read`, `update`, `delete` rules validate against the _existing record_

### 6. Leverage Caching

Permission results are cached for 5 minutes. Changes take effect within this window.

### 7. Monitor Cache Size

Check cache size in production to ensure it's not growing unbounded.

### 8. Use Wildcards Carefully

Wildcard permissions (`*` collection) apply to ALL collections. Use sparingly.

---

## Troubleshooting

### Permission Denied Errors

If you're getting unexpected permission denied errors:

1. **Check Superadmin Status**: Verify the user's `account_id` is not the system account
2. **Check Cache**: Wait for cache to expire (5 minutes) or manually invalidate
3. **Verify Rule Syntax**: Use the rule tester to validate syntax
4. **Check Field Access**: Ensure fields aren't restricted by field-level access
5. **Review System Fields**: Ensure you're not trying to write system fields

### Cache Issues

If permissions aren't taking effect:

1. **Wait for TTL**: Default is 5 minutes
2. **Manual Invalidation**: Use the API to trigger cache invalidation
3. **Restart Server**: Clears all in-memory caches

### Performance Issues

If permission checks are slow:

1. **Check Cache Hit Rate**: Ensure cache is being utilized
2. **Simplify Rules**: Complex rules take longer to evaluate
3. **Use SQL Macros**: Offload complex logic to SQL
4. **Database Indexing**: Ensure proper indexes on permission tables

### Testing Permissions

Use these approaches to test permissions:

1. **Admin UI**: Use the built-in rule tester
2. **API Testing**: Use tools like curl or Postman
3. **Integration Tests**: Write automated tests for permission scenarios
4. **Debug Logging**: Enable debug logging to trace permission resolution

---

## Security Considerations

### SQL Injection Prevention

- SQL macros use parameter binding
- Never interpolate user input directly into SQL queries
- Use named parameters with `:param_name` syntax

### Time-Based Attacks

- Permission cache has consistent lookup times
- No information leakage via timing

### Information Disclosure

- Error messages don't reveal sensitive information
- Permission denied errors are generic
- System field errors clearly indicate the issue

### Audit Logging

All permission checks are logged at appropriate levels:
- `DEBUG`: Successful checks
- `WARNING`: Denied access
- `ERROR`: Failed permission resolution

---

## Summary

SnackBase permissions provide:

- **Fine-grained control**: Operation, record-level, and field-level access
- **High performance**: 5-minute TTL cache with automatic invalidation
- **Flexibility**: Expression language + SQL macros for custom logic
- **Security**: System field protection, SQL injection prevention, audit logging
- **Developer-friendly**: Simple syntax, built-in macros, comprehensive API

For more information on related topics:
- See [docs/macros.md](macros.md) for detailed macro documentation
- See [docs/authentication.md](authentication.md) for user authentication
- See [docs/api-examples.md](api-examples.md) for API usage examples
