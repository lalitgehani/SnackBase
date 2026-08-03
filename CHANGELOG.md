# Changelog

## [0.9.0] - 2026-08-03

This release adds encrypted collection fields and strengthens the handling of
webhook and provider secrets throughout SnackBase.

### Security

- Added Fernet-based encryption for collection fields marked `encrypted: true`.
  Encrypted fields are limited to `text` and `json` types, encrypted before
  persistence, redacted in normal API responses, and excluded from filtering,
  sorting, grouping, searching, and aggregation.
- Added the account-scoped `records:secrets:read` API-key scope and a dedicated
  record-secret reveal endpoint. Secret plaintext is available only through an
  account-bound service API key carrying this scope; ordinary JWT sessions,
  superadmin sessions, and unscoped API keys remain redacted.
- Added shared secret redaction for collection records, provider configuration
  responses, audit values, and error-safe response paths.
- Added production validation that rejects the default encryption key.

### Data migrations

- Added the superadmin-only field encryption migration endpoint:
  `POST /api/v1/collections/{collection_id}/fields/{field_name}/encryption`.
  It converts existing values before changing the field schema flag and leaves
  the schema unchanged if conversion fails.
- Added the `20260803_encrypt_webhook_secrets` Alembic migration to widen the
  webhook secret column and encrypt existing plaintext signing secrets.
- Webhook signing secrets are now encrypted at rest while remaining available
  in plaintext only in the one-time create response and trusted delivery path.

### Authentication and API behavior

- Extended API-key and authenticated-user token data to carry validated scopes.
- Added fail-closed decryption behavior so ciphertext is never returned as if it
  were plaintext when decryption fails.
- Preserved redaction placeholders during record updates so they cannot overwrite
  existing encrypted values.

### Validation and tests

- Added unit, integration, and security coverage for encrypted fields, encryption
  state migration, webhook-secret storage, API-key scopes, authorization, secret
  redaction, and production encryption-key validation.
- Updated the admin collection schema UI and validation for encrypted fields.

### Upgrade notes

- Set `SNACKBASE_ENCRYPTION_KEY` to a stable, secret, non-default value in every
  production deployment before running migrations.
- Run the normal SnackBase migration upgrade before serving traffic so existing
  webhook signing secrets are converted to ciphertext.
- Encrypted fields are intentionally non-queryable and are returned as
  `••••••••` through normal record APIs.
