---
trigger: model_decision
description: Authentication rules and patterns - apply when working on auth, login, JWT, or user identity
---

# Authentication Rules

## Enterprise Multi-Account Model

Users can belong to multiple accounts with the same email address. User identity is `(email, account_id)` tuple.

- Passwords are **per-account** - each `(email, account_id)` has its own password
- OAuth identities are stored separately in `oauth_identities` table
- Login **always requires account context** (slug/ID from URL or request body)

## Superadmin vs Admin

| Aspect  | Superadmin                                | Admin (role)                        |
| ------- | ----------------------------------------- | ----------------------------------- |
| Account | Linked to `system` account (ID: `SY0000`) | Linked to specific account          |
| Access  | All accounts and system operations        | Full CRUD within their account only |

## JWT Configuration

- Access token: 1 hour default
- Refresh token: 7 days default
- Claims must include: `user_id`, `account_id`, `email`, `role`
- Implement refresh token rotation

## Authentication Flow

1. User provides credentials + account context (slug or ID)
2. Validate against `(email, account_id)` tuple
3. Issue JWT with account-scoped claims
4. All subsequent requests are scoped to that account
