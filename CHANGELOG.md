# Unreleased

## 📦 Packaging

- Slimmed the Docker image with a three-stage build: frontend builder, Python
  dependency builder, and a runtime stage that no longer ships
  `build-essential` / gcc (saves ~300 MB).
- Runtime still includes the pinned `uv` binary and `packages/snackbase_fn` for
  Functions env installs; the app process starts via `.venv/bin/uvicorn`
  instead of `uv run`.
- Moved `types-aiobotocore-ses` from runtime dependencies to the dev group
  (type stubs only).
- Tightened `.dockerignore` to shrink build context (tests, examples, UI
  node_modules, coverage, etc.).

---

# Release Notes - v0.10.0

SnackBase v0.10.0 introduces SnackBase Functions: account-scoped, tenant-deployed
Python handlers with versioned deployments, HTTP invocation, an SDK, and an
integrated admin experience.

## ✨ Highlights

### ⚡ SnackBase Functions

- Added account-scoped Function resources with CRUD management, enable/disable
  controls, authentication-required or public invocation modes, soft deletion,
  lifecycle statuses, and per-account limits.
- Added the Functions management API under `/api/v1/functions`, including
  deployment, version listing and activation, source retrieval, grants,
  execution history, test invocation, and execution statistics.
- Added the public invocation API at
  `/api/v1/f/{account_slug}/{slug}` with arbitrary path suffixes, HTTP method
  support, request context, CORS configuration, and execution IDs.
- Added the `20260803_functions` Alembic migration with durable tables for
  functions, immutable function versions, execution records, and encrypted
  function secrets.

### 🚀 Versioned deployments and runtime

- Added deployment of multi-file Python source with deterministic SHA-256
  version hashes, active-version switching, retained version history, and
  per-version virtual environments built with `uv`.
- Added deploy-time validation for safe source paths, required entrypoints,
  Python syntax, exact dependency pins, optional dependency allowlists, and
  configurable source-size limits.
- Added isolated subprocess execution with a dedicated worker pool, execution
  and streaming timeouts, process-group cleanup, captured output, and
  success/failed/timeout execution states.
- Added JSON, plain-text, and streaming/SSE response helpers, plus synchronous
  and asynchronous handler support.
- Added configurable concurrency limits per account and globally, nested
  invocation depth/budget protection, execution-log retention, and cleanup of
  old per-version environments.

### 🧩 Functions SDK and automation

- Added the `snackbase_fn` SDK with request and authentication context objects,
  JSON/text/streaming responses, caller-scoped and grant-controlled admin
  clients, record helpers, and background job enqueue support.
- Added nested function invocation headers and a shared `invoke_function`
  action for hook and endpoint automation.
- Added the `snackbase functions` CLI group with `list`, `deploy`, `logs`,
  `serve` (watch and redeploy), and `purge-executions` commands.

### 🖥️ Admin UI

- Added Functions navigation, listing, creation, editing, enable/disable,
  deletion, authentication settings, and starter templates for JSON handlers,
  public webhooks, and OpenAI-backed handlers.
- Added a multi-file CodeMirror editor with Python/JSON language support,
  syntax highlighting, autocomplete, search, folding, light/dark themes,
  dependency and entrypoint management, safe file-path validation, and
  unsaved-change protection.
- Added in-browser deployment and test controls, execution output and logs,
  runtime statistics, version activation, side-by-side version comparison, and
  function capability-grant management.
- Added a write-only Function Secrets page. Secret values are never returned
  after saving and are injected into function processes as environment
  variables.

### 🛡️ Runtime security

- Added account-bound invocation authentication and deny-by-default admin
  client grants for record reads, writes, deletes, and secret reads.
- Added encrypted-at-rest function secrets with protected runtime environment
  construction; reserved SnackBase credentials are not exposed to user code.
- Added SSRF-safe outbound HTTP policy for function clients and raw `httpx` /
  `urllib` usage, blocking unsafe schemes, private and local addresses,
  metadata hosts, and restricted mail ports.
- Added redaction and truncation for authorization material, cookies, tokens,
  request snapshots, responses, stdout, stderr, and audit metadata.
- Added immutable audit events for function lifecycle operations without
  storing secret values.

## 📖 Documentation and quality

- Added unit, integration, security, UI, and browser end-to-end coverage for
  function management, deployment validation, runtime execution, streaming,
  concurrency, egress controls, grants, secrets, redaction, version comparison,
  and editor accessibility.
- Updated the Python package build and Docker image to include the Functions
  SDK source, refreshed the `uvicorn` requirement and lockfile, and extended
  development cleanup to remove per-version function environments.
- Simplified group member loading in the admin UI and added CodeMirror test
  environment support.

## ⚠️ Upgrade notes

- Run the normal SnackBase migration upgrade before using Functions so the four
  Functions tables are created.
- Function deployment requires `uv` on the SnackBase host to build isolated
  per-version environments. Configure the `SNACKBASE_FUNCTION_*` limits and
  retention settings for the deployment environment.
- Function secrets are write-only through the API; update or replace a secret
  when its value changes rather than expecting the stored plaintext to be
  recoverable.

---

# Release Notes - v0.9.0

SnackBase v0.9.0 is a security-focused release that adds encrypted collection
fields and strengthens the handling of webhook and provider secrets.

## ✨ Highlights

### 🔐 Encrypted collection fields

- Added Fernet-based encryption for collection fields marked `encrypted: true`.
  Encrypted fields are limited to `text` and `json` types, encrypted before
  persistence, and redacted in normal API responses.
- Encrypted fields are intentionally non-queryable: filtering, searching,
  sorting, grouping, and aggregation are rejected for these fields.
- Added fail-closed decryption behavior so ciphertext is never returned as if it
  were plaintext when decryption fails.
- Preserved redaction placeholders during record updates so they cannot overwrite
  existing encrypted values.

### 🪝 Protected webhook and provider secrets

- Added the `20260803_encrypt_webhook_secrets` Alembic migration to widen the
  webhook secret column and encrypt existing plaintext signing secrets.
- Webhook signing secrets are now encrypted at rest while remaining available in
  plaintext only in the one-time create response and trusted delivery path.
- Added shared secret redaction for collection records, provider configuration
  responses, audit values, and error-safe response paths.
- Added production validation that rejects the default encryption key.

### 🎟️ Scoped secret access

- Added the account-scoped `records:secrets:read` API-key scope and a dedicated
  record-secret reveal endpoint.
- Secret plaintext is available only through an account-bound service API key
  carrying this scope. Ordinary JWT sessions, superadmin sessions, and
  unscoped API keys remain redacted.
- Extended API-key and authenticated-user token data to carry validated scopes.

### 🔄 Safe encryption migrations

- Added the superadmin-only field encryption migration endpoint:
  `POST /api/v1/collections/{collection_id}/fields/{field_name}/encryption`.
- The migration converts existing values before changing the field schema flag
  and leaves the schema unchanged if conversion fails.

## 📖 Documentation and quality

- Added unit, integration, and security coverage for encrypted fields, encryption
  state migration, webhook-secret storage, API-key scopes, authorization, secret
  redaction, and production encryption-key validation.
- Updated the admin collection schema UI and validation for encrypted fields.
- Updated application version reporting and documentation to `0.9.0`.

## ⚠️ Upgrade notes

- Set `SNACKBASE_ENCRYPTION_KEY` to a stable, secret, non-default value in every
  production deployment before running migrations.
- Run the normal SnackBase migration upgrade before serving traffic so existing
  webhook signing secrets are converted to ciphertext.
- Encrypted fields are returned as `••••••••` through normal record APIs and
  require an account-bound API key with `records:secrets:read` for explicit
  secret reveals.
