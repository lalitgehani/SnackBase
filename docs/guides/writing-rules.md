# Writing Permission Rules

This guide explains how to write and use permission rules in SnackBase's rule engine for fine-grained access control.

---

## Table of Contents

- [Overview](#overview)
- [Rule Syntax](#rule-syntax)
- [Built-in Functions](#built-in-functions)
- [Evaluation Context](#evaluation-context)
- [Rule Examples](#rule-examples)
- [Advanced Patterns](#advanced-patterns)
- [Testing Rules](#testing-rules)
- [Best Practices](#best-practices)

---

## Overview

SnackBase includes a **powerful rule engine** with a custom DSL (Domain Specific Language) for expressing complex permission logic.

### What Are Rules?

Rules are **boolean expressions** that determine whether a permission grant allows an operation.

```
Permission = CRUD flags (create, read, update, delete)
            + Rules (additional conditions)

Example: "Users can update posts if they created them"
```

> **Screenshot Placeholder 1**
>
> **Description**: A visual diagram showing permission = CRUD flags + Rules, with an example.

### When to Use Rules

Use rules when you need:

| Scenario | Example |
|----------|---------|
| **Record ownership** | Users can only edit their own posts |
| **Status-based access** | Published posts can only be edited by admins |
| **Time-based access** | Records can only be modified within 24 hours |
| **Field-value conditions** | High-priority tickets require manager approval |
| **Complex logic** | Combination of role, ownership, and status |

> **Screenshot Placeholder 2**
>
> **Description**: A table showing rule use cases with examples for each scenario.

---

## Rule Syntax

### Basic Expressions

```python
# Field comparisons
user.id == "user_abc123"
user.email == "admin@example.com"
record.status == "published"

# Numeric comparisons
record.views > 1000
record.priority >= 3
record.quantity <= 50

# List membership
status in ["draft", "published", "archived"]
record.category in ["news", "updates"]

# Negation
not record.status == "archived"
record.status != "archived"
```

> **Screenshot Placeholder 3**
>
> **Description**: Code showing various basic expression types with annotations.

### Logical Operators

```python
# AND (both conditions must be true)
@has_role("editor") and @owns_record()
status == "draft" and priority < 5

# OR (at least one condition must be true)
@has_role("admin") or @owns_record()
status in ["draft", "pending"] or @has_role("moderator")

# NOT (inverts condition)
not status == "archived"
not @has_role("banned")

# Grouping with parentheses
(@has_role("admin") or @owns_record()) and not status == "locked"
```

> **Screenshot Placeholder 4**
>
> **Description**: Code showing logical operators (AND, OR, NOT) with grouping examples.

### Operator Precedence

Operators are evaluated in this order (highest to lowest):

1. `()` - Parentheses
2. `not` - Negation
3. `==`, `!=`, `>`, `>=`, `<`, `<=`, `in` - Comparisons
4. `and` - Logical AND
5. `or` - Logical OR

```python
# Example: How this is evaluated
@has_role("admin") or @owns_record() and status == "draft"

# Step 1: AND first (higher precedence)
(@has_role("admin") or (@owns_record() and status == "draft"))

# Use parentheses to change order
(@has_role("admin") or @owns_record()) and status == "draft"
```

> **Screenshot Placeholder 5**
>
> **Description**: A diagram showing operator precedence with step-by-step evaluation.

---

## Built-in Functions

### Role Functions

| Function | Description | Example |
|----------|-------------|---------|
| `@has_role(role)` | User has specific role | `@has_role("admin")` |
| `@has_any_role([roles])` | User has any of these roles | `@has_any_role(["admin", "moderator"])` |
| `@has_all_roles([roles])` | User has all of these roles | `@has_all_roles(["editor", "publisher"])` |

> **Screenshot Placeholder 6**
>
> **Description**: A table showing role-related functions with descriptions and examples.

### Ownership Functions

| Function | Description | Example |
|----------|-------------|---------|
| `@owns_record()` | Current user created the record | `@owns_record()` |
| `@is_superadmin()` | User is a superadmin | `@is_superadmin()` |

> **Screenshot Placeholder 7**
>
> **Description**: A table showing ownership and superadmin functions.

### Function Examples

```python
# Single role check
@has_role("admin")

# Multiple roles (OR logic)
@has_any_role(["admin", "moderator", "editor"])

# All roles required (AND logic)
@has_all_roles(["verified", "subscriber"])

# Ownership check
@owns_record()

# Combined with other conditions
@owns_record() and record.status in ["draft", "pending"]
@has_role("admin") or (@owns_record() and not record.locked)
```

> **Screenshot Placeholder 8**
>
> **Description**: Code showing various function combinations and usage patterns.

---

## Evaluation Context

Rules have access to these variables:

| Variable | Type | Description | Example Fields |
|----------|------|-------------|----------------|
| `user` | dict | Current user | `id`, `email`, `role` |
| `record` | dict | Record being accessed | All record fields |
| `context` | dict | Request context | `account_id`, `request_id` |

> **Screenshot Placeholder 9**
>
> **Description**: A table showing evaluation context variables with their types and available fields.

### Accessing User Data

```python
# User ID
user.id == "user_abc123"

# User email
user.email == "admin@example.com"
user.email.endswith("@domain.com")

# User fields (if you add custom fields)
user.department == "engineering"
user.location == "remote"
```

> **Screenshot Placeholder 10**
>
> **Description**: Code showing how to access various user fields in rules.

### Accessing Record Data

```python
# String fields
record.title == "Important Post"
record.category in ["news", "updates"]

# Numeric fields
record.views > 1000
record.priority >= 3

# Boolean fields
record.published == true
record.archived == false

# Date fields (comparing timestamps)
record.created_at > "2025-01-01T00:00:00Z"

# Nested JSON fields
record.metadata.severity == "high"
record.settings.notifications == true
```

> **Screenshot Placeholder 11**
>
> **Description**: Code showing how to access various record field types in rules.

### Accessing Context

```python
# Account ID
context.account_id == "AB1001"

# Request ID (for logging/tracking)
context.request_id != null
```

> **Screenshot Placeholder 12**
>
> **Description**: Code showing context variable access in rules.

---

## Rule Examples

### Example 1: Edit Own Drafts

Users can edit posts they created, but only if the post is in draft status:

```python
@owns_record() and record.status == "draft"
```

> **Screenshot Placeholder 13**
>
> **Description**: A decision tree showing this rule logic with branches for ownership and status checks.

### Example 2: Admin or Owner

Admins can edit any post. Non-admins can only edit their own:

```python
@has_role("admin") or @owns_record()
```

> **Screenshot Placeholder 14**
>
> **Description**: A visual truth table showing all combinations of admin/owner and the rule result.

### Example 3: Status-Based Access

Published posts are locked - only admins can edit them:

```python
# For update permission
not record.status == "published" or @has_role("admin")

# Equivalent to:
@has_role("admin") or record.status in ["draft", "pending", "archived"]
```

> **Screenshot Placeholder 15**
>
> **Description**: A flowchart showing status-based access control with admin override.

### Example 4: Time-Based Access

Records can only be edited within 24 hours of creation:

```python
# Note: This requires a custom function or field
record.hours_since_creation < 24 or @has_role("admin")
```

> **Screenshot Placeholder 16**
>
> **Description**: A timeline visualization showing the 24-hour window for edits with admin override.

### Example 5: Field-Value Conditions

High-priority tickets require manager approval:

```python
# For update permission
record.priority < 5 or (@has_role("manager") and record.approved)
```

> **Screenshot Placeholder 17**
>
> **Description**: A decision matrix showing priority levels and required roles.

### Example 6: Complex Multi-Condition

Combined conditions for document access:

```python
# User can edit if:
# - They're an admin, OR
# - They own it AND it's not locked, OR
# - They're an editor AND it's in draft status

@has_role("admin")
or (@owns_record() and not record.locked)
or (@has_role("editor") and record.status == "draft")
```

> **Screenshot Placeholder 18**
>
> **Description**: A complex decision tree showing all branches of this rule.

---

## Advanced Patterns

### Pattern 1: Role-Based Workflow

Implement approval workflow based on roles:

```python
# Create permission
@has_role("author") or @has_role("editor")

# Update permission (draft stage)
@has_any_role(["author", "editor"]) and record.status == "draft"

# Update permission (review stage)
@has_role("editor") and record.status == "review"

# Update permission (published stage)
@has_role("admin") and record.status == "published"

# Delete permission
@has_role("admin")
```

> **Screenshot Placeholder 19**
>
> **Description**: A state diagram showing the document workflow (draft → review → published) with role requirements at each stage.

### Pattern 2: Escalation Rules

Higher priority items require higher privileges:

```python
# Priority 1-2: Anyone
record.priority <= 2

# Priority 3-4: Editors
record.priority <= 4 and @has_any_role(["editor", "admin"])

# Priority 5+: Admins only
record.priority >= 5 and @has_role("admin")
```

> **Screenshot Placeholder 20**
>
> **Description**: A table showing priority levels and required roles for each level.

### Pattern 3: Department-Based Access

Users can only access records from their department:

```python
# Assuming user.department field exists
user.department == record.department or @has_role("admin")
```

> **Screenshot Placeholder 21**
>
> **Description**: A diagram showing departments as isolated silos with admin cross-cutting access.

### Pattern 4: Temporary Access

Grant access based on date/time:

```python
# Assuming record.expires_at field exists
record.expires_at == null or record.expires_at > now()

# Or for events
record.event_start <= now() and record.event_end >= now()
```

> **Screenshot Placeholder 22**
>
> **Description**: A timeline visualization showing temporary access window.

### Pattern 5: Field-Specific Rules

Different rules for different fields:

```python
# For "title" field update
@has_role("editor") or @owns_record()

# For "status" field update
@has_role("admin") or (@has_role("editor") and @owns_record())

# For "published_at" field update
@has_role("admin")
```

> **Screenshot Placeholder 23**
>
> **Description**: A table showing fields and their respective permission rules.

---

## Testing Rules

### Unit Testing Rules

Test rule logic in isolation:

```python
# tests/unit/test_rules.py
import pytest
from src.snackbase.core.rules.evaluator import RuleEvaluator

@pytest.mark.asyncio
async def test_owns_record_rule():
    """Test @owns_record() function."""
    evaluator = RuleEvaluator()

    # Should pass: user owns record
    result = await evaluator.evaluate(
        rule="@owns_record()",
        user={"id": "user_123"},
        record={"created_by": "user_123"}
    )
    assert result is True

    # Should fail: user doesn't own record
    result = await evaluator.evaluate(
        rule="@owns_record()",
        user={"id": "user_123"},
        record={"created_by": "user_456"}
    )
    assert result is False
```

> **Screenshot Placeholder 24**
>
> **Description**: Code showing unit tests for rule evaluation with pass/fail cases.

### Integration Testing

Test rules in context of API requests:

```python
# tests/integration/test_permission_rules.py
import pytest

@pytest.mark.asyncio
async def test_cannot_update_published_post_as_author(client, author_token):
    """Test authors cannot update published posts."""

    # Create a published post
    create_response = await client.post(
        "/api/v1/posts/",
        json={"title": "Test", "status": "published"},
        headers={"Authorization": f"Bearer {author_token}"}
    )
    post_id = create_response.json()["id"]

    # Try to update as author (should fail)
    update_response = await client.put(
        f"/api/v1/posts/{post_id}",
        json={"title": "Updated"},
        headers={"Authorization": f"Bearer {author_token}"}
    )

    assert update_response.status_code == 403
```

> **Screenshot Placeholder 25**
>
> **Description**: Code showing integration test for permission rule enforcement via API.

### Manual Testing with Swagger UI

Use Swagger UI at `http://localhost:8000/docs` to test rules interactively:

1. Create test users with different roles
2. Create test records with different states
3. Try operations with different users
4. Verify rules work as expected

> **Screenshot Placeholder 26**
>
> **Description**: Browser screenshot of Swagger UI with authentication and a test request.

---

## Best Practices

### 1. Keep Rules Simple

Complex rules are hard to understand and maintain:

```python
# ❌ BAD: Hard to understand
@has_role("a") or (@has_role("b") and record.x == 1) or (@has_role("c") and not @has_role("d") and record.y in [1,2])

# ✅ GOOD: Clear and logical
@has_role("admin")
or (@has_role("editor") and record.status == "draft")
or (@has_role("reviewer") and record.status == "review")
```

> **Screenshot Placeholder 27**
>
> **Description**: Code comparison showing complex (bad) vs clean (good) rule formatting.

### 2. Use Parentheses for Clarity

Always use parentheses when combining operators:

```python
# ❌ AMBIGUOUS: What does this mean?
@has_role("admin") or @owns_record() and record.status == "draft"

# ✅ CLEAR: Intent is obvious
(@has_role("admin") or @owns_record()) and record.status == "draft"
```

> **Screenshot Placeholder 28**
>
> **Description**: Code comparison showing ambiguous vs clear rule with parentheses.

### 3. Test All Branches

Ensure all logical paths are tested:

```python
# Rule with multiple conditions
@has_role("admin") or (@owns_record() and record.status == "draft")

# Test cases:
# 1. Admin + any status → Should pass
# 2. Owner + draft → Should pass
# 3. Owner + published → Should fail
# 4. Non-owner + any status → Should fail
```

> **Screenshot Placeholder 29**
>
> **Description**: A truth table showing all test cases and expected results.

### 4. Document Complex Rules

Add comments explaining business logic:

```python
# Business rule: Published content is locked
# - Admins can always edit (emergency fixes)
# - Original authors can edit if not locked
# - Editors can edit draft content only
@has_role("admin")
or (@owns_record() and not record.locked)
or (@has_role("editor") and record.status == "draft")
```

> **Screenshot Placeholder 30**
>
> **Description**: Code showing a complex rule with explanatory comments.

### 5. Use Wildcards Carefully

Wildcard permissions with rules can be powerful but dangerous:

```python
# ⚠️ CAUTION: This applies to ALL collections
{
  "collection": "*",
  "delete": @has_role("admin")  # Only admins can delete ANYTHING
}

# ✅ SAFER: Be explicit
{
  "collection": "posts",
  "delete": @has_role("admin")
}
{
  "collection": "comments",
  "delete": @has_role("admin") or @owns_record()
}
```

> **Screenshot Placeholder 31**
>
> **Description**: Code comparison showing risky wildcard (caution) vs explicit collections (safer).

### 6. Consider Performance

Rules are evaluated on every request. Keep them efficient:

```python
# ❌ SLOW: Multiple nested function calls
@has_any_role(["admin", "editor", "moderator", "publisher", "reviewer"])
and not @has_any_role(["banned", "suspended", "pending"])
and record.status in ["draft", "pending", "review", "published"]

# ✅ FASTER: Simplified logic
@has_role("admin") or (@owns_record() and not record.archived)
```

> **Screenshot Placeholder 32**
>
> **Description**: Code comparison showing slow (complex) vs fast (simple) rules with performance notes.

### 7. Use Rule Testing Tools

Test rules before deploying:

```bash
# Test rule evaluation
uv run python -m snackbase test-rule \
  --rule "@owns_record() or @has_role('admin')" \
  --user-id "user_123" \
  --record '{"created_by": "user_123", "status": "draft"}'
```

> **Screenshot Placeholder 33**
>
> **Description**: Terminal output showing a CLI tool for testing rules with evaluation result.

---

## Summary

| Concept | Key Takeaway |
|---------|--------------|
| **Rule Syntax** | Comparisons, logical operators, list membership |
| **Built-in Functions** | `@has_role()`, `@has_any_role()`, `@owns_record()`, `@is_superadmin()` |
| **Context Variables** | `user`, `record`, `context` available in rules |
| **Operator Precedence** | `()` > `not` > comparisons > `and` > `or` |
| **Common Patterns** | Ownership, role-based, status-based, time-based, workflow |
| **Best Practices** | Keep simple, use parentheses, test thoroughly, document |

---

## Related Documentation

- [Security Model](../concepts/security.md) - Overall security architecture
- [Permissions Reference](../permissions.md) - Complete rule syntax reference
- [API Examples](../api-examples.md) - Permission management API usage

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
