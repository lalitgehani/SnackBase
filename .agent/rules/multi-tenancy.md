---
activation: model_decision
description: Rules for multi-tenancy, account isolation, and data segregation - apply when working on accounts, users, or data access
---

# Multi-Tenancy Rules

## Core Concepts

Accounts represent isolated tenants within a single database. Data segregation uses row-level isolation via `account_id` column.

## Two-Tier Table Architecture

1. **Core System Tables** - Schema changes via releases only:
   - `accounts`, `users`, `roles`, `permissions`
   - `collections`, `macros`, `migrations`

2. **User-Created Collections** - Global tables shared by ALL accounts:
   - Example: `posts`, `products`
   - SINGLE physical table where all accounts' data is stored together
   - Isolated by `account_id` column

## Account ID Format

Use format `XX####` (2 letters + 4 digits, e.g., `AB1234`):
- `id`: XX#### format (primary key, immutable)
- `slug`: URL-friendly identifier for login (globally unique)
- `name`: Display name (not unique)

## Critical Rules

1. **ALWAYS filter by `account_id`** when querying user-created collections
2. **Never allow cross-account data access** without explicit superadmin permissions
3. **The `collections` table stores schema/metadata**, not actual data
4. **User identity is `(email, account_id)` tuple** - same email can exist in multiple accounts
