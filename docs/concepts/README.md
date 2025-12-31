# Conceptual Guides

Deep dives into SnackBase's core concepts and architectural patterns. These guides explain **how things work** under the hood.

---

## Available Guides

| Guide | Description | Screenshots |
|-------|-------------|-------------|
| [Multi-Tenancy Model](./multi-tenancy.md) | Account model, data isolation, two-tier architecture, multi-account users | 20 |
| [Collections Model](./collections.md) | Dynamic schemas, table generation, field types, auto-generated APIs | 23 |
| [Authentication Model](./authentication.md) | Auth flows, token management, multi-account login, security features | 25 |
| [Security Model](./security.md) | RBAC, permissions, rule engine, field-level security, best practices | 30 |

---

## How to Use These Guides

### For New Users

Start here to understand fundamental concepts:

1. **[Multi-Tenancy Model](./multi-tenancy.md)** - Understand how accounts and data isolation work
2. **[Collections Model](./collections.md)** - Learn how to define schemas and structure data
3. **[Authentication Model](./authentication.md)** - Understand user identity and login flows
4. **[Security Model](./security.md)** - Learn how to control access and permissions

### For Developers

Reference these guides when:

- **Designing data models**: See [Collections Model](./collections.md)
- **Implementing features**: Check [Multi-Tenancy Model](./multi-tenancy.md) for account context
- **Adding permissions**: Reference [Security Model](./security.md) and [Authentication Model](./authentication.md)
- **Debugging access issues**: Review [Security Model](./security.md) rule engine and permission evaluation

### For Architects

Use these guides to:

- **Evaluate SnackBase**: Review all guides for architectural understanding
- **Design integrations**: Understand multi-tenancy and security implications
- **Plan migrations**: See [Collections Model](./collections.md) for schema evolution patterns

---

## Key Concepts Overview

### Multi-Tenancy

- **Account ID Format**: `XX####` (e.g., `AB1001`)
- **Data Isolation**: Row-level via `account_id` column
- **Two-Tier Architecture**: System tables + shared user collection tables
- **Multi-Account Users**: Same email can exist in multiple accounts with different passwords

### Collections

- **Schema Definition**: Metadata stored in `collections` table
- **Shared Tables**: ONE physical table per collection for ALL accounts
- **Field Types**: text, number, email, boolean, date, json, select, relation
- **Auto-Generated APIs**: REST endpoints created automatically

### Authentication

- **User Identity**: `(email, account_id)` tuple
- **Token Management**: Access token (1 hour) + Refresh token (7 days)
- **Password Hashing**: Argon2id (OWASP recommended)
- **Multi-Account Login**: Users must specify account context

### Security

- **RBAC**: Users → Roles → Permissions → Collections
- **Rule Engine**: Custom DSL for fine-grained control
- **Field-Level Security**: Hide sensitive fields from specific roles
- **Account Isolation**: Automatic filtering, enforced at multiple layers

---

## Reading Order

If you're new to SnackBase, read in this order:

```
1. Multi-Tenancy Model
   ↓
2. Collections Model
   ↓
3. Authentication Model
   ↓
4. Security Model
```

If you're familiar with similar systems, you can jump to any guide as needed.

---

## Related Documentation

- **[Quick Start Tutorial](../quick-start.md)** - Hands-on introduction
- **[Architecture](../architecture.md)** - Overall system architecture
- **[API Examples](../api-examples.md)** - Practical API usage
- **[Deployment Guide](../deployment.md)** - Production setup

---

## Contribute

Found an error or want to improve these guides?

1. **Report Issues**: [GitHub Issues](repository-url/issues)
2. **Submit PRs**: Documentation improvements welcome
3. **Ask Questions**: [Community Forum](community-url)

---

**Ready to dive in?** Start with the [Multi-Tenancy Model](./multi-tenancy.md).
