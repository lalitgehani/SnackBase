# Security Model

SnackBase provides a comprehensive security model with role-based access control, field-level permissions, and a powerful rule engine. This guide explains the security architecture, authorization flows, and best practices.

---

## Table of Contents

- [Overview](#overview)
- [Security Architecture](#security-architecture)
- [Authentication vs Authorization](#authentication-vs-authorization)
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
- [Permission System](#permission-system)
- [Rule Engine](#rule-engine)
- [Field-Level Security](#field-level-security)
- [Account Isolation](#account-isolation)
- [Security Best Practices](#security-best-practices)

---

## Overview

SnackBase security operates on **multiple layers** to ensure data protection:

| Layer | Purpose | Mechanism |
|-------|---------|-----------|
| **Authentication** | Verify user identity | JWT tokens, Argon2id password hashing |
| **Account Isolation** | Separate tenant data | Row-level filtering via `account_id` |
| **Authorization** | Control user actions | RBAC + Permission system |
| **Field-Level Security** | Hide sensitive data | Field-level access control |
| **Audit Logging** | Track all actions | Immutable audit logs (coming soon) |

> **Screenshot Placeholder 1**
>
> **Description**: A layered security diagram showing five concentric circles: Authentication (inner), Account Isolation, Authorization, Field-Level Security, and Audit Logging (outer).

---

## Security Architecture

### Request Security Flow

```
┌──────────────┐
│ Client       │
│ Request      │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│ 1. Authentication Middleware    │
│    - Verify JWT token           │
│    - Extract user & account      │
│    - Check token expiration      │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 2. Account Isolation Hook       │
│    - Inject account_id filter   │
│    - Enforce row-level security │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 3. Authorization Middleware     │
│    - Load user permissions      │
│    - Check collection access    │
│    - Evaluate operation rules   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 4. Field-Level Security         │
│    - Filter sensitive fields    │
│    - Apply field rules          │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ 5. Business Logic               │
│    - Execute operation          │
│    - Return filtered data       │
└─────────────────────────────────┘
```

> **Screenshot Placeholder 2**
>
> **Description**: A vertical flow diagram showing the request passing through five security layers before reaching business logic.

---

## Authentication vs Authorization

Understanding the distinction is critical:

| Aspect | Authentication | Authorization |
|--------|----------------|---------------|
| **Question** | Who are you? | What can you do? |
| **Mechanism** | JWT tokens, passwords | Roles, permissions, rules |
| **Timing** | Once per session | Every request |
| **Failure Result** | 401 Unauthorized | 403 Forbidden |

> **Screenshot Placeholder 3**
>
> **Description**: A comparison table showing authentication vs authorization with visual icons representing each concept.

### Example Scenario

```
Authentication (Who are you?):
├── User provides credentials
├── System verifies identity
└── Result: "You are alice@acme.com"

Authorization (What can you do?):
├── User requests DELETE /api/v1/posts/123
├── System checks permissions
├── User has "editor" role
├── Editor role does NOT have "delete" permission
└── Result: 403 Forbidden - "You cannot delete posts"
```

> **Screenshot Placeholder 4**
>
> **Description**: A split-screen example showing authentication (left) and authorization (right) with their respective questions and results.

---

## Role-Based Access Control (RBAC)

SnackBase uses **RBAC** as the foundation of authorization.

### RBAC Hierarchy

```
Account (AB1001)
│
├── Users
│   ├── alice@acme.com
│   ├── bob@acme.com
│   └── jane@acme.com
│
├── Roles
│   ├── admin
│   │   └── Permissions: All operations on all collections
│   ├── editor
│   │   └── Permissions: Create, Read, Update on posts only
│   └── viewer
│       └── Permissions: Read on posts only
│
└── Role Assignments
    ├── alice@acme.com → admin
    ├── bob@acme.com → editor
    └── jane@acme.com → viewer
```

> **Screenshot Placeholder 5**
>
> **Description**: A tree diagram showing the RBAC hierarchy with Account at top, branching to Users, Roles, and Role Assignments.

### Default Roles

| Role | Description | Typical Permissions |
|------|-------------|---------------------|
| **admin** | Full administrative access | All operations on all collections |
| **editor** | Content creator/manager | Create, Read, Update on specific collections |
| **viewer** | Read-only access | Read on specific collections |

> **Screenshot Placeholder 6**
>
> **Description**: A table showing default roles with their descriptions and typical permission sets.

### Custom Roles

You can create custom roles for any purpose:

```json
{
  "name": "moderator",
  "description": "Can moderate user-generated content",
  "permissions": [
    {
      "collection": "comments",
      "create": false,
      "read": true,
      "update": true,
      "delete": true
    },
    {
      "collection": "users",
      "create": false,
      "read": true,
      "update": false,
      "delete": false
    }
  ]
}
```

> **Screenshot Placeholder 7**
>
> **Description**: JSON showing a custom "moderator" role with specific permissions for comments and users collections.

---

## Permission System

Permissions define **what operations** a user can perform on **which collections**.

### Permission Matrix

For a role with permissions:

| Collection | Create | Read | Update | Delete |
|------------|--------|------|--------|--------|
| posts | ✅ | ✅ | ✅ | ❌ |
| comments | ✅ | ✅ | ✅ | ✅ |
| users | ❌ | ✅ | ❌ | ❌ |

> **Screenshot Placeholder 8**
>
> **Description**: A visual permission matrix grid showing checkboxes for Create, Read, Update, Delete permissions across multiple collections.

### Permission Structure

```json
{
  "id": "perm_abc123",
  "role_id": "role_editor",
  "collection": "posts",
  "create": true,
  "read": true,
  "update": true,
  "delete": false,
  "fields": ["title", "content", "status"],
  "rules": {
    "create": "@has_role('editor')",
    "update": "@owns_record() or @has_role('admin')"
  }
}
```

> **Screenshot Placeholder 9**
>
> **Description**: JSON showing a complete permission object with CRUD flags, field restrictions, and rule expressions.

### Wildcard Collections

Use `*` to grant permissions on **all collections**:

```json
{
  "role": "admin",
  "collection": "*",
  "create": true,
  "read": true,
  "update": true,
  "delete": true
}
```

This grants admin full access to ALL collections, including future ones.

> **Screenshot Placeholder 10**
>
> **Description**: A code example showing wildcard collection permission with a visual highlight of the asterisk.

### Permission Caching

Permissions are cached for **5 minutes** to improve performance:

```
┌──────────────────┐
│ First Request    │
│ Check permissions│
│ from database    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Cache for 5 min  │
│ Subsequent       │
│ requests use     │
│ cached perms     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ After 5 min or   │
│ permission change│
│ Cache invalidated│
└──────────────────┘
```

> **Screenshot Placeholder 11**
>
> **Description**: A timeline diagram showing permission caching with cache hit period and invalidation.

---

## Rule Engine

SnackBase includes a **powerful rule engine** for fine-grained access control.

### Rule Syntax

Rules use a custom DSL (Domain Specific Language):

```python
# Simple comparisons
user.id == "user_abc123"
user.email == "admin@example.com"

# Role checks
@has_role("admin")
@has_any_role(["admin", "moderator"])

# Record ownership
@owns_record()

# Field comparisons
status in ["draft", "published"]
priority >= 3

# Logical operators
@has_role("admin") or @owns_record()
@has_role("editor") and status == "draft"
not status == "archived"

# Complex expressions
(@has_role("admin") or @owns_record()) and not status == "locked"
```

> **Screenshot Placeholder 12**
>
> **Description**: A code example showing various rule syntax patterns with comments explaining each.

### Built-in Functions

| Function | Description | Example |
|----------|-------------|---------|
| `@has_role(role)` | User has specific role | `@has_role("admin")` |
| `@has_any_role([roles])` | User has any of these roles | `@has_any_role(["admin", "moderator"])` |
| `@owns_record()` | User created this record | `@owns_record()` |
| `@is_superadmin()` | User is superadmin | `@is_superadmin()` |

> **Screenshot Placeholder 13**
>
> **Description**: A table showing all built-in rule functions with their descriptions and usage examples.

### Rule Evaluation Context

Rules have access to:

| Variable | Description | Example |
|----------|-------------|---------|
| `user` | Current user object | `user.id`, `user.email` |
| `record` | Record being accessed | `record.created_by`, `record.status` |
| `context` | Request context | `context.account_id` |

> **Screenshot Placeholder 14**
>
> **Description:** A table showing rule evaluation context variables with their available properties.

### Permission Rules Example

```json
{
  "collection": "posts",
  "update": true,
  "rules": {
    "update": "(@owns_record() and status in ['draft', 'pending']) or @has_role('admin')"
  }
}
```

**Translation**: Users can update posts if:
- They created the post AND status is draft/pending, OR
- They have admin role

> **Screenshot Placeholder 15**
>
> **Description**: A visual decision tree diagram showing the rule logic with branches for ownership check and admin check.

---

## Field-Level Security

SnackBase supports **field-level access control** to hide sensitive data.

### Field Visibility

Restrict which fields a role can see:

```json
{
  "role": "viewer",
  "collection": "users",
  "read": true,
  "fields": ["name", "email"],
  "excluded_fields": ["phone", "ssn", "salary"]
}
```

Users with this role will receive:

```json
// Response (excluded fields filtered out)
{
  "id": "user_abc123",
  "name": "Alice Johnson",
  "email": "alice@example.com"
  // phone, ssn, salary NOT included
}
```

> **Screenshot Placeholder 16**
>
> **Description:** A side-by-side comparison showing full user record (left) vs filtered response (right) with sensitive fields redacted.

### Field-Level Rules

Apply rules to specific fields:

```json
{
  "collection": "users",
  "field_rules": {
    "salary": {
      "read": "@has_role('admin') or @owns_record()",
      "write": "@has_role('hr') or @is_superadmin()"
    },
    "email": {
      "read": "true",
      "write": "@has_role('admin')"
    }
  }
}
```

> **Screenshot Placeholder 17**
>
> **Description:** A code example showing field-level rules with different permissions for salary and email fields.

---

## Account Isolation

Account isolation is the **foundation of SnackBase security**.

### Multi-Tenant Isolation

All data is automatically isolated by `account_id`:

```sql
-- User from AB1001 requests posts
SELECT * FROM posts WHERE account_id = 'AB1001';

-- User from XY2048 requests posts
SELECT * FROM posts WHERE account_id = 'XY2048';
```

Users cannot see or access data from other accounts.

> **Screenshot Placeholder 18**
>
> **Description:** A database diagram showing two account partitions (AB1001, XY2048) with data separated, and a query showing results from one partition only.

### Enforcement Layers

Account isolation is enforced at **multiple layers**:

| Layer | Mechanism | Example |
|-------|-----------|---------|
| **Database** | `account_id` column in WHERE clause | `WHERE account_id = ?` |
| **Repository** | Automatic filtering in queries | `posts.find_all(context)` |
| **API Middleware** | Validates account in token | Token contains account_id |
| **Hooks** | Built-in account_isolation_hook | Cannot be disabled |

> **Screenshot Placeholder 19**
>
> **Description:** A layered diagram showing account isolation enforcement at Database, Repository, API Middleware, and Hooks layers.

### Cross-Account Access Prevention

Attempting to access another account's data:

```bash
# User from AB1001 tries to access XY2048 data
GET /api/v1/posts?account_id=XY2048

# Result: 403 Forbidden
# The account_id filter is overridden and reset to AB1001
```

The system **ignores** malicious `account_id` parameters.

> **Screenshot Placeholder 20**
>
> **Description:** A sequence diagram showing a malicious cross-account request being blocked and the account_id being reset to the user's actual account.

---

## Security Best Practices

### 1. Principle of Least Privilege

Grant minimum required permissions:

```json
// ❌ Too permissive
{
  "role": "viewer",
  "collection": "*",
  "delete": true  // Viewers shouldn't delete!
}

// ✅ Correct
{
  "role": "viewer",
  "collection": "posts",
  "read": true,
  "create": false,
  "update": false,
  "delete": false
}
```

> **Screenshot Placeholder 21**
>
> **Description:** A code comparison showing overly permissive (bad) vs minimal required permissions (good) with visual indicators.

### 2. Use Rules for Fine-Grained Control

Leverage the rule engine for complex scenarios:

```json
{
  "rules": {
    "update": "@owns_record() or @has_role('admin')",
    "delete": "@has_role('admin') and not record.status == 'locked'"
  }
}
```

> **Screenshot Placeholder 22**
>
> **Description:** Code example showing best practice rule usage with ownership checks and admin role checks.

### 3. Implement Field-Level Security

Hide sensitive fields by default:

```json
{
  "collection": "users",
  "excluded_fields": ["password_hash", "ssn", "salary"]
}
```

> **Screenshot Placeholder 23**
>
> **Description:** Code example showing field exclusion for sensitive user data.

### 4. Regular Permission Audits

Periodically review and update permissions:

- Remove unused roles
- Tighten overly permissive rules
- Document permission rationale
- Use audit logs (when available) to track access

> **Screenshot Placeholder 24**
>
> **Description:** A checklist or flowchart showing permission audit process with steps: Review Roles → Analyze Permissions → Tighten Rules → Document Changes.

### 5. Use Wildcards Carefully

Wildcard permissions (`*`) are powerful but dangerous:

```json
// ⚠️ Use with caution
{
  "collection": "*",
  "delete": true  // Can delete from ALL collections!
}

// ✅ Prefer explicit collections
{
  "collection": "posts",
  "delete": true
}
```

> **Screenshot Placeholder 25**
>
> **Description:** Code comparison showing risky wildcard usage vs safer explicit collection permission.

### 6. Test Permission Changes

Always test permission changes in development:

```python
def test_editor_cannot_delete_posts():
    editor_user = create_user(role="editor")
    client = login_as(editor_user)

    response = client.delete("/api/v1/posts/123")

    assert response.status_code == 403
```

> **Screenshot Placeholder 26**
>
> **Description:** A code example showing a test case for verifying permission restrictions.

### 7. Monitor and Alert

Monitor for suspicious activity:
- Repeated failed authorization attempts
- Unusual access patterns
- Permission escalation attempts
- Cross-account access attempts

> **Screenshot Placeholder 27**
>
> **Description:** A dashboard mockup showing security monitoring with metrics for failed attempts, unusual patterns, and alerts.

---

## Common Security Scenarios

### Scenario 1: User Can Only Edit Their Own Posts

```json
{
  "role": "author",
  "collection": "posts",
  "create": true,
  "read": true,
  "update": true,
  "delete": true,
  "rules": {
    "update": "@owns_record()",
    "delete": "@owns_record() and not status == 'published'"
  }
}
```

> **Screenshot Placeholder 28**
>
> **Description:** A use case diagram showing the author role workflow with permission boundaries.

### Scenario 2: Moderators Can Edit All Comments

```json
{
  "role": "moderator",
  "collection": "comments",
  "create": false,
  "read": true,
  "update": true,
  "delete": true,
  "field_rules": {
    "author_ip": {
      "read": "@has_role('admin')"
    }
  }
}
```

> **Screenshot Placeholder 29**
>
> **Description:** A use case diagram showing moderator permissions with IP address hidden from non-admins.

### Scenario 3: Public Read, Private Write

```json
{
  "role": "anonymous",
  "collection": "posts",
  "read": true,
  "create": false,
  "update": false,
  "delete": false,
  "excluded_fields": ["draft_notes", "internal_status"]
}
```

> **Screenshot Placeholder 30**
>
> **Description:** A use case diagram showing public access with restricted write operations and hidden internal fields.

---

## Summary

| Concept | Key Takeaway |
|---------|--------------|
| **Security Layers** | Authentication → Account Isolation → Authorization → Field-Level Security → Audit |
| **Authentication vs Authorization** | Authentication = Who are you? Authorization = What can you do? |
| **RBAC** | Users → Roles → Permissions → Collections |
| **Permission System** | CRUD permissions per collection, wildcard support, 5-minute cache |
| **Rule Engine** | Custom DSL for fine-grained control with built-in functions |
| **Field-Level Security** | Hide sensitive fields, field-specific rules |
| **Account Isolation** | Automatic via account_id, enforced at multiple layers |
| **Best Practices** | Least privilege, use rules, hide sensitive data, audit permissions |

---

## Related Documentation

- [Authentication Model](./authentication.md) - Authentication flows and token management
- [Multi-Tenancy Model](./multi-tenancy.md) - Account isolation architecture
- [Permissions](../permissions.md) - Permission rule syntax reference
- [Hooks System](../hooks.md) - Extending security with custom hooks

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
