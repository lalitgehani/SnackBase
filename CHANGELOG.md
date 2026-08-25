# Release Notes - Unreleased

## 🚦 Rate limiting and client-IP attribution

- **The limiter now meters only `/api/v1` paths.** It previously applied to every
  path, so a single cold load of the admin SPA spent the whole token bucket on its
  own HTML, JavaScript and CSS and returned `429` for chunks the page needed to
  render — reaching the browser as unparseable JSON and leaving a blank screen.
  `/health`, `/ready` and `/live` fall outside the prefix and are exempt by the same
  rule.
- **`rate_limit_burst` is replaced by `rate_limit_burst_multiplier`.** The old
  setting documented itself as a multiplier but implemented an absolute ceiling of
  10 requests regardless of `rate_limit_per_minute`. Capacity is now
  `max(1, rate_per_minute × multiplier)`, so the limit an operator configures is the
  limit that is enforced. See the upgrade notes.
- **`trusted_proxies` accepts CIDR networks and `*`.** Entries were compared by exact
  string against the socket peer, so on a managed platform whose edge address is
  neither stable nor published there was no correct value to write. Entries are
  parsed once, and an unparseable one now fails at startup naming the entry rather
  than being silently skipped.
- **`CF-Connecting-IP` is honoured** ahead of `X-Forwarded-For`, gated by the same
  trust check, so an untrusted peer cannot forge it.
- **A warning is logged** — once per peer — when a request arrives proxied from a peer
  that is not trusted, naming the setting and the consequence.
- **`HEAD` is answered on the SPA catch-all and `/health`.** FastAPI's `APIRoute`
  does not derive `HEAD` from `GET` the way Starlette's plain route does, so uptime
  monitors probing with `HEAD` saw `405` on a working deployment.
- **New response header `X-RateLimit-Burst`** reports the computed capacity alongside
  `X-RateLimit-Limit`, on both `200` and `429`.
- `rate_limit_per_hour` is removed. It was defined in settings and documented in
  `.env.example` but never read by the limiter.
- `SNACKBASE_TRUSTED_PROXIES` is now declared in `railway.json` and both compose
  files.

## ⚠️ Upgrade notes

- **Breaking configuration change: `SNACKBASE_RATE_LIMIT_BURST` →
  `SNACKBASE_RATE_LIMIT_BURST_MULTIPLIER`.** The old variable is no longer read;
  delete it. The value is no longer a token count but a multiple of the per-minute
  allowance, so the default of `1.0` with `SNACKBASE_RATE_LIMIT_PER_MINUTE=60` gives
  a capacity of 60 — six times the old default of 10, which is the point. Multiply
  your old intent rather than your old number: `SNACKBASE_RATE_LIMIT_BURST=120`
  against a rate of 60 becomes `SNACKBASE_RATE_LIMIT_BURST_MULTIPLIER=2.0`.
- **`SNACKBASE_RATE_LIMIT_PER_HOUR` is no longer read**; delete it. It never had an
  effect.
- **Correction to the v0.11.0 upgrade note on trusted proxies.** That note said to
  "configure the trusted-proxy setting so `X-Forwarded-For` is honoured" without
  saying that no correct value existed on a managed platform, which is why instances
  shipped misconfigured. Stated plainly: **leaving `trusted_proxies` at its loopback
  default behind a proxy collapses every client into one rate-limit bucket and one
  login-failure budget.** One attacker then exhausts the login budget for every
  visitor, and any visitor's successful login clears the attacker's accumulated
  failure count. Set `SNACKBASE_TRUSTED_PROXIES` to your proxy's address or network,
  or to `*` when the platform's edge address is not stable — `*` is safe only where
  the application is not directly reachable from the internet.
- **Known limitation, unchanged:** rate-limit state is per-process and in-memory, so
  `N` replicas enforce `N` times the configured limit.

---

# Release Notes - v0.11.0

SnackBase v0.11.0 is a security and platform release. It remediates every
Critical, High and Medium finding from the 2026-08-09 VAPT, adds optional
trusted-issuer platform authentication with an integrated Cloud Studio, moves
the runtime to Python 3.14, and ships a substantially smaller Docker image.

## 🛡️ Security remediation (VAPT 2026-08-09)

### 🔴 Critical

- **C-01 — File path traversal.** `FileStorageService` accepted
  `"<B>/../<A>/f.txt"`, which satisfied the account-prefix check and the
  storage-root check while landing in a sibling tenant's directory. Resolved
  paths are now confined to the caller's own account directory with
  `is_relative_to`, and the S3 provider rejects dot segments in object keys.
- **C-02 — Custom-endpoint aggregate injection.** The aggregate action
  interpolated `collection`, `group_by` and `field` directly into `text()` SQL,
  so a template-expanded request value could read another tenant's rows.
  Aggregates now resolve the collection through `CollectionRepository`, validate
  against the collection schema, and execute through
  `RecordRepository.aggregate_records`, which quotes identifiers and ANDs the
  account clause. `collection` now means a collection name, as documented, and
  the previously ignored `filter` is compiled and applied.
- **C-03 — Default signing secrets accepted in production.** `secret_key` and
  `token_secret` could stay on the published placeholder values, so a
  production instance could sign every JWT and API key with a secret in the
  repository. A production `model_validator` now fails closed and names each
  variable still on its default. `SNACKBASE_TOKEN_SECRET` was previously
  undocumented and is now in `.env.example` and `docker-compose.yml`.
- **C-04a — Function deploy-time build isolation.** `uv pip install` inherited
  the full environment, exposing `SNACKBASE_SECRET_KEY`,
  `SNACKBASE_ENCRYPTION_KEY` and `SNACKBASE_DATABASE_URL` to any source
  distribution's build backend. Builds now receive only what `uv` needs, tenant
  pins install with `--only-binary :all:` so no attacker-authored `setup.py`
  runs, and `function_dependency_mode` defaults to `allowlist`.
- **C-04b — Function invoke sandbox.** Invoked handlers ran as ordinary child
  processes with full filesystem and network reach. Three kernel-enforced
  bounds replace that: Landlock confines the child to the interpreter, its own
  read-only function env and its per-invoke work directory; `setrlimit` bounds
  address space, CPU and open files; and the egress policy moved down to
  `socket.connect` so every Python networking path shares it. Governed by
  `SNACKBASE_FUNCTION_SANDBOX_MODE` (`auto`/`required`/`disabled`), where
  `auto` resolves to `required` in production.

### 🟠 High

- **H-01 — Webhook SSRF.** The hand-written RFC1918 deny list left cloud
  instance metadata (`169.254.169.254`), `0.0.0.0/8`, CGNAT and IPv4-mapped
  IPv6 literals reachable, checked only literal IPs, and reflected 5000
  characters of the destination's response body. Classification now uses
  `ipaddress` special-use properties, hostnames are resolved with every A/AAAA
  answer checked, and sends go through a transport pinned to the approved
  address (preserving Host and SNI) so DNS cannot be re-answered between
  validation and connect. Redirects are refused and `test_webhook` returns only
  a status code.
- **H-02 — Unbounded online password guessing.** Login had no effective
  throttle. Two layers now apply: a per-client-IP failure budget charged only by
  failed attempts, and a per-account lockout persisted on the user row with
  doubling backoff. Both live in the login handler so no authenticated-caller
  bypass reaches around them, client-IP derivation is trusted-proxy aware, and
  **rate limiting now defaults to on**.
- **H-03 — SAML assertion binding.** All three providers verified the XML
  signature and then read the assertion, accepting captured assertions
  indefinitely and assertions minted for any other SP on the same IdP.
  `validate_assertion` now enforces `NotBefore`/`NotOnOrAfter` with configurable
  clock skew, a required `AudienceRestriction` naming this SP,
  `SubjectConfirmationData` recipient and expiry, and an assertion-ID replay
  cache claimed last.

### 🟡 Medium

- **M-01 — Realtime bypassed read rules.** Broadcasts filtered only on account
  and subscription, so subscribers received rows their view rule excluded,
  fields outside their projection, and unmasked PII. `RealtimeReadPolicy` now
  reuses the REST read path's controls — view rule, row re-read, field
  projection and PII masking — and reads role and groups fresh per event.
  Deletes deliver only the record id.
- **M-02 — Upload MIME validated from the client header.** Types are now
  detected from file content with `puremagic`; only signature-less types
  (`text/plain`, `text/csv`, `application/json`) are taken on the caller's word
  and must decode as UTF-8. Stored filenames use a UUID plus the *detected*
  type's extension in both the local and S3 providers.
- **M-03 — Uploads buffered whole before the size check.** Uploads are read
  through `buffer_upload_within_limit`: an over-limit `Content-Length` is
  refused before a byte is read, the body is consumed in 1 MiB slices, and
  accepted uploads spool past the first chunk.
- **M-04 — File downloads authorized by path prefix.** Uploads are now
  registered in a `files` table and a download requires a claim: the uploader,
  or a record referencing the path that passes the caller's `view` rule
  (evaluated by the existing `check_collection_permission`). Superadmin keeps
  its bypass.
- **M-05 — Refresh-token replay.** A replayed refresh token now revokes every
  refresh token for that user, forcing both parties to re-authenticate.
- **M-06 — Invitation tokens stored in plaintext.** The column holds a SHA-256
  hash and lookups hash the presented value. Resending rotates the token,
  invalidating any link in flight; listing no longer returns a token, and the
  admin UI's copy-link action goes through resend.
- **M-07 — Login as an account/IdP oracle.** A password attempt against an
  SSO-only user returned the provider name and redirect URL. Both that case and
  an unknown address now return an identical generic 401 and charge the failed
  attempt budget.
- **M-08 — Anonymous reachability.** *Accepted, not fixed.* An `allow_anonymous`
  opt-in was implemented and then reverted: setting an empty rule is already the
  opt-in, and both the rules and the flag were superadmin-owned, so the flag
  moved no decision to a different principal. The residual risk — collections
  and rules are global, so opening one exposes every account with rows in it —
  is recorded in the VAPT roadmap and under "Accepted findings" in the security
  README.
- **M-09 — Image built on an interpreter CI never validated.** Both Python
  stages now build on `3.14-slim`, matching `.python-version`, and every base
  image (including the `uv` image used by `COPY --from`) is digest-pinned.
- **M-10 — Production JSON logging crashed at boot.** `basicConfig` rejects
  `stream` and `handlers` together; the redundant `stream` argument is removed,
  so the shipping default (production + JSON) boots.

### 🧪 Security test suite

- Added a two-tenant security harness with per-surface fixtures (files,
  collections, endpoints, functions), `assert_denied`/`assert_no_leak`/
  `assert_allowed` helpers, a `cross_tenant_matrix` attack helper, and a
  `security` pytest marker applied automatically to `tests/security/`.
- Every Critical, High and Medium finding traces to a named guard, documented in
  `tests/security/README.md`. The suite now carries no `xfail` markers, so a
  VULNERABLE row means a regression rather than a known gap.
- Fixed the security HTML report, which previously hardcoded PASSED for every
  test including the 51 guarding confirmed vulnerabilities. Outcomes now come
  from a `pytest_runtest_makereport` hook and map to an audit vocabulary
  (`xfail` → VULNERABLE, strict `xpass` → FIXED), with findings grouped by VAPT
  ID and requests labelled ALLOWED/DENIED by what the server did.
- Added a Tests workflow running the security suite as its own job with the
  consolidated HTML report uploaded as an artifact.

## ☁️ Platform authentication and Cloud Studio

- Added optional trusted-issuer authentication: instances can accept RS256/ES256
  access tokens from a configured external issuer (SnackBase Cloud or a
  self-hosted OIDC provider) via `SNACKBASE_PLATFORM_ISSUER`,
  `SNACKBASE_PLATFORM_JWKS_URL` and `SNACKBASE_PLATFORM_AUDIENCE`. Every
  `SNACKBASE_PLATFORM_*` setting defaults to unset, so an unconfigured instance
  behaves exactly as before — no JWKS fetch, no alternate auth path.
- Platform principals are supported on both single- and multi-tenant instances.
  A platform principal is the operator of the instance and resolves into the
  system account (`SY0000`); only `snackbase_role: admin` is accepted.
- An existing bootstrap superadmin with the same email is adopted unmodified
  rather than duplicated, so break-glass password login keeps working.
- Merged the Cloud Console into `ui/` as a dual-mode build. Studio migrated to
  `@snackbase/sdk` with runtime platform configuration, behind a single lazy
  route import gated by `IS_PLATFORM`, with an integration test asserting that
  platform-only code is eliminated from self-host production bundles.
- Added a stable environment reference for platform routing and authentication,
  with tests for reference generation and validation.

## 🐍 Runtime and packaging

- Upgraded the runtime to **Python 3.14** (`.python-version`, Ruff
  `target-version`, mypy), switching `hook_registry` to
  `inspect.iscoroutinefunction`.
- Function deploy-time syntax validation now parses with the running
  interpreter's version, so Python 3.14 syntax (t-strings) is accepted.
- Slimmed the Docker image with a three-stage build — frontend builder, Python
  dependency builder, and a runtime stage that no longer ships
  `build-essential`/gcc (saves ~300 MB). The runtime keeps the pinned `uv`
  binary, `ruff` for dynamic collection migrations, and `packages/snackbase_fn`
  for Functions env installs; the app starts via `.venv/bin/uvicorn`.
- The frontend image stage now pins the published `@snackbase/sdk` 0.9.0 and
  `@snackbase/react` 0.6.0 rather than resolving `file:` workspace deps, fixing
  `collections.listPaginated is not a function` in containers.
- Moved `types-aiobotocore-ses` to the dev dependency group and tightened
  `.dockerignore` to shrink the build context.

## 🔧 Fixes and housekeeping

- The SPA no longer answers API paths, so unmatched API requests return an API
  response instead of HTML.
- Audit log endpoints accept requests without a trailing slash; collection rules
  are registered under the collections router.
- Collapsed the byte-for-byte duplicate at
  `packages/snackbase_fn/snackbase_fn` into a symlink of `src/snackbase_fn`, so
  runtime fixes land in the copy function envs actually install.
- Removed the stray empty `src/__init__.py` that made mypy resolve every module
  under two names and abort before checking anything.
- Refreshed E2E tests with a reworked auth flow, a reusable
  delete-collection-by-name helper, and `data-testid` hooks on the collections
  page.
- Updated API documentation for the `sb_ak.<payload>.<signature>` API key format
  and the `/api/v1/admin/api-keys` and `/api/v1/records/{collection}` paths.
- Updated application version reporting and documentation to `0.11.0`.

## ⚠️ Upgrade notes

- **Rate limiting now defaults to on.** Review
  `SNACKBASE_RATE_LIMIT_PER_MINUTE` and, if you run behind a proxy, configure
  the trusted-proxy setting so `X-Forwarded-For` is honoured — it is believed
  only from a configured peer and defaults to loopback.
  **Corrected in the next release:** at the time this was written there was no
  correct value to write on a managed platform, because entries were matched by
  exact string against an edge address that is neither stable nor published. See
  the Unreleased upgrade notes above.
- **`SNACKBASE_TOKEN_SECRET` and `SNACKBASE_SECRET_KEY` must be set to
  non-default values in production**, or the instance refuses to boot. Generate
  with `openssl rand -hex 32`.
- **Function dependency installs now default to `allowlist`.** Name the packages
  your tenants may install, or set `function_dependency_mode=open_pinned` to
  restore the previous behaviour.
- **Function invocation requires a Landlock-capable kernel in production.**
  `SNACKBASE_FUNCTION_SANDBOX_MODE=auto` resolves to `required` there and
  refuses invokes rather than running handlers on the bare host. Set `disabled`
  only where you accept that.
- **Invitation tokens are one-way hashed.** Resending an invitation rotates the
  token and invalidates any link already in flight; listing invitations no
  longer returns a token.
- **File downloads now require a claim.** Attachments are reachable by their
  uploader or through a record the caller may view. Files uploaded before this
  release are not in the `files` table, so only the record-reference path
  authorizes them.
- **Custom-endpoint aggregate actions take a collection name**, not a physical
  table name, and their `filter` is now applied instead of ignored. Review any
  aggregate endpoint configuration.
- Run the normal migration upgrade before starting: `uv run python -m snackbase
  migrate upgrade`.
- The runtime is now Python 3.14. Self-hosted installs that pin an interpreter
  need to update it.

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
