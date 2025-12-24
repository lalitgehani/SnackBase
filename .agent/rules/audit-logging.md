---
trigger: model_decision
description: GxP-compliant audit logging rules - apply when working on audit trails or compliance features
---

# Audit Logging Rules

## GxP Compliance Requirements

Must comply with 21 CFR Part 11 and EU Annex 11.

## Core Architecture

- **ONE central `audit_log` table** for ALL collections
- **Column-level granularity** - one row per column changed
- **Immutable writes** - NO UPDATE/DELETE on audit logs
- **Blockchain-style integrity** - checksums, previous_hash chain

## Critical Rules

1. **NEVER modify audit log entries** once written
2. **Log every field change** individually
3. **Include integrity chain** - each entry references previous hash
4. **Capture full context** - who, what, when, where, why (if provided)

## Required Fields

- `id`: Unique identifier
- `timestamp`: UTC timestamp of change
- `user_id`: User who made the change
- `account_id`: Account context
- `collection`: Table/collection affected
- `record_id`: ID of affected record
- `field_name`: Specific field changed
- `old_value`: Previous value
- `new_value`: New value
- `action`: CREATE, UPDATE, DELETE
- `checksum`: Hash of current entry
- `previous_hash`: Hash of previous entry
