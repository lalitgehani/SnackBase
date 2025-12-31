# Multi-Tenancy Model

SnackBase uses a **shared database, row-level isolation** multi-tenancy model. This guide explains how accounts work, how data is isolated, and what you need to know when building multi-tenant applications.

---

## Table of Contents

- [Overview](#overview)
- [Account Model](#account-model)
- [Data Isolation](#data-isolation)
- [Two-Tier Architecture](#two-tier-architecture)
- [Account ID Format](#account-id-format)
- [System Account vs User Accounts](#system-account-vs-user-accounts)
- [Multi-Account Users](#multi-account-users)
- [Implications for Developers](#implications-for-developers)

---

## Overview

SnackBase enables **Software-as-a-Service (SaaS)** applications by allowing multiple independent tenants (accounts) to coexist in a single database while maintaining complete data isolation.

### Key Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Isolation Type** | Row-level isolation via `account_id` column |
| **Database Model** | Shared database, shared tables |
| **Account Scope** | All data (users, collections, records) scoped to `account_id` |
| **Cross-Account Access** | Not possible by design (enforced at database and API levels) |

> **Screenshot Placeholder 1**
>
> **Description**: A diagram showing multiple accounts (AB1001, XY2048, ZZ9999) with their respective data in shared tables, isolated by account_id column values.

---

## Account Model

### What is an Account?

An **Account** (also called a "tenant" or "organization") represents an isolated workspace containing:
- Users who belong to the account
- Collections (data schemas) defined for the account
- Records (actual data) created by the account's users
- Roles and permissions specific to the account
- Groups for organizing users

### Account Hierarchy

```
SnackBase Instance
│
├── System Account (SY0000)
│   ├── Superadmin users
│   └── Manages all accounts
│
├── Account AB1001 (Acme Corp)
│   ├── Users: alice@acme.com, bob@acme.com
│   ├── Collections: posts, products, orders
│   ├── Roles: admin, editor, viewer
│   └── Records: (all scoped to account_id = "AB1001")
│
├── Account XY2048 (Globex Inc)
│   ├── Users: jane@globex.com
│   ├── Collections: customers, tickets
│   ├── Roles: support, manager
│   └── Records: (all scoped to account_id = "XY2048")
│
└── Account ZZ9999 (StartUp Co)
    └── ... (completely isolated)
```

> **Screenshot Placeholder 2**
>
> **Description**: A tree diagram showing the account hierarchy with the system account at the top and multiple user accounts below, each with their own users, collections, and data.

---

## Data Isolation

### How Isolation Works

Every table in SnackBase (except the `accounts` table itself) includes an `account_id` column:

```sql
-- Example: users table
┌─────────────┬──────────────────┬─────────────┐
│ id          │ email            │ account_id  │
├─────────────┼──────────────────┼─────────────┤
│ user_abc123 │ alice@acme.com   │ AB1001      │
│ user_def456 │ bob@acme.com     │ AB1001      │
│ user_ghi789 │ jane@globex.com  │ XY2048      │
└─────────────┴──────────────────┴─────────────┘

-- Example: Dynamic collection table (posts)
┌─────────────┬─────────────────────┬─────────────┬─────────────┐
│ id          │ title               │ content     │ account_id  │
├─────────────┼─────────────────────┼─────────────┼─────────────┤
│ post_001    │ Hello World         │ Welcome...  │ AB1001      │
│ post_002    │ Acme News           │ Latest...   │ AB1001      │
│ post_003    │ Globex Update       │ News...     │ XY2048      │
└─────────────┴─────────────────────┴─────────────┴─────────────┘
```

> **Screenshot Placeholder 3**
>
> **Description**: Side-by-side view of database tables showing the account_id column in both system tables (users) and dynamic collection tables (posts).

### Automatic Filtering

SnackBase **automatically filters** all queries by `account_id`. Users never see data from other accounts.

**Example API Request:**
```bash
# User from AB1001 requests all posts
GET /api/v1/posts

# SQL executed (simplified):
SELECT * FROM posts WHERE account_id = 'AB1001'
```

The user doesn't need to specify `account_id`—it's automatically added based on their authentication context.

> **Screenshot Placeholder 4**
>
> **Description**: A sequence diagram showing an API request → Middleware extracts account_id → Query with automatic filter → Response returns only account-scoped data.

### Enforcement Layers

Isolation is enforced at **three layers** for defense-in-depth:

| Layer | Mechanism |
|-------|-----------|
| **Database** | `account_id` column with row-level filtering |
| **Repository** | All repositories enforce `account_id` in queries |
| **API Middleware** | Authorization middleware validates account context |

> **Screenshot Placeholder 5**
>
> **Description**: A layered security diagram showing Database (bottom), Repository (middle), and API Middleware (top) layers, each enforcing account isolation.

---

## Two-Tier Architecture

SnackBase uses a **two-tier table architecture** that's critical to understand:

### Tier 1: Core System Tables

These tables define the platform structure and are shared across all accounts:

| Table | Purpose | Schema Changes |
|-------|---------|----------------|
| `accounts` | Account/tenant definitions | Releases only |
| `users` | User identities (per-account) | Releases only |
| `roles` | Role definitions | Releases only |
| `permissions` | Permission rules | Releases only |
| `collections` | Collection schema definitions | Releases only |
| `macros` | SQL macro definitions | Releases only |
| `migrations` | Database migration history | Automatic |

**Important**: Schema changes to these tables only happen via SnackBase releases.

> **Screenshot Placeholder 6**
>
> **Description**: A diagram showing "Core System Tables" as a foundation layer with icons representing accounts, users, roles, permissions, collections.

### Tier 2: User-Created Collections

User collections are **single physical tables** shared by ALL accounts:

| Physical Table | Purpose | Contains |
|----------------|---------|----------|
| `posts` | All accounts' post data | Account AB1001's posts, Account XY2048's posts, etc. |
| `products` | All accounts' product data | All accounts' products in one table |
| `orders` | All accounts' order data | All accounts' orders in one table |

**Critical Concept**: When you create a collection named "posts", you're creating:
1. A **schema definition** in the `collections` table (metadata)
2. A **physical table** named `posts` (if it doesn't exist)
3. All accounts' post data goes into this **single shared table**

> **Screenshot Placeholder 7**
>
> **Description**: A diagram showing the "posts" physical table with rows from multiple accounts (AB1001, XY2048) stored together, separated only by account_id.

### Why This Architecture?

| Approach | Description | SnackBase Choice |
|----------|-------------|------------------|
| **Separate Tables** | Each account gets their own `posts_AB1001`, `posts_XY2048` tables | ❌ Not scalable (thousands of tables) |
| **Separate Databases** | Each account gets their own database | ❌ Complex operations and migrations |
| **Shared Tables** | All accounts share one `posts` table with `account_id` | ✅ **Chosen for scalability and simplicity** |

> **Screenshot Placeholder 8**
>
> **Description**: A comparison diagram showing three multi-tenancy approaches with pros/cons, highlighting SnackBase's shared table approach.

---

## Account ID Format

Accounts use a **fixed-format ID**: `XX####`

### Format Breakdown

```
XX#### = 2 letters + 4 digits

Examples:
├── SY0000  (System account - reserved)
├── AB1001  (Acme Corp)
├── XY2048  (Globex Inc)
└── ZZ9999  (StartUp Co)
```

- **Letters (XX)**: Random uppercase letters A-Z
- **Digits (####)**: Sequential number starting from 0001

> **Screenshot Placeholder 9**
>
> **Description**: A visual breakdown of the account ID format showing the letter component and digit component with color coding.

### Account ID Properties

| Property | Value |
|----------|-------|
| **Format** | `XX####` (e.g., `AB1234`) |
| **Primary Key** | `id` column in `accounts` table |
| **Immutable** | Once assigned, never changes |
| **Globally Unique** | No two accounts share the same ID |
| **System Account** | Always `SY0000` (reserved) |

### Account ID vs Slug vs Name

| Field | Purpose | Example | Constraints |
|-------|---------|---------|-------------|
| `id` | Primary key, immutable | `AB1001` | Auto-generated, `XX####` format |
| `slug` | URL-friendly identifier | `acme-corp` | User-defined, unique, used in login |
| `name` | Display name | `Acme Corporation` | User-defined, not unique |

> **Screenshot Placeholder 10**
>
> **Description**: A table showing the three account identifiers (id, slug, name) with examples and how they're used in the UI and API.

---

## System Account vs User Accounts

### System Account (SY0000)

The **system account** is a special reserved account for superadmin operations:

| Attribute | Value |
|-----------|-------|
| **ID** | `SY0000` (fixed) |
| **Name** | "System" |
| **Purpose** | Superadmin operations, account management |
| **Access** | Superadmin users can operate across ALL accounts |
| **Data** | Contains minimal data (mostly metadata) |

**Superadmin users** are linked to the system account and have:
- Access to ALL accounts
- Ability to create/manage accounts
- Ability to manage global collections
- System-wide visibility

> **Screenshot Placeholder 11**
>
> **Description**: UI screenshot showing the system account in the accounts list with a special badge/indicator distinguishing it from user accounts.

### User Accounts

**User accounts** are regular tenant accounts created by superadmins:

| Attribute | Value |
|-----------|-------|
| **ID** | Auto-generated (e.g., `AB1001`) |
| **Name** | User-defined (e.g., "Acme Corporation") |
| **Purpose** | Regular tenant operations |
| **Access** | Users can only access THEIR account |
| **Data** | Contains all tenant data (users, collections, records) |

**Regular users** (even with "admin" role) are linked to a specific account and have:
- Access ONLY to their account
- No cross-account visibility
- Full CRUD within their account (based on permissions)

> **Screenshot Placeholder 12**
>
> **Description**: UI screenshot showing a user account detail page with the account ID (e.g., AB1001) prominently displayed.

---

## Multi-Account Users

### Enterprise Multi-Account Model

SnackBase supports **enterprise multi-account scenarios** where a single user can belong to multiple accounts with different roles and permissions.

### User Identity

A user's identity is defined by the **(email, account_id) tuple**:

```
┌────────────────────┬─────────────┬──────────────┐
│ email              │ account_id  │ role         │
├────────────────────┼─────────────┼──────────────┤
│ alice@acme.com     │ AB1001      │ admin        │
│ alice@acme.com     │ XY2048      │ viewer       │
│ bob@acme.com       │ AB1001      │ editor       │
│ jane@globex.com    │ XY2048      │ admin        │
└────────────────────┴─────────────┴──────────────┘
```

**Key Point**: The same email (`alice@acme.com`) can exist in multiple accounts (`AB1001`, `XY2048`) with different roles.

> **Screenshot Placeholder 13**
>
> **Description**: A database table view showing users with the same email address appearing multiple times with different account_id values and roles.

### Password Scope

**Passwords are per-account**, not per-email.

This means:
- `alice@acme.com` in `AB1001` has password `Password1!`
- `alice@acme.com` in `XY2048` has password `Password2!`
- These are **different credentials** even though the email is the same

> **Screenshot Placeholder 14**
>
> **Description**: A login form UI showing the account selector (slug/ID field) alongside email and password, illustrating that account context is required.

### Login Flow

When logging in, users must specify their account:

**Option 1: Account in URL**
```
POST /api/v1/auth/login
Host: ab1001.snackbase.com  # Account in subdomain
{
  "email": "alice@acme.com",
  "password": "Password1!"
}
```

**Option 2: Account in Request Body**
```
POST /api/v1/auth/login
{
  "account": "acme-corp",  # Account slug
  "email": "alice@acme.com",
  "password": "Password1!"
}
```

> **Screenshot Placeholder 15**
>
> **Description**: A sequence diagram showing the login flow with account resolution: User provides account → Server resolves account_id → Validates credentials → Returns account-scoped token.

---

## Implications for Developers

### When Building Applications

Understanding multi-tenancy is critical when building on SnackBase:

### 1. Never Store Account ID Manually

```python
# ❌ DON'T: Manual account_id
def create_post(title: str, account_id: str):
    post = Post(title=title, account_id=account_id)
    # Error-prone, security risk

# ✅ DO: Let the framework handle it
def create_post(title: str, context: Context):
    post = Post(title=title, account_id=context.account_id)
    # Automatic, secure
```

> **Screenshot Placeholder 16**
>
> **Description**: Code comparison showing bad practice (manual account_id) vs good practice (using context.account_id).

### 2. Account Isolation is Automatic

You don't need to write WHERE clauses for account filtering:

```python
# ❌ DON'T: Manual filtering
def get_posts(account_id: str):
    return db.query(Post).filter(Post.account_id == account_id).all()

# ✅ DO: Use the repository
def get_posts(context: Context):
    return posts_repo.find_all(context)  # Automatically filters by account_id
```

> **Screenshot Placeholder 17**
>
> **Description**: Code comparison showing manual filtering vs repository pattern with automatic account isolation.

### 3. Cross-Account Queries Are Impossible

By design, you cannot query across accounts:

```python
# ❌ This will NEVER return results
def get_all_posts_from_all_accounts():
    return db.query(Post).all()  # Only returns current account's posts
```

> **Screenshot Placeholder 18**
>
> **Description**: A code snippet showing an attempted cross-account query with a comment explaining it only returns the current account's data.

### 4. Collections Are Global

When creating a collection, remember:
- The collection schema is shared across ALL accounts
- The physical table is shared across ALL accounts
- Each account only sees their own data (via `account_id` filtering)

```python
# Creating "posts" collection creates ONE global table
collections_service.create("posts", fields=[...])
# Result: All accounts can use "posts", but see only their data
```

> **Screenshot Placeholder 19**
>
> **Description**: A diagram showing the "posts" collection being created once, then being available to multiple accounts with isolated data views.

### 5. Migrations Affect All Accounts

Database migrations affect ALL accounts simultaneously:

```python
# ⚠️ CAUTION: This affects ALL accounts
alembic revision --autogenerate -m "Add index to posts"
# Result: ALL accounts' posts data is affected
```

Always test migrations thoroughly before deploying!

> **Screenshot Placeholder 20**
>
> **Description**: A warning diagram showing a database migration operation affecting multiple accounts' data simultaneously.

---

## Summary

| Concept | Key Takeaway |
|---------|--------------|
| **Account Model** | Accounts are isolated tenants with their own users, collections, and data |
| **Data Isolation** | Row-level isolation via `account_id` column, automatic filtering |
| **Two-Tier Architecture** | Core system tables (release-only schema) + user collections (shared global tables) |
| **Account ID Format** | `XX####` format, immutable, primary key |
| **System vs User Accounts** | System account (SY0000) for superadmins; user accounts for regular tenants |
| **Multi-Account Users** | Same email can exist in multiple accounts with different passwords |
| **Developer Implications** | Never handle `account_id` manually; isolation is automatic; collections are global |

---

## Related Documentation

- [Authentication Concepts](./authentication.md) - How authentication works with multi-tenancy
- [Collections](./collections.md) - How dynamic collections work
- [Security Model](./security.md) - Security implications of multi-tenancy
- [Architecture](../architecture.md) - Overall system architecture

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
