# Multi-Tenancy Model

SnackBase uses a **shared database, row-level isolation** multi-tenancy model. This guide explains how accounts work, how data is isolated, and what you need to know when building multi-tenant applications.

---

## Table of Contents

- [Overview](#overview)
- [Account Model](#account-model)
- [Data Isolation](#data-isolation)
- [Two-Tier Architecture](#two-tier-architecture)
- [Account Identifiers](#account-identifiers)
- [System Account vs User Accounts](#system-account-vs-user-accounts)
- [Multi-Account Users](#multi-account-users)
- [Configuration Hierarchy](#configuration-hierarchy)
- [Implications for Developers](#implications-for-developers)

---

## Overview

SnackBase enables **Software-as-a-Service (SaaS)** applications by allowing multiple independent tenants (accounts) to coexist in a single database while maintaining complete data isolation.

### Key Characteristics

| Characteristic           | Description                                                   |
| ------------------------ | ------------------------------------------------------------- |
| **Isolation Type**       | Row-level isolation via `account_id` column                   |
| **Database Model**       | Shared database, shared tables                                |
| **Account Scope**        | All data (users, collections, records) scoped to `account_id` |
| **Cross-Account Access** | Not possible by design (enforced at database and API levels)  |

> **Description**: A diagram showing multiple accounts (AB1001, XY2048, ZZ9999) with their respective data in shared tables, isolated by account_id column values.

> [!NOTE]
> **Single-Tenant Mode**: While SnackBase is natively multi-tenant, it supports a **Single-Tenant Mode** where the server is dedicated to one account. In this mode, the multi-tenancy architecture remains the same (data is still isolated by `account_id`), but the registration and login flows are modified to ensure all users join the same pre-configured account.

---

## Account Model

### What is an Account?

An **Account** (also called a "tenant" or "organization") represents an isolated workspace containing:

- Users who belong to the account
- Collections (data schemas) defined for the account
- Records (actual data) created by the account's users
- Roles and permissions specific to the account
- Groups for organizing users
- Configuration overrides for providers (auth, email, storage)

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
│   └── Records: (all scoped to account_id = "550e8400-...")
│
├── Account XY2048 (Globex Inc)
│   ├── Users: jane@globex.com
│   ├── Collections: customers, tickets
│   ├── Roles: support, manager
│   └── Records: (all scoped to account_id = "aabbccdd-...")
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

Most tables in SnackBase include an `account_id` column that references the `accounts` table:

```sql
-- Example: users table
┌─────────────┬──────────────────┬─────────────────────┐
│ id          │ email            │ account_id          │
├─────────────┼──────────────────┼─────────────────────┤
│ user_abc123 │ alice@acme.com   │ 550e8400-e29b-...   │
│ user_def456 │ bob@acme.com     │ 550e8400-e29b-...   │
│ user_ghi789 │ jane@globex.com  │ aabbccdd-1234-...   │
└─────────────┴──────────────────┴─────────────────────┘

-- Example: Dynamic collection table (col_posts)
┌─────────────┬─────────────────────┬─────────────┬─────────────────────┐
│ id          │ title               │ content     │ account_id          │
├─────────────┼─────────────────────┼─────────────┼─────────────────────┤
│ post_001    │ Hello World         │ Welcome...  │ 550e8400-e29b-...   │
│ post_002    │ Acme News           │ Latest...   │ 550e8400-e29b-...   │
│ post_003    │ Globex Update       │ News...     │ aabbccdd-1234-...   │
└─────────────┴─────────────────────┴─────────────┴─────────────────────┘
```

> **Screenshot Placeholder 3**
>
> **Description**: Side-by-side view of database tables showing the account_id column in both system tables (users) and dynamic collection tables (col_posts).

### Tables WITHOUT account_id (Global Tables)

The following tables **do not have** an `account_id` column because they define global structures shared by all accounts:

| Table         | Why No account_id?                                           |
| ------------- | ------------------------------------------------------------ |
| `accounts`    | Defines accounts themselves (cannot be scoped to an account) |
| `roles`       | Roles are global definitions shared by all accounts          |
| `permissions` | Permissions are global rules shared by all accounts          |
| `collections` | Collection schemas are global definitions (data is isolated) |
| `macros`      | Macros are global SQL snippets shared by all accounts        |
| `migrations`  | Migrations are global and affect all accounts                |

> **Screenshot Placeholder 3b**
>
> **Description**: A diagram showing global tables (accounts, roles, permissions, collections, macros) at the foundation, with tenant-specific tables built on top.

### Automatic Filtering

SnackBase **automatically filters** all queries by `account_id`. Users never see data from other accounts.

**Example API Request:**

```bash
# User from AB1001 requests all posts
GET /api/v1/posts

# SQL executed (simplified):
SELECT * FROM col_posts WHERE account_id = '550e8400-e29b-41d4-a716-446655440000'
```

The user doesn't need to specify `account_id`—it's automatically added based on their authentication context.

> **Screenshot Placeholder 4**
>
> **Description**: A sequence diagram showing an API request → Middleware extracts account_id → Query with automatic filter → Response returns only account-scoped data.

### Enforcement Layers

Isolation is enforced at **multiple layers** for defense-in-depth:

| Layer                 | Mechanism                                          | Details                                    |
| --------------------- | -------------------------------------------------- | ------------------------------------------ |
| **Database**          | `account_id` column with foreign key to accounts   | Row-level filtering at SQL level           |
| **Hook**              | `account_isolation_hook` (priority -200)           | Automatically injects `account_id` filters |
| **Repository**        | All repositories enforce `account_id` in queries   | Cannot bypass without explicit override    |
| **API Middleware**    | Authorization middleware validates account context | Checks permissions before execution        |
| **Superadmin Bypass** | Superadmin can pass `account_id=None`              | Allows cross-account visibility for admins |

> **Screenshot Placeholder 5**
>
> **Description**: A layered security diagram showing Database (bottom), Hook, Repository, and API Middleware (top) layers, each enforcing account isolation, with superadmin bypass capability.

---

## Two-Tier Architecture

SnackBase uses a **two-tier table architecture** that's critical to understand:

### Tier 1: Core System Tables

These tables define the platform structure and are shared across all accounts:

| Table         | Purpose                       | Has account_id?       | Schema Changes |
| ------------- | ----------------------------- | --------------------- | -------------- |
| `accounts`    | Account/tenant definitions    | No (defines accounts) | Releases only  |
| `users`       | User identities (per-account) | Yes                   | Releases only  |
| `roles`       | Role definitions              | No (global)           | Releases only  |
| `permissions` | Permission rules              | No (global)           | Releases only  |
| `collections` | Collection schema definitions | No (global)           | Releases only  |
| `macros`      | SQL macro definitions         | No (global)           | Releases only  |
| `migrations`  | Database migration history    | No (global)           | Automatic      |

**Important**: Schema changes to these tables only happen via SnackBase releases.

> **Screenshot Placeholder 6**
>
> **Description**: A diagram showing "Core System Tables" as a foundation layer with icons representing accounts, users, roles, permissions, collections.

### Tier 2: User-Created Collections

User collections are **single physical tables** shared by ALL accounts:

| Physical Table | Collection Name | Contains                   |
| -------------- | --------------- | -------------------------- |
| `col_posts`    | "posts"         | All accounts' post data    |
| `col_products` | "products"      | All accounts' product data |
| `col_orders`   | "orders"        | All accounts' order data   |

**Critical Concept**: When you create a collection named "posts", you're creating:

1. A **schema definition** in the `collections` table (metadata)
2. A **physical table** named `col_posts` (if it doesn't exist)
3. All accounts' post data goes into this **single shared table**

> **Screenshot Placeholder 7**
>
> **Description**: A diagram showing the "col_posts" physical table with rows from multiple accounts stored together, separated only by account_id.

### Physical Table Naming Convention

Collection tables are **prefixed with `col_`** to avoid conflicts with system tables:

| Collection Name | Physical Table Name | Example Query                                          |
| --------------- | ------------------- | ------------------------------------------------------ |
| `posts`         | `col_posts`         | `SELECT * FROM col_posts WHERE account_id = ?`         |
| `products`      | `col_products`      | `SELECT * FROM col_products WHERE account_id = ?`      |
| `user_profiles` | `col_user_profiles` | `SELECT * FROM col_user_profiles WHERE account_id = ?` |

This prefix:

- Prevents naming conflicts with system tables
- Makes it clear which tables are user-created collections
- Allows easy identification of collection tables in database dumps

> **Screenshot Placeholder 7b**
>
> **Description**: A mapping diagram showing collection names on the left and their corresponding physical table names with col\_ prefix on the right.

### Why This Architecture?

| Approach               | Description                                                               | SnackBase Choice                             |
| ---------------------- | ------------------------------------------------------------------------- | -------------------------------------------- |
| **Separate Tables**    | Each account gets their own `col_posts_AB1001`, `col_posts_XY2048` tables | ❌ Not scalable (thousands of tables)        |
| **Separate Databases** | Each account gets their own database                                      | ❌ Complex operations and migrations         |
| **Shared Tables**      | All accounts share one `col_posts` table with `account_id`                | ✅ **Chosen for scalability and simplicity** |

> **Screenshot Placeholder 8**
>
> **Description**: A comparison diagram showing three multi-tenancy approaches with pros/cons, highlighting SnackBase's shared table approach.

---

## Account Identifiers

Accounts have **three distinct identifiers** that serve different purposes:

### Identifier Comparison

| Field          | Format           | Purpose                             | Example                                | Uniqueness      |
| -------------- | ---------------- | ----------------------------------- | -------------------------------------- | --------------- |
| `id`           | UUID (36 chars)  | Primary key, foreign key references | `550e8400-e29b-41d4-a716-446655440000` | Globally unique |
| `account_code` | XX#### (6 chars) | Human-readable identifier           | `AB1234`                               | Globally unique |
| `slug`         | URL-friendly     | Login and URL routing               | `acme-corp`                            | Globally unique |
| `name`         | Free text        | Display name only                   | `Acme Corporation`                     | Not unique      |

### Account ID (UUID)

The **internal primary key** for accounts is a standard UUID:

```
Format: 8-4-4-4-12 hexadecimal characters
Example: 550e8400-e29b-41d4-a716-446655440000
```

- **Purpose**: Primary key, used in foreign key references
- **Format**: Standard UUID v4 (36 characters)
- **Used by**: `account_id` columns in all tenant-scoped tables
- **Human-readable**: No (designed for systems, not humans)

### Account Code (XX####)

The **human-readable identifier** for accounts:

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
- **Total Capacity**: 6,760,000 unique codes (26×26×10,000)
- **Reserved Range**: SY#### (skipped during generation)

### Account Code Generation

Account codes are generated **sequentially** from the highest existing code:

```python
# Generation logic
1. Find highest existing account code (e.g., AB2345)
2. Increment numeric portion (AB2346)
3. Skip SY#### range (reserved for system)
4. Assign to new account
```

**Important Notes**:

- Codes are never reused
- Sequential generation ensures predictability
- SY#### range is permanently reserved
- System account uses SY0000

> **Screenshot Placeholder 9**
>
> **Description**: A visual breakdown of the account identifier types showing the UUID (internal), account_code (human-readable), slug (URL-friendly), and name (display) with examples.

### Identifier Usage

| Identifier       | Used In...                         | Example                                                |
| ---------------- | ---------------------------------- | ------------------------------------------------------ |
| **id** (UUID)    | Foreign keys, `account_id` columns | `WHERE account_id = '550e8400-...'`                    |
| **account_code** | Admin UI, support, logs            | "Account AB1234"                                       |
| **slug**         | Login URLs, subdomain routing      | `ab1234.snackbase.com` or `/api/v1/accounts/acme-corp` |
| **name**         | UI display, emails                 | "Welcome to Acme Corporation"                          |

> **Screenshot Placeholder 10**
>
> **Description**: A table showing the four account identifiers with examples and where each is used in the application (UI, API, database).

---

## System Account vs User Accounts

### System Account (SY0000)

The **system account** is a special reserved account for superadmin operations:

| Attribute        | Value                                                      |
| ---------------- | ---------------------------------------------------------- |
| **ID**           | `00000000-0000-0000-0000-000000000000` (nil UUID)          |
| **Account Code** | `SY0000` (fixed)                                           |
| **Name**         | "System"                                                   |
| **Purpose**      | Superadmin operations, system-level configuration          |
| **Access**       | Superadmin users can operate across ALL accounts           |
| **Data**         | Contains minimal data (mostly metadata and system configs) |

**Superadmin users** are linked to the system account and have:

- Access to ALL accounts
- Ability to create/manage accounts
- Ability to manage global collections
- System-wide visibility (can pass `account_id=None` to see all data)

> **Screenshot Placeholder 11**
>
> **Description**: UI screenshot showing the system account in the accounts list with a special badge/indicator distinguishing it from user accounts.

### User Accounts

**User accounts** are regular tenant accounts created by superadmins:

| Attribute        | Value                                                              |
| ---------------- | ------------------------------------------------------------------ |
| **ID**           | Auto-generated UUID (e.g., `550e8400-e29b-41d4-a716-446655440000`) |
| **Account Code** | Auto-generated (e.g., `AB1001`)                                    |
| **Name**         | User-defined (e.g., "Acme Corporation")                            |
| **Purpose**      | Regular tenant operations                                          |
| **Access**       | Users can only access THEIR account                                |
| **Data**         | Contains all tenant data (users, collections, records)             |

**Regular users** (even with "admin" role) are linked to a specific account and have:

- Access ONLY to their account
- No cross-account visibility
- Full CRUD within their account (based on permissions)

> **Screenshot Placeholder 12**
>
> **Description**: UI screenshot showing a user account detail page with the account code (e.g., AB1001) prominently displayed.

---

## Multi-Account Users

### Enterprise Multi-Account Model

SnackBase supports **enterprise multi-account scenarios** where a single user can belong to multiple accounts with different roles and permissions.

### User Identity

A user's identity is defined by the **(email, account_id) tuple**:

```
┌────────────────────┬─────────────────────┬──────────────┐
│ email              │ account_id          │ role         │
├────────────────────┼─────────────────────┼──────────────┤
│ alice@acme.com     │ 550e8400-e29b-...   │ admin        │
│ alice@acme.com     │ aabbccdd-1234-...   │ viewer       │
│ bob@acme.com       │ 550e8400-e29b-...   │ editor       │
│ jane@globex.com    │ aabbccdd-1234-...   │ admin        │
└────────────────────┴─────────────────────┴──────────────┘
```

**Key Point**: The same email (`alice@acme.com`) can exist in multiple accounts with different roles.

> **Screenshot Placeholder 13**
>
> **Description**: A database table view showing users with the same email address appearing multiple times with different account_id values and roles.

### Password Scope

**Passwords are per-account**, not per-email.

This means:

- `alice@acme.com` in account `AB1001` has password `Password1!`
- `alice@acme.com` in account `XY2048` has password `Password2!`
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

## Configuration Hierarchy

SnackBase uses a **hierarchical configuration model** for provider settings (authentication, email, storage, etc.):

### Two-Level Hierarchy

```
System-Level Configuration
├── account_id: 00000000-0000-0000-0000-000000000000 (nil UUID)
├── Purpose: Default configs for all accounts
└── Applied when: No account-level override exists

Account-Level Configuration
├── account_id: <specific account UUID>
├── Purpose: Per-account custom settings
└── Priority: Always overrides system defaults
```

### Configuration Resolution

When resolving a provider configuration:

1. **Check account-level** config for the specific account
2. **If not found**, use system-level default
3. **Merge** with fallback values for any missing keys

```python
# Example: Email provider resolution
config = config_registry.get_config(
    account_id="550e8400-e29b-41d4-a716-446655440000",
    provider_name="email"
)

# Returns:
# - Account-specific config if exists
# - System-level config if no account override
# - Cached for 5 minutes
```

### Use Cases

| Configuration Type   | System-Level        | Account-Level           |
| -------------------- | ------------------- | ----------------------- |
| **SMTP Settings**    | Default SMTP server | Custom SMTP per account |
| **OAuth Providers**  | Available to all    | Custom app credentials  |
| **Storage Backends** | Default S3 bucket   | Per-account buckets     |
| **Auth Providers**   | Default providers   | Custom provider config  |

> **Screenshot Placeholder 16**
>
> **Description**: A diagram showing the configuration hierarchy with system-level defaults at the top and account-level overrides below, with arrows showing resolution flow.

### Key Points

- System-level configs use the **nil UUID** (`00000000-0000-0000-0000-000000000000`)
- Account-level configs use the **account's UUID** as `account_id`
- Resolution is cached for **5 minutes** for performance
- Built-in providers are marked with `is_builtin` flag (cannot be deleted)

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

> **Screenshot Placeholder 17**
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

> **Screenshot Placeholder 18**
>
> **Description**: Code comparison showing manual filtering vs repository pattern with automatic account isolation.

### 3. Cross-Account Queries Are Impossible

By design, you cannot query across accounts:

```python
# ❌ This will NEVER return results
def get_all_posts_from_all_accounts():
    return db.query(Post).all()  # Only returns current account's posts
```

**Superadmin Exception**: Superadmins can explicitly pass `account_id=None` to bypass filtering:

```python
# ✅ Superadmin-only cross-account query
def get_all_posts_as_superadmin():
    return posts_repo.find_all(context, account_id=None)  # Returns ALL posts
```

> **Screenshot Placeholder 19**
>
> **Description**: A code snippet showing an attempted cross-account query with a comment explaining it only returns the current account's data, plus a superadmin bypass example.

### 4. Collections Are Global

When creating a collection, remember:

- The collection schema is shared across ALL accounts
- The physical table (`col_<name>`) is shared across ALL accounts
- Each account only sees their own data (via `account_id` filtering)

```python
# Creating "posts" collection creates ONE global table
collections_service.create("posts", fields=[...])
# Result: col_posts table created (if not exists)
#         All accounts can use "posts", but see only their data
```

> **Screenshot Placeholder 20**
>
> **Description**: A diagram showing the "posts" collection being created once, creating the col_posts table, then being available to multiple accounts with isolated data views.

### 5. Migrations Affect All Accounts

Database migrations affect ALL accounts simultaneously:

```python
# ⚠️ CAUTION: This affects ALL accounts
alembic revision --autogenerate -m "Add index to col_posts"
# Result: ALL accounts' posts data is affected
```

Always test migrations thoroughly before deploying!

> **Screenshot Placeholder 21**
>
> **Description**: A warning diagram showing a database migration operation affecting multiple accounts' data simultaneously.

### 6. Use Account Code for Display

When displaying account identifiers in UI or logs:

```python
# ✅ DO: Use account_code for display
account_code = account.account_code  # "AB1234"
print(f"Processing account {account_code}")

# ❌ DON'T: Use UUID for display
account_id = account.id  # "550e8400-e29b-41d4-a716-446655440000"
print(f"Processing account {account_id}")  # Hard to read!
```

> **Screenshot Placeholder 22**
>
> **Description**: UI comparison showing a list of accounts with human-readable codes (AB1234) vs UUIDs, highlighting the user experience difference.

---

## Summary

| Concept                     | Key Takeaway                                                                            |
| --------------------------- | --------------------------------------------------------------------------------------- |
| **Account Model**           | Accounts are isolated tenants with their own users, collections, and data               |
| **Account Identifiers**     | UUID (id) for system, account_code (XX####) for humans, slug for URLs, name for display |
| **Data Isolation**          | Row-level isolation via `account_id` column, enforced at multiple layers                |
| **Global Tables**           | accounts, roles, permissions, collections, macros, migrations have no account_id        |
| **Two-Tier Architecture**   | Core system tables (release-only schema) + user collections (shared col\_\* tables)     |
| **System Account**          | Uses nil UUID for ID, SY0000 for account_code, reserved for superadmin operations       |
| **Multi-Account Users**     | Same email can exist in multiple accounts with different passwords                      |
| **Configuration Hierarchy** | System-level (nil UUID) defaults + account-level overrides                              |
| **Developer Implications**  | Never handle `account_id` manually; isolation is automatic; collections are global      |

---

## Related Documentation

- [Authentication Concepts](./authentication.md) - How authentication works with multi-tenancy
- [Collections](./collections.md) - How dynamic collections work
- [Security Model](./security.md) - Security implications of multi-tenancy
- [Architecture](../architecture.md) - Overall system architecture
- [Configuration System](./configuration.md) - Provider configuration management

---

**Questions?** Check the [FAQ](../faq.md) or open an issue on GitHub.
