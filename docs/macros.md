# Macros Guide

Macros are reusable logic blocks that can be used in Permission Rules. They allow you to encapsulate complex logic, SQL queries, and common patterns into simple function calls like `@has_role("admin")` or `@is_project_member(record.project_id)`.

Macros come in two flavors:

1.  **Built-in Macros**: Hardcoded helpers provided by SnackBase.
2.  **SQL Macros**: Custom SQL queries defined by administrators.

**Important**: Macros are **global** - they are shared across all accounts in the system. Only superadmins can create, update, and delete macros.

---

## Built-in Macros

SnackBase provides several optimized macros for common scenarios.

### `@has_group(group_name: str)`

Checks if the current user is a member of the specified group.

- **Example**: `@has_group("managers")`
- **Returns**: `true` if the user is a member of the group, `false` otherwise.

### `@has_role(role_name: str)`

Checks if the current user has the specified role.

- **Example**: `@has_role("admin")`
- **Returns**: `true` if the user has the role, `false` otherwise.

### `@owns_record()`

Checks if the current user ID matches the `owner_id` field on the record.

- **Example**: `@owns_record()`
- **Returns**: `true` if `user.id == record.owner_id`, `false` otherwise.
- **Note**: The field checked is **hardcoded to `owner_id`** and cannot be configured to check a different field.

### `@is_creator()`

Alias for `@owns_record()`. Checks if the current user ID matches the `owner_id` field on the record.

- **Example**: `@is_creator()`
- **Returns**: `true` if `user.id == record.owner_id`, `false` otherwise.

### `@has_permission(operation: str, collection: str)`

Checks if the user has permission to perform another operation. Useful for chaining permissions or creating dependent access rules.

- **Example**: `@has_permission("read", "users")`
- **Returns**: `true` if the user is allowed to perform the specified operation on the collection, `false` otherwise.

### `@in_time_range(start_hour: int, end_hour: int)`

Checks if the current server time is within the specified hour range (24-hour format).

- **Example**: `@in_time_range(9, 17)` (9 AM to 5 PM)
- **Returns**: `true` if current hour is >= start_hour and < end_hour, `false` otherwise.

---

## SQL Macros

SQL Macros allow you to define custom logic using raw SQL queries. This is powerful for checking relationships across tables.

### Creating a SQL Macro

To create a macro, use the Macros API (accessible via Admin UI or API). Only superadmins can create macros.

**Example Scenario**: Allow access if the user is a "member" of the "project" associated with the "task" record.

1.  **Name**: `is_project_member`
2.  **Parameters**: `["project_id"]`
3.  **SQL Query**:
    ```sql
    SELECT 1 FROM project_members
    WHERE project_id = :project_id
    AND user_id = :user_id
    AND account_id = :account_id
    AND role = 'member'
    LIMIT 1
    ```

**Important**: Parameters like `:user_id` and `:account_id` must be explicitly included in your query's WHERE clause. They are available in the execution context but are not automatically injected - you must reference them in your SQL query.

### Using SQL Macros

Once created, use it in your permission rules like a function:

```python
@is_project_member(record.project_id)
```

The macro will execute with the provided parameter (in this case, `record.project_id`) along with `user_id` and `account_id` from the request context.

---

## Security Features & Constraints

SQL Macros include several security features to prevent abuse and protect your data:

### Query Validation

- **SELECT Only**: Macros must start with `SELECT`. Any attempt to use other SQL commands (INSERT, UPDATE, DELETE, etc.) will be rejected.
- **Forbidden Keywords**: The following keywords are blocked entirely:
  - `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`
  - `GRANT`, `REVOKE`
  - `CREATE`, `ALTER TABLE`, `DROP TABLE`
- **Parameter Binding**: All parameters use prepared statement binding to prevent SQL injection attacks.

### Execution Constraints

- **Timeout**: All macros have a **5-second execution timeout**. Queries exceeding this limit will return `false`.
- **Error Handling**: Any error during macro execution (syntax errors, constraint violations, etc.) will return `false` rather than exposing database details.
- **Read-Only Execution**: Macros execute within a transaction context designed for read operations. While it's technically possible to execute subqueries that reference other tables, the system validates against data modification commands.

### Deletion Safety

When attempting to delete a macro, the system checks if the macro is currently in use by any permissions. If the macro is referenced, the deletion will be rejected with a list of dependent permissions to prevent breaking access control.

---

## API Endpoints

The following endpoints are available for macro management:

### List All Macros
```
GET /api/v1/macros
```
- **Access**: All authenticated users
- **Returns**: List of all macros with their parameters and descriptions
- **Use Case**: View available macros for use in permission rules

### Get Macro by ID
```
GET /api/v1/macros/{id}
```
- **Access**: All authenticated users
- **Returns**: Details of a specific macro
- **Use Case**: Retrieve macro configuration before using in permissions

### Create Macro
```
POST /api/v1/macros
```
- **Access**: Superadmin only
- **Body**:
  ```json
  {
    "name": "is_active_subscriber",
    "description": "Checks if user has an active subscription",
    "parameters": [],
    "sql_query": "SELECT 1 FROM subscriptions WHERE user_id = :user_id AND status = 'active' AND expires_at > NOW() LIMIT 1"
  }
  ```
- **Validation**:
  - Name must be a valid Python identifier (letters, numbers, underscores, cannot start with a number)
  - Name must be unique across all macros
  - SQL query must start with SELECT
  - SQL query cannot contain forbidden keywords

### Update Macro
```
PUT /api/v1/macros/{id}
```
- **Access**: Superadmin only
- **Body**: Same as create
- **Note**: Updating a macro affects all permissions that use it immediately

### Test Macro
```
POST /api/v1/macros/{id}/test
```
- **Access**: Superadmin only
- **Body**:
  ```json
  {
    "parameters": {
      "project_id": "project_123"
    }
  }
  ```
- **Behavior**: Executes the macro with test parameters using transaction rollback to prevent side effects
- **Returns**: Result of the macro execution (true/false) and any error information
- **Use Case**: Validate macro logic before deploying to production

### Delete Macro
```
DELETE /api/v1/macros/{id}
```
- **Access**: Superadmin only
- **Safety Check**: Fails if the macro is used in any permissions
- **Returns**: Success confirmation or error with list of dependent permissions

---

## Macro Development Guide

### Best Practices

1.  **Use SELECT 1**: Always use `SELECT 1` or `SELECT true`. The engine checks if _any_ row is returned, not the actual value.
2.  **Add LIMIT 1**: Always include `LIMIT 1` for performance. You only need to know if a match exists, not how many matches.
3.  **Index Your Columns**: Ensure columns used in `WHERE` clauses (like `user_id`, `project_id`, `account_id`) are properly indexed for fast lookups.
4.  **Include Account Isolation**: Always include `account_id = :account_id` in WHERE clauses to maintain multi-tenancy isolation.
5.  **Keep It Simple**: Use SQL macros for data lookup only. Keep business logic in the Rule Expression when possible.
6.  **Test Before Deploying**: Use the `/test` endpoint to validate macro logic with sample data before using in production permissions.
7.  **Document Dependencies**: If your macro references specific tables or columns, document this in the description field.

### Naming Conventions

- Use descriptive names that indicate what the macro checks
- Prefix with `is_`, `has_`, `can_`, or similar verbs
- Examples:
  - `is_project_member` - Checks membership in a project
  - `has_active_subscription` - Checks subscription status
  - `can_access_resource` - Checks resource access rights

### Common Patterns

**Check relationship existence**:
```sql
SELECT 1 FROM table_relationships
WHERE parent_id = :parent_id
AND user_id = :user_id
AND account_id = :account_id
LIMIT 1
```

**Check status with date validation**:
```sql
SELECT 1 FROM subscriptions
WHERE user_id = :user_id
AND account_id = :account_id
AND status = 'active'
AND (expires_at IS NULL OR expires_at > NOW())
LIMIT 1
```

**Check multiple conditions**:
```sql
SELECT 1 FROM access_grants
WHERE resource_id = :resource_id
AND user_id = :user_id
AND account_id = :account_id
AND role IN ['editor', 'owner']
AND is_active = true
LIMIT 1
```

### Example API Payloads

**Create Macro**:

```json
{
  "name": "is_active_subscriber",
  "description": "Checks if user has an active subscription that hasn't expired",
  "parameters": [],
  "sql_query": "SELECT 1 FROM subscriptions WHERE user_id = :user_id AND account_id = :account_id AND status = 'active' AND (expires_at IS NULL OR expires_at > NOW()) LIMIT 1"
}
```

**Usage in Rule**:

```python
@is_active_subscriber()
```

**Create Macro with Parameters**:

```json
{
  "name": "has_project_access",
  "description": "Checks if user has access to a specific project",
  "parameters": ["project_id"],
  "sql_query": "SELECT 1 FROM project_members WHERE project_id = :project_id AND user_id = :user_id AND account_id = :account_id LIMIT 1"
}
```

**Usage in Rule**:

```python
@has_project_access(record.project_id)
```
