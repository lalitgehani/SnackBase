# Permission Rule Syntax & Patterns

SnackBase uses a powerful expression language for defining granular access control rules. This guide covers the syntax, available variables, operations, and common patterns for securing your data.

## Overview

Permissions are defined per **Role** and **Collection**. Each permission rule consists of:

1.  **Operation**: `create`, `read`, `update`, `delete`
2.  **Rule Expression**: A logic string that evaluates to `true` (allow) or `false` (deny)
3.  **Allowed Fields**: A list of fields (or `*`) that are accessible

### Resolution Order

SnackBase resolves permissions in the following order:

1.  **User-Specific Rules**: Rules directly assigned to a user ID take precedence.
2.  **Role-Based Rules**: Rules assigned to the user's role.
3.  **Wildcard Collection Rules**: Rules for the `*` collection apply if no specific collection rule matches.

If multiple permissions match (e.g., multiple roles or role + wildcard), they are combined with **OR** logic. If any rule evaluates to `true`, access is granted.

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

**Note**: SnackBase enforces Account ID isolation automatically (WHERE account_id = X). You generally do not need to write rules for account isolation unless you are doing cross-account operations (which are restricted by default).

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

---

## Testing Rules

You can use the built-in **Macro Tester** or create a test record to verify your rules.
When testing, remember:

- `create` rules valid against the _incoming data_.
- `read`, `update`, `delete` rules validate against the _existing record_.

## Best Practices

1.  **Deny by Default**: If no rule is defined, access is denied. You only need to define allow rules.
2.  **Use Macros**: For complex logic repeated across collections, wrap it in a Macro.
3.  **Keep it Simple**: Complex rules impact performance.
4.  **Field Filtering**: Always use field limiting for sensitive data sets, don't rely solely on UI hiding.
