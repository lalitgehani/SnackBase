# Macros Guide

Macros are reusable logic blocks that can be used in Permission Rules. They allow you to encapsulate complex logic, SQL queries, and common patterns into simple function calls like `@is_admin()` or `@has_access("project_a")`.

Macros come in two flavors:

1.  **Built-in Macros**: Hardcoded helpers provided by SnackBase.
2.  **SQL Macros**: Custom SQL queries defined by you.

---

## Built-in Macros

SnackBase provides several optimized macros for common scenarios.

### `@has_group(group_name: str)`

Checks if the current user is a member of the specified group.

- **Example**: `@has_group("managers")`
- **Returns**: `true` if member, `false` otherwise.

### `@has_role(role_name: str)`

Checks if the current user has the specified role.

- **Example**: `@has_role("admin")`
- **Returns**: `true` if role matches.

### `@owns_record(field_name: str = "created_by")`

Checks if the current user ID matches a field on the record.

- **Example**: `@owns_record()` (defaults to checking `created_by`)
- **Example**: `@owns_record("owner_id")`
- **Returns**: `true` if `user.id == record[field_name]`.

### `@in_time_range(start_hour: int, end_hour: int)`

Checks if the current server time is within the specified hour range (24-hour format).

- **Example**: `@in_time_range(9, 17)` (9 AM to 5 PM)
- **Returns**: `true` if current hour is >= start and < end.

### `@has_permission(operation: str, collection: str)`

Checks if the user has permission to perform another operation. Useful for chaining permissions.

- **Example**: `@has_permission("read", "users")`
- **Returns**: `true` if the user is allowed to perform the operation.

---

## SQL Macros

SQL Macros allow you to define custom logic using raw SQL queries. This is powerful for checking relationships across tables.

### Creating a SQL Macro

To create a macro, use the Macros API (accessible via Admin UI or API).

**Example Scenario**: Allow access if the user is a "member" of the "project" associated with the "task" record.

1.  **Name**: `is_project_member`
2.  **Parameters**: `["project_id"]`
3.  **SQL Query**:
    ```sql
    SELECT 1 FROM project_members
    WHERE project_id = :project_id
    AND user_id = :user_id
    AND role = 'member'
    LIMIT 1
    ```

**Note**: `:user_id` and `:account_id` are automatically injected into the query context.

### Using SQL Macros

Once created, use it in your permission rules like a function:

```python
@is_project_member(record.project_id)
```

### Security & Performance

- **ReadOnly**: Macros are executed in a read-only transaction. You cannot modify data.
- **Timeouts**: Execution is capped at **5 seconds** by default.
- **Parameter Binding**: All parameters are safely bound to prevent SQL injection.
- **Caching**: Macro results are cached for the duration of the request.

---

## Macro Development Guide

### Best Practices

1.  **Select 1**: Always use `SELECT 1` or `SELECT true`. The engine checks if _any_ row is returned.
2.  **Limit 1**: Always add `LIMIT 1` for performance. You only need to know if a match exists.
3.  **Indexes**: Ensure columns used in `WHERE` clauses (like `user_id`, `project_id`) are indexed.
4.  **No Logic in SQL**: Keep business logic in the Rule Expression if possible, use SQL only for data lookup.

### Managing Macros via API

- **List Macros**: `GET /api/v1/macros`
- **Create Macro**: `POST /api/v1/macros`
- **Test Macro**: `POST /api/v1/macros/{id}/test`
- **Delete Macro**: `DELETE /api/v1/macros/{id}` (Checks for usage before deletion)

### Example API Payload

**Create Macro**:

```json
{
  "name": "is_active_subscriber",
  "description": "Checks if user has an active subscription",
  "parameters": [],
  "sql_query": "SELECT 1 FROM subscriptions WHERE user_id = :user_id AND status = 'active' AND expires_at > NOW()"
}
```

**Usage in Rule**:

```python
@is_active_subscriber()
```
