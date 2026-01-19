# SQL Macros (V2)

SQL Macros in SnackBase allow you to define reusable permission logic via text substitution or custom SQL subqueries. They are expanded before your rule expressions are compiled to SQL, making them highly efficient and compatible with Row-Level Security (RLS).

---

## 1. Built-in Macros

SnackBase provides several optimized macros for common scenarios. These act as **text fragments** that are substituted into your rule.

### `@owns_record(field = "created_by")`

Checks if the current user ID matches a field on the record.

- **Expands to**: `[field] = @request.auth.id`
- **Default Use**: `@owns_record()` -> `created_by = @request.auth.id`
- **Custom Use**: `@owns_record("owner_id")` -> `owner_id = @request.auth.id`

### `@is_creator()`

An alias for `@owns_record()`.

- **Expands to**: `created_by = @request.auth.id`

### `@is_public()`

Check if a record is marked as public.

- **Expands to**: `public = true`

### `@has_role(role_name)`

Check if the current user has a specific role.

- **Example**: `@has_role("admin")`
- **Expands to**: `@request.auth.role = "admin"`

---

## 2. Custom SQL Macros (Subqueries)

Custom macros allow you to define complex relationship checks using raw SQL. These are stored in the database and executed as **SQL Subqueries**.

### Creating a Custom Macro

When creating a macro, you define a SQL template. You can use positional parameters like `$1`, `$2` which will be replaced by arguments during rule execution.

**Example: `@is_project_member(project_id)`**

- **Name**: `is_project_member`
- **SQL Query**:
  ```sql
  SELECT count(*) > 0 FROM project_members
  WHERE project_id = $1 AND user_id = @request.auth.id
  ```

### Using in Rules

Macros can be combined with standard logic:

```python
# Allow access if user is admin OR they own the record
@has_role("admin") || @owns_record()

# Allow access if user is a member of the project
@is_project_member(project_id)
```

---

## API Management

### List Macros

`GET /api/v1/macros`

### Create Macro

`POST /api/v1/macros`

**Payload:**

```json
{
  "name": "has_active_subscription",
  "description": "Checks if user has a paid plan",
  "sql_query": "SELECT count(*) > 0 FROM subscriptions WHERE user_id = @request.auth.id AND status = 'active'"
}
```

---

## Best Practices

1.  **Return Boolean**: Custom SQL macros must return a boolean (usually `count(*) > 0` or `EXISTS(...)`).
2.  **Performance**: Macros are executed as subqueries. Ensure the underlying tables (e.g., `project_members.user_id`) are indexed.
3.  **Naming**: Use descriptive names like `can_edit_document` or `is_account_owner`.
4.  **Parameter Safety**: Always use `$1`, `$2` for arguments; SnackBase handles the substitution safely.
5.  **Multi-tenancy**: Note that `@request.auth.id` automatically respects isolation when combined with RLS.
