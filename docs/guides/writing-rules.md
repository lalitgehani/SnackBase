# Writing Permission Rules (V2)

This guide explains how to write and use permission rules in SnackBase's new database-centric rule engine.

---

## Overview

In SnackBase V2, rules are **SQL-native expressions** defined on a per-collection basis. Instead of being evaluated in Python after fetching data, these rules are compiled directly into SQL `WHERE` clauses, ensuring high performance and native row-level security.

### Core Philosophy

1.  **Rules ARE Filters**: A rule like `status = "published"` is literally added to the database query.
2.  **5 Operations**: Rules are distinct for `list`, `view`, `create`, `update`, and `delete`.
3.  **Context-Aware**: Access `@request.auth.*` for user info and `@request.data.*` for incoming data.

---

## Syntax Guide

### Basic Expressions

```python
# Direct field access
status = "active"
priority >= 5
public = true

# String matching
title ~ "%draft%"      # LIKE '%draft%'
email ~ "%.edu"        # Case-insensitive suffix match

# List-like membership (handled via SQL IN)
category = "news" || category = "updates"
```

### Logical Operators

| Operator | SQL Equivalent | Description                   |
| :------- | :------------- | :---------------------------- | ---- | ------------------------------------ |
| `&&`     | `AND`          | Both conditions must be true. |
| `        |                | `                             | `OR` | At least one condition must be true. |
| `!`      | `NOT`          | Inverts the condition.        |

**Grouping**: Use parentheses for complex logic:
`(status = "active" || @request.auth.role = "admin") && !archived`

---

## Evaluation Context

### Auth Context (`@request.auth.*`)

Accessible in all rule types.

| Variable                   | Description                   |
| :------------------------- | :---------------------------- |
| `@request.auth.id`         | Current user's unique ID.     |
| `@request.auth.email`      | Current user's email address. |
| `@request.auth.role`       | Current user's role name.     |
| `@request.auth.account_id` | Current account/tenant ID.    |

### Data Context (`@request.data.*`)

Only accessible in `create` and `update` rules. Refers to the incoming request body.

```python
# For create: Ensure the user sets themselves as the creator.
@request.data.created_by = @request.auth.id

# For update: Prevent changing the status to "locked".
@request.data.status != "locked"
```

### Record Context (Direct Field Names)

Accessible in `list`, `view`, `update`, and `delete` rules. Refers to the existing record in the database.

```python
# Record ownership check
created_by = @request.auth.id
```

---

## Common Patterns

### 1. Simple Ownership

`created_by = @request.auth.id`

### 2. Admin Override

`@request.auth.role = "admin" || created_by = @request.auth.id`

### 3. Public Listing, Private Editing

- **list_rule**: `status = "published"`
- **update_rule**: `created_by = @request.auth.id`

### 4. Tenant Isolation (Implicit)

SnackBase automatically injects `account_id = :auth_account_id` into all queries. You do **not** need to add this to your rules unless you are implementing custom cross-tenant logic.

### 5. Using Macros

`@owns_record() && status = "draft"`
_(Note: `@owns_record()` expands to `created_by = @request.auth.id`)_

---

## Testing Rules

You can test your rules directly in the **Admin UI > Collections > [Name] > Rules**.

1.  **Syntax Check**: The editor will highlight errors as you type.
2.  **Simulator**: Provide a sample Auth Context and Record context to see if the rule evaluates to "Allowed" or "Denied".

---

## Best Practices

1.  **Keep it Simple**: Rules are compiled to SQL. Extremely complex logic may impact query performance.
2.  **Use Parentheses**: Be explicit with operator precedence to avoid unexpected logic.
3.  **Leverage List vs View**: Use `list_rule` to hide rows from browsable lists and `view_rule` for stricter detail access.
4.  **Locked by Default**: Use `null` for sensitive internal collections to ensure only superadmins can access them.
