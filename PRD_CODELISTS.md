# SnackBase Codelists - Product Requirements Document

**Version**: 1.1  
**Last Updated**: 2026-07-25  
**Status**: In Progress (Phase 1 complete)  
**Target Audience**: SnackBase core engineers, Admin UI engineers, Cloud control-plane / console engineers, product stakeholders  
**Source of Truth**: Stakeholder design discussion on multi-tenant shared dimensions; CDISC Controlled Terminology conceptual model; existing SnackBase multi-tenancy, configurations hierarchy, and Admin UI patterns; control-plane fan-out limitation for `regions`  
**Primary Platform**: SnackBase backend (Python 3.12+, FastAPI, SQLAlchemy), Admin UI (React 19, Vite, ShadCN), optional consumers: Cloud Console + `@snackbase/sdk`

**Compatibility Policy**: **No backward compatibility.** Breaking changes are acceptable and preferred over dual-path designs. There is no requirement to keep collection-based region fan-out, dual sources of truth, feature flags for old pickers, or interim dual validation. Remove obsolete paths cleanly; update call sites, tests, seeds, and docs in the same delivery. Do not ship “legacy mode.”

---

## Phase 1: Foundation — Data Model and Domain Services ✅ **DONE**

**Duration**: 2–3 weeks  
**Goal**: Establish first-class codelist storage and domain services that support system-shared and account-private dictionaries without using tenant collection fan-out.

**Overview**: Phase 1 introduces core system tables and domain logic for codelists, values, labels, and account overrides. It locks the stable-key model (submission `code` stored in business data; labels resolved at read time) and mirrors the configurations pattern (`account_id` always populated; system scope uses system account + `is_system`). No public API or Admin UI yet—foundation only.

### 1.1: Codelist Master Entity and Persistence ✅ **DONE**

**User Story**: As a platform engineer, I need a first-class `codelists` table so that shared dictionaries are not modeled as per-tenant collection rows.

**Requirements**:

- Create `codelists` system table with fields: `id`, `code`, `name`, `description`, `definition`, `scope` (`system` | `account`), `account_id`, `is_system`, `is_extensible`, `is_active`, `is_builtin`, `external_code`, `version`, `metadata` (JSON), `created_at`, `updated_at`
- `account_id` is always populated (system account UUID for system lists; tenant UUID for account lists)
- Uniqueness: system list `code` unique among system lists; account list unique on `(account_id, code)`
- Alembic migration; SQLAlchemy model; domain entity; repository CRUD
- Builtin/system lists cannot be hard-deleted via domain service (soft-deactivate only unless empty and not builtin)
- Follow existing system-account constant `00000000-0000-0000-0000-000000000000` / `SY0000`

**Acceptance Criteria**:

- [x] Migration creates `codelists` with indexes and uniqueness constraints
- [x] Repository can create system and account-scoped codelists
- [x] Duplicate system `code` is rejected
- [x] Duplicate `(account_id, code)` for account lists is rejected
- [x] Builtin flag prevents hard delete in domain service
- [x] Unit tests cover create, unique constraint, and scope rules

**Dependencies**: None

**Testing Requirements**:

- Unit tests for entity validation and repository uniqueness
- Migration upgrade/downgrade smoke test
- Isolation: account A cannot load account B private codelist by id via repository scope helpers

### 1.2: Codelist Values (Decode / Terms) Entity ✅ **DONE**

**User Story**: As a platform engineer, I need value rows with stable submission codes so that applications store machine-stable keys independent of display labels.

**Requirements**:

- Create `codelist_values` table: `id`, `codelist_id`, `code` (submission value), `external_code`, `sort_order`, `is_active`, `scope`, `account_id`, `is_system`, `definition`, `metadata` (JSON), timestamps
- Unique constraint on `(codelist_id, code, account_id)` to allow system value + optional account extension with same list without collision across owners
- System values use system `account_id`; account extension values use tenant `account_id`
- Soft-deactivate via `is_active=false`; prefer over hard delete when referenced
- Domain service methods: add value, update value, deactivate value, list values by codelist with scope filters

**Acceptance Criteria**:

- [x] Values can be created for a system codelist with unique `code`
- [x] Account-owned extension values are stored with tenant `account_id`
- [x] Deactivate sets `is_active=false` and retains row
- [x] Metadata JSON round-trips (e.g. `{"country":"DE","status":"available"}`)
- [x] Unit tests cover uniqueness and soft deactivate

**Dependencies**: F1.1

**Testing Requirements**:

- Unit tests for CRUD, uniqueness, metadata
- Test that deactivating a value keeps the row queryable by id/code for historical display

### 1.3: Value Labels (Language Layer) Entity ✅ **DONE**

**User Story**: As a product operator supporting multiple languages, I need labels per language so that Japanese and English UIs can share the same submission codes.

**Requirements**:

- Create `codelist_value_labels` table: `id`, `value_id`, `language` (BCP-47, e.g. `en`, `ja`), `label`, `description`, `is_preferred`, timestamps
- Unique constraint supporting preferred + synonym strategy (at minimum unique preferred per `(value_id, language)` or unique `(value_id, language, label)` with single preferred per language)
- Domain service: set preferred label for language, list labels for value, bulk upsert labels for a value
- Label resolution helper: requested language → fallback language → `en` → raw `code`

**Acceptance Criteria**:

- [x] Can store `en` and `ja` preferred labels for the same value
- [x] Resolution returns Japanese label when `lang=ja` is requested
- [x] Resolution falls back to `en` then `code` when preferred language missing
- [x] Unit tests cover fallback chain

**Dependencies**: F1.2

**Testing Requirements**:

- Unit tests for preferred label upsert and resolution fallback order
- Edge cases: empty label rejected; invalid empty language rejected

### 1.4: Account Overrides Entity ✅ **DONE**

**User Story**: As a multi-tenant operator, I need per-account overrides so that I can hide or default shared values without duplicating the master list into every account.

**Requirements**:

- Create `codelist_account_overrides` table: `id`, `account_id`, `codelist_id`, `value_id`, `visibility` (`visible` | `hidden`), `is_default`, `sort_order` (nullable override), `metadata_override` (JSON nullable), timestamps
- Unique `(account_id, value_id)`
- Domain service: set/clear override, list overrides for account+codelist
- Overrides never copy value rows; they only store deltas
- Clearing override restores system effective behavior for that account

**Acceptance Criteria**:

- [x] Account can hide a system value via override
- [x] Account can mark one value as default
- [x] Unique constraint prevents duplicate override rows
- [x] Clear override removes the delta row
- [x] Unit tests cover hide, default, clear

**Dependencies**: F1.1, F1.2

**Testing Requirements**:

- Unit tests for override CRUD and uniqueness
- Security: override for account A not readable/writable under account B context in service methods

### 1.5: Codelist Domain Service and Effective Resolution ✅ **DONE**

**User Story**: As an application or API layer, I need a single effective-resolution function so that I always get the correct value set for an account and language without implementing merge logic myself.

**Requirements**:

- Implement `CodelistService` with:
  - CRUD for codelists (scope-aware)
  - CRUD for values and labels
  - Override management
  - `get_effective_values(account_id, codelist_code, language, include_inactive=False)`
- Effective algorithm:
  1. Resolve codelist: account-owned list with code if present (when product rules allow), else system list
  2. Candidate values: active system values + active account extension values if `is_extensible`
  3. Apply account overrides (drop hidden; apply sort/default/metadata merge)
  4. Resolve labels via language fallback
  5. Return ordered list of DTOs: `code`, `label`, `definition`, `metadata`, `is_default`, `sort_order`, `scope`, `is_active`
- Do not use user-collection record repositories for this data path
- Service must be usable later from API, validation, and Admin UI backends

**Acceptance Criteria**:

- [x] Effective list for account with no overrides returns all active system values
- [x] Hidden override removes value from effective list
- [x] New system value appears for all accounts without per-account insert
- [x] Extension values on extensible list appear only for owning account
- [x] Label language fallback works end-to-end in service tests
- [x] Unit tests cover all merge branches

**Dependencies**: F1.1, F1.2, F1.3, F1.4

**Testing Requirements**:

- Comprehensive unit tests for resolution matrix (system only, hide, default, extension, languages)
- Property-style cases: N accounts, one system insert → N accounts see value without fan-out

### 1.6: Seed Bootstrap for Builtin `regions` Codelist ✅ **DONE**

**User Story**: As a Cloud control-plane operator, I need a builtin `regions` system codelist with `eu-01` so that product features have a stable dimension without seeding each customer account.

**Requirements**:

- Bootstrap (migration data or startup/seed function) creates system codelist `regions` with `is_builtin=true`, `is_extensible=false` (MVP)
- Seed value `eu-01` with metadata `{ "country": "DE", "status": "available", "sort_order": 1 }` and EN label “EU Central (Germany)”
- Optional JA label may be included if available; otherwise EN-only is acceptable for Phase 1
- Bootstrap is idempotent
- Control-plane collection fan-out for regions is **not** retained as a fallback; Phase 4 removes it outright (breaking change)

**Acceptance Criteria**:

- [x] Fresh DB after migrate/seed has system codelist `regions` and value `eu-01`
- [x] Re-running bootstrap does not duplicate rows
- [x] `get_effective_values(any_account, "regions", "en")` includes `eu-01`
- [x] Builtin list cannot be hard-deleted

**Dependencies**: F1.5

**Testing Requirements**:

- Integration/unit test for idempotent seed
- Assert effective values for two different account UUIDs both include `eu-01` without per-account value rows

## Phase 1 Definition of Done ✅ **DONE**

- [x] All Phase 1 features implemented
- [x] Migrations applied cleanly on SQLite and PostgreSQL targets used by SnackBase
- [x] Domain service effective-resolution tests pass
- [x] Builtin `regions` / `eu-01` seeded idempotently
- [x] No dependency on collection fan-out for shared dimensions at the service layer
- [x] Stakeholder demo of effective resolution for two accounts

---

## Phase 2: Core API — Management and Effective Read Paths 🟧 **PLANNED**

**Duration**: 2–3 weeks  
**Goal**: Expose secure REST APIs so clients and Admin UI can manage codelists and read effective values without superadmin collection hacks.

**Overview**: Phase 2 adds HTTP routes, schemas, authz, and OpenAPI documentation. Superadmins manage system dictionaries; account admins manage private lists and overrides; authenticated users can read effective values for their account. This phase does not yet ship full Admin UI.

### 2.1: Effective Values Read API 🟧 **PLANNED**

**User Story**: As an authenticated app or Cloud Console, I need to list effective codelist values for my account so that pickers show the right shared and customized options.

**Requirements**:

- `GET /api/v1/codelists` — list codelists visible to caller (system + own account)
- `GET /api/v1/codelists/{code}` — get codelist metadata
- `GET /api/v1/codelists/{code}/values?lang=en&active=true` — effective values for caller account
- Language query param optional; default `en` or account preference if available
- Response DTOs include `code`, `label`, `definition`, `metadata`, `is_default`, `sort_order`
- Authenticated users required for MVP (no anonymous public codelists unless explicitly flagged later)
- Superadmin may pass `account_id` query to preview effective list as another account

**Acceptance Criteria**:

- [ ] Authenticated user receives effective `regions` values including `eu-01`
- [ ] Hidden value for that account is omitted
- [ ] Unauthenticated request is rejected (401/403 per platform norms)
- [ ] Superadmin preview with `account_id` returns that account’s effective set
- [ ] OpenAPI documents endpoints and query params

**Dependencies**: F1.5

**Testing Requirements**:

- API integration tests for two accounts with different overrides
- Auth negative tests
- Superadmin preview tests

### 2.2: System Codelist Management API (Superadmin) 🟧 **PLANNED**

**User Story**: As a superadmin, I need to create and update system codelists and values so that platform dimensions stay centralized.

**Requirements**:

- Superadmin-only routes for system scope:
  - Create/update/deactivate codelist
  - Create/update/deactivate values
  - Upsert labels
- Reject non-superadmin attempts to create `scope=system`
- Protect `is_builtin` lists from destructive delete
- Audit log significant mutations (create/update/deactivate) if audit hooks exist for similar admin resources

**Acceptance Criteria**:

- [ ] Superadmin can create system codelist and values
- [ ] Account admin cannot create system codelist (403)
- [ ] Builtin list delete is rejected
- [ ] Labels can be upserted for `en` and `ja`
- [ ] Integration tests cover happy path and authz failures

**Dependencies**: F1.5, F2.1

**Testing Requirements**:

- Authz matrix tests (superadmin vs account admin vs user)
- CRUD integration tests for system lists

### 2.3: Account Private Codelists and Extension Values API 🟧 **PLANNED**

**User Story**: As an account admin, I need private codelists (and optional extensions on extensible shared lists) so that tenant-specific enums stay isolated.

**Requirements**:

- Account admin can create/update/deactivate account-scoped codelists
- Account admin can manage values on own account codelists
- If system list `is_extensible=true`, account admin may add account-owned values to that list
- If `is_extensible=false`, extension create is rejected
- Account A cannot read/write account B private lists or extension values
- Users without admin role cannot mutate (configurable: only `admin` role for MVP)

**Acceptance Criteria**:

- [ ] Account admin creates private codelist and values
- [ ] Effective API returns private list only for that account
- [ ] Cross-account access denied
- [ ] Non-extensible system list rejects extension values
- [ ] Extensible list allows account-only extension value in effective results

**Dependencies**: F2.1, F2.2

**Testing Requirements**:

- Cross-account isolation integration tests
- Extensible vs non-extensible matrix tests

### 2.4: Account Override Management API 🟧 **PLANNED**

**User Story**: As an account admin, I need to hide or default shared values for my account so that unavailable options do not appear in product UIs.

**Requirements**:

- `PUT /api/v1/codelists/{code}/values/{value_code}/override` with body `{ visibility, is_default, sort_order?, metadata_override? }`
- `DELETE .../override` clears override
- Account admin operates only on own account; superadmin may target `account_id`
- At most one `is_default=true` per account+codelist (clear previous default)
- Override cannot invent a value_code that does not exist on the list

**Acceptance Criteria**:

- [ ] Hide removes value from effective list for that account only
- [ ] Other accounts still see the value
- [ ] Setting default flips previous default off
- [ ] Clear restore default effective behavior
- [ ] Invalid value_code returns 404

**Dependencies**: F1.4, F2.1

**Testing Requirements**:

- Integration tests multi-account hide isolation
- Default uniqueness tests

### 2.5: Validation Helper for Codelist Membership 🟧 **PLANNED**

**User Story**: As a backend developer, I need a reusable validator so that product endpoints can reject invalid codes against the effective list.

**Requirements**:

- Service method `assert_in_codelist(account_id, codelist_code, value_code, *, allow_inactive_existing=False)`
- Raise domain/HTTP-friendly validation error when code not in effective set
- Optional mode for updates: allow historically stored inactive codes when editing old records (document behavior)
- Unit-tested helper used by at least one example (regions) in later phase; stub usage tests in this phase

**Acceptance Criteria**:

- [ ] Valid effective code passes
- [ ] Hidden or unknown code fails
- [ ] Documented behavior for inactive historical codes
- [ ] Unit tests cover pass/fail paths

**Dependencies**: F1.5

**Testing Requirements**:

- Unit tests for validator including hidden and inactive cases

### 2.6: API Documentation and Error Contracts 🟧 **PLANNED**

**User Story**: As an SDK and Console engineer, I need consistent error shapes and OpenAPI docs so that clients can integrate without reverse-engineering.

**Requirements**:

- Document all codelist endpoints in OpenAPI / Mintlify-ready descriptions
- Standardize error codes for: not found, forbidden, duplicate code, non-extensible, builtin protected
- Align with existing SnackBase API error conventions
- Add docs page outline under `docs/` for Codelists concept (draft content acceptable if linked from API)

**Acceptance Criteria**:

- [ ] OpenAPI includes codelist paths
- [ ] Error responses match platform patterns
- [ ] Draft concept doc describes system vs account vs overrides
- [ ] Example requests for effective values and override hide

**Dependencies**: F2.1–F2.4

**Testing Requirements**:

- Contract tests or schema snapshot for key endpoints if project pattern exists
- Manual OpenAPI review checklist

## Phase 2 Definition of Done 🟧 **PLANNED**

- [ ] All Phase 2 APIs implemented and authz-tested
- [ ] Effective values API used successfully by integration tests for two accounts
- [ ] Superadmin can fully manage system `regions` via API
- [ ] Account override hide works without value fan-out
- [ ] OpenAPI/docs draft available
- [ ] Stakeholder demo of API-driven region list without collection seed per account

---

## Phase 3: Admin UI — Codelist Workspace 🟧 **PLANNED**

**Duration**: 3–4 weeks  
**Goal**: Deliver a first-class Admin UI workspace so operators can manage codelists, values, labels, and overrides without raw API calls.

**Overview**: Phase 3 builds on existing Admin UI patterns (Collections workspace rail + tabs; Configuration system/account mental model; Macros list/service layer). Codelists appear under **Data** navigation. Superadmin and account admin experiences are gated appropriately.

### 3.1: Navigation, Routes, and Workspace Shell 🟧 **PLANNED**

**User Story**: As an admin user, I need Codelists in the Admin sidebar and a list/detail workspace so that I can manage dictionaries like other platform data resources.

**Requirements**:

- Add **Data → Codelists** nav item (`/admin/codelists`)
- Routes: list/rail, new, detail with tabs (`values`, `overrides`, `settings`)
- Workspace shell: left rail of codelists + detail pane
- Filters: All | System | Account; search by code/name
- Scope badges (`System`, `Account`), builtin lock indicator, active status
- Reuse ShadCN components; do not hand-roll design-system primitives
- Wire `codelists.service.ts` + TypeScript types

**Acceptance Criteria**:

- [ ] Nav link visible to authenticated admin users (role gates as designed)
- [ ] Workspace loads codelist rail from API
- [ ] Selecting a codelist opens detail with default Values tab
- [ ] Empty state explains system vs account dictionaries
- [ ] UI builds and typechecks

**Dependencies**: F2.1, F2.2

**Testing Requirements**:

- Component/unit tests for route shell and empty state
- Smoke test navigation render with mocked service

### 3.2: Create and Settings for Codelists 🟧 **PLANNED**

**User Story**: As a superadmin or account admin, I need to create and edit codelist metadata so that new dictionaries can be defined from the UI.

**Requirements**:

- Create flow: code, name, description, scope (system only if superadmin), extensible switch, active switch
- Settings tab: edit mutable fields; code immutable after create (display only)
- Builtin protection messaging; deactivate instead of delete for builtin
- Validation: code pattern `^[a-z][a-z0-9_]*$`
- Toast/error handling via existing patterns

**Acceptance Criteria**:

- [ ] Superadmin creates system codelist from UI
- [ ] Account admin creates account codelist from UI
- [ ] Account admin cannot select system scope
- [ ] Invalid code shows field error
- [ ] Builtin list shows restricted delete/deactivate affordances

**Dependencies**: F3.1, F2.2, F2.3

**Testing Requirements**:

- Component tests for form validation and role-gated scope
- Service mock tests for create/update

### 3.3: Values Management UI 🟧 **PLANNED**

**User Story**: As an operator, I need a values table with add/edit/deactivate so that I can maintain submission codes and metadata visually.

**Requirements**:

- Values tab table: code, label preview, sort order, status, scope, metadata summary, actions
- Language preview selector (e.g. `en`, `ja`) affecting label column only
- Add/Edit dialogs: code, definition, sort_order, active, metadata editor
- Deactivate confirmation; prefer deactivate over delete
- Search filter on code/label
- Superadmin edits system values; account admin edits own list values / extensions when allowed

**Acceptance Criteria**:

- [ ] Can add `us-01` to system `regions` from UI (superadmin)
- [ ] Label preview updates when language switched
- [ ] Deactivated values hidden by default with “Show inactive” toggle
- [ ] Code field locked on edit after create
- [ ] Tests cover table render and dialog validation

**Dependencies**: F3.1, F2.2, F2.3

**Testing Requirements**:

- Component tests for Values table and dialogs
- Mock API success/error paths

### 3.4: Labels Editor UI 🟧 **PLANNED**

**User Story**: As an operator supporting Japanese UI, I need to manage per-language labels so that pickers display localized text without changing stored codes.

**Requirements**:

- MVP: labels section inside value create/edit dialog (add language rows)
- Fields: language, label, description, preferred
- Prevent empty labels; require at least one preferred language when any labels exist
- Phase stretch: optional matrix view deferred if time-boxed (document as Phase 5 enhancement if not shipped)

**Acceptance Criteria**:

- [ ] Can set EN and JA labels on `eu-01` from UI
- [ ] Values table preview shows JA when preview language is JA
- [ ] Removing last label falls back to code in preview
- [ ] Component tests for multi-language rows

**Dependencies**: F3.3, F1.3, F2.2

**Testing Requirements**:

- Component tests for label row add/remove and preferred flag

### 3.5: Overrides Tab and Effective Preview 🟧 **PLANNED**

**User Story**: As an account admin (or superadmin acting for an account), I need to hide/default shared values and preview the effective list so that I trust multi-tenant customization without data copies.

**Requirements**:

- Overrides tab: table of system (and extension) values with Visible toggle, Default radio/star, optional sort override
- Superadmin: account selector to manage another account’s overrides
- Account admin: fixed to own account
- Effective preview panel: account + language → resulting codes/labels
- Educational callout: shared values defined once; overrides are deltas; new system values appear for all accounts unless hidden

**Acceptance Criteria**:

- [ ] Hiding `us-01` for account A updates effective preview for A only
- [ ] Setting default marks exactly one default
- [ ] Clear override restores visibility
- [ ] Callout text visible on tab
- [ ] Component/integration tests with mocked effective API

**Dependencies**: F2.4, F3.1

**Testing Requirements**:

- Component tests for hide/default interactions
- Preview panel tests for language switch

### 3.6: Role Gating, Empty States, and UX Polish 🟧 **PLANNED**

**User Story**: As any admin user, I need clear permissions and guidance so that I do not misuse system dictionaries or get stuck on empty data.

**Requirements**:

- Consistent 403 handling and disabled actions with tooltips
- Empty states for no codelists, no values, no overrides
- Loading skeletons matching Admin UI patterns
- Accessibility: labels on controls, keyboard reachable dialogs
- Help text explaining submission code vs label (CDISC-inspired stability)

**Acceptance Criteria**:

- [ ] Non-privileged actions disabled or hidden appropriately
- [ ] Empty states render with primary CTA
- [ ] Submission-code helper text present on value form
- [ ] Basic a11y checks for dialogs (focus trap via existing dialog component)

**Dependencies**: F3.1–F3.5

**Testing Requirements**:

- Snapshot/component tests for empty states
- Manual a11y pass checklist documented

## Phase 3 Definition of Done 🟧 **PLANNED**

- [ ] Codelists workspace usable end-to-end for system `regions`
- [ ] Superadmin can manage values/labels without API client
- [ ] Account override hide + effective preview works in UI
- [ ] UI unit tests pass; lint/typecheck clean
- [ ] Stakeholder demo of Admin UI managing shared regions

---

## Phase 4: Product Integration and Control-Plane Cutover 🟧 **PLANNED**

**Duration**: 2–4 weeks  
**Goal**: Wire codelists into Cloud control plane / console and **hard-remove** per-account region fan-out as a breaking cutover (no dual SoT).

**Overview**: Phase 4 switches control-plane consumers to the effective codelist API, validates project create against effective membership, rewrites seed/runbooks, and **deletes** collection-based region catalog paths. Breaking changes are explicit and acceptable; do not preserve legacy fan-out or dual validation.

### 4.1: Control-Plane Seed and Schema Docs Cutover 🟧 **PLANNED**

**User Story**: As a control-plane operator, I need seed scripts and docs that treat `regions` as a system codelist only so that onboarding never uses account fan-out for catalog rows.

**Requirements**:

- Update `control-plane` docs (`SCHEMA.md`, `RUNBOOK.md`, `README.md`) to describe codelist-backed regions only
- **Remove** region fan-out from `scripts/seed.mjs` (no `--account` region copy; no dual path)
- Remove or stop creating the control-plane `regions` **collection** as catalog SoT if it exists solely for dimensions (orgs/projects/envs collections remain)
- Bootstrap of system codelist is the only setup path for region catalog
- Delete obsolete fan-out helpers, comments, and “legacy collection” notes—do not document a fallback

**Acceptance Criteria**:

- [ ] Runbook documents setup without per-account region insert
- [ ] Seed path has **no** region fan-out code path
- [ ] Docs state effective codelist is the **only** SoT for region catalog
- [ ] Isolation verify script does not assume or perform fan-out

**Dependencies**: F1.6, F2.1

**Testing Requirements**:

- Manual/automated setup path on clean instance
- `verify-isolation` updated expectations pass without fan-out

### 4.2: Cloud Console Region Picker Integration 🟧 **PLANNED**

**User Story**: As a Cloud user creating a project, I need the region dropdown to load effective codelist values so that I see available regions without tenant-local copies.

**Requirements**:

- Replace collection-based region loading (`lib/control-plane/regions.ts` or equivalent) with codelist effective API client call
- Display localized label when language available; store `code` on project
- Empty state if no effective regions
- Handle API errors with existing console error patterns

**Acceptance Criteria**:

- [ ] Create Project page lists `eu-01` from codelist API
- [ ] Project stores region code string (not label)
- [ ] Two accounts without fan-out both see system regions
- [ ] Account with hidden region does not see it
- [ ] Console unit tests updated/mocks pass

**Dependencies**: F2.1, F2.4, F4.1

**Testing Requirements**:

- Console unit tests for region loader
- Manual E2E: register account → create project without seed fan-out

### 4.3: Server-Side Project Region Validation via Codelist 🟧 **PLANNED**

**User Story**: As a platform, I need project create validation to use effective codelist membership so that clients cannot bypass the catalog with arbitrary region strings.

**Requirements**:

- **Replace** hard-coded region allowlists / collection-based catalog checks with `assert_in_codelist` (or equivalent) as the sole membership check
- No dual validation (do not keep old create_rule allowlist “and also” codelist)
- Server enforcement required for project create (not Console-only)
- Invalid region returns clear 400 error

**Acceptance Criteria**:

- [ ] Creating project with unknown region fails server-side
- [ ] Creating with effective `eu-01` succeeds
- [ ] Hidden region for account fails for that account
- [ ] No remaining hard-coded dual path for region membership
- [ ] Tests cover allow/deny

**Dependencies**: F2.5, F4.2

**Testing Requirements**:

- Integration tests for create project validation
- Negative tests for hidden/unknown codes

### 4.4: Remove Collection Fan-Out Path (Breaking) 🟧 **PLANNED**

**User Story**: As a maintainer, I need the fan-out seeding path **deleted** so that engineers cannot reintroduce per-account dimension copies.

**Requirements**:

- **Remove** control-plane `regions` collection definition/seed/fan-out code if it was only a catalog (breaking; no legacy mode)
- Remove `--account` region fan-out from scripts and isolation helpers
- Update isolation tests so catalog readability is via codelist API only
- Do not keep “ignore historical per-account rows” dual readers—product code must not query a regions collection for catalog
- Changelog entry: **breaking change** for control-plane and SnackBase consumers of collection-based regions

**Acceptance Criteria**:

- [ ] No docs instruct `seed --account` for regions
- [ ] No fan-out implementation remains in control-plane scripts
- [ ] CI/setup scripts green without fan-out
- [ ] Changelog explicitly labels breaking removal
- [ ] No production code path reads tenant-local region collection rows for picker/validation

**Dependencies**: F4.1, F4.2, F4.3

**Testing Requirements**:

- Full control-plane setup + console create project smoke
- Regression: org/project/env isolation still holds

### 4.5: SDK Client Surface for Codelists 🟧 **PLANNED**

**User Story**: As a TypeScript developer, I need SDK methods for effective codelist reads so that apps integrate without hand-written HTTP.

**Requirements**:

- Add `@snackbase/sdk` service methods: list codelists, get codelist, get effective values, (admin) manage if consistent with SDK scope
- Types for value DTO and query params
- Unit tests with mocked HTTP
- Docs snippet in SDK mdx if present in monorepo

**Acceptance Criteria**:

- [ ] `client.codelists.getValues('regions', { lang: 'en' })` returns data
- [ ] Types compile in SDK package
- [ ] Unit tests pass
- [ ] README/docs mention codelists

**Dependencies**: F2.1

**Testing Requirements**:

- SDK unit tests for service methods
- Typecheck package

### 4.6: Optional Field Option `codelist` (Stretch) 🟧 **PLANNED**

**User Story**: As a collection designer, I need a field option linking a text field to a codelist so that generic record validation can enforce dictionaries.

**Requirements**:

- Optional field schema option: `"codelist": "regions"`
- On create/update record validation, if option present, assert membership via effective list for record account
- Admin Schema UI indicator (read-only badge or select) if low-cost; otherwise API-only for stretch
- If not completed, move explicitly to Phase 5 open work—do not block Phase 4 DoD

**Acceptance Criteria**:

- [ ] (If shipped) invalid code rejected on record create
- [ ] (If shipped) valid effective code accepted
- [ ] (If deferred) Phase 5 feature references this item

**Dependencies**: F2.5

**Testing Requirements**:

- Record validation unit/integration tests if shipped

## Phase 4 Definition of Done 🟧 **PLANNED**

- [ ] Cloud Console uses effective codelist for regions
- [ ] New accounts do not require region fan-out seed
- [ ] Server-side validation prevents arbitrary region codes
- [ ] Fan-out path **removed** (not merely deprecated)
- [ ] SDK read API available (or explicitly deferred with issue link)
- [ ] Stakeholder demo: two new accounts create projects with shared regions, no per-account seed

---

## Phase 5: Hardening, Advanced Features, and Launch Readiness 🟧 **PLANNED**

**Duration**: 2–4 weeks  
**Goal**: Production-harden codelists with security tests, performance checks, import/export, and operational documentation.

**Overview**: Phase 5 closes gaps: cross-tenant security suite, performance of effective resolution, optional import of terminology packages, usage guidance, and full documentation. Prepares for broader adoption beyond Cloud regions (countries, statuses, app-specific enums).

### 5.1: Security and Isolation Test Suite 🟧 **PLANNED**

**User Story**: As a security-conscious platform owner, I need automated isolation tests so that codelist APIs cannot leak private lists or overrides across accounts.

**Requirements**:

- Integration suite: private list isolation, extension isolation, override isolation, superadmin-only system mutations
- Attempt malicious `account_id` injection on effective and override endpoints
- Ensure non-superadmin cannot elevate to system scope
- Align with existing account isolation test style in SnackBase

**Acceptance Criteria**:

- [ ] Full isolation suite green in CI
- [ ] No cross-account private value leakage
- [ ] System mutation forbidden for account admin
- [ ] Report or checklist attached to PR

**Dependencies**: F2.1–F2.4

**Testing Requirements**:

- Dedicated `test_codelist_isolation.py` (or equivalent) integration module
- Negative authz cases

### 5.2: Performance and Indexing 🟧 **PLANNED**

**User Story**: As an operator of a large multi-tenant instance, I need effective resolution to stay fast so that pickers remain responsive.

**Requirements**:

- Verify indexes on `(codelist_id)`, `(account_id)`, `(codelist_id, code, account_id)`, override `(account_id, value_id)`
- Benchmark effective resolution for a codelist with ≥500 values and ≥1000 overrides (dev benchmark acceptable)
- Target: effective list p95 < 100ms on typical dev/staging hardware for 500 values (document environment)
- Avoid N+1 label queries (join or batch load)

**Acceptance Criteria**:

- [ ] Indexes present in migration
- [ ] Benchmark notes recorded in PR or docs
- [ ] No N+1 in service implementation (query plan or code review)
- [ ] Load test or unit-level batch fetch verification

**Dependencies**: F1.5, F2.1

**Testing Requirements**:

- Performance benchmark script or pytest benchmark optional
- Query count assertion in service test if feasible

### 5.3: Import / Export of Codelist Packages 🟧 **PLANNED**

**User Story**: As a superadmin, I need to export and import codelist JSON packages so that environments can be promoted and external CT can be loaded later.

**Requirements**:

- Export: codelist + values + labels (system package)
- Import: idempotent upsert by `code` within system scope
- Validate package schema; reject partial corrupt files
- Admin UI button for export/import (superadmin)
- Document mapping notes for future CDISC CT column import (external_code, submission value, definition)

**Acceptance Criteria**:

- [ ] Export produces versioned JSON
- [ ] Import on second environment recreates `regions` values/labels
- [ ] Invalid package rejected with clear error
- [ ] UI triggers download/upload for superadmin

**Dependencies**: F2.2, F3.3

**Testing Requirements**:

- Round-trip import/export tests
- UI smoke for export download

### 5.4: Historical Validity and Soft-Retire Semantics 🟧 **PLANNED**

**User Story**: As an application storing historical records, I need retired codes to remain resolvable for display so that old projects still show region labels.

**Requirements**:

- Document semantics: inactive values excluded from effective pickers; label resolution by code still available via `resolve_label(codelist, code, lang)` including inactive
- API: optional `GET .../values/{code}` resolve including inactive for display
- Admin UI shows inactive with badge
- Tests for historical display vs create-time rejection

**Acceptance Criteria**:

- [ ] Inactive `eu-01` rejected for new project create
- [ ] Label for inactive `eu-01` still resolvable for existing project display
- [ ] Docs describe semantics clearly
- [ ] Tests cover both paths

**Dependencies**: F2.5, F4.3

**Testing Requirements**:

- Unit/integration tests for inactive membership vs label resolve

### 5.5: Documentation, Runbooks, and Developer Guides 🟧 **PLANNED**

**User Story**: As a developer adopting codelists, I need concept docs and runbooks so that I use system lists, private lists, and overrides correctly.

**Requirements**:

- Mintlify/docs page: Codelists concept (system vs account, effective resolution, languages, overrides)
- Admin UI help blurb / in-app empty states finalized
- Control-plane runbook final
- API reference pages for codelist endpoints
- Note CDISC inspiration and non-goals (not full CT regulatory engine in v1)

**Acceptance Criteria**:

- [ ] Concept doc published in `docs/`
- [ ] API reference entries complete
- [ ] Runbook updated
- [ ] Link from multi-tenancy docs to codelists as shared reference data pattern

**Dependencies**: F2.6, F4.1

**Testing Requirements**:

- Docs link check (`mint broken-links` or equivalent if available)
- Editorial review checklist

### 5.6: Observability and Audit Completeness 🟧 **PLANNED**

**User Story**: As an operator, I need audits and logs for codelist mutations so that dictionary changes are traceable.

**Requirements**:

- Audit log entries for create/update/deactivate of system codelists/values and override changes (if audit system supports resource types)
- Structured logs on effective resolution errors
- Metrics optional: counters for effective reads / override hits (if metrics infrastructure exists; else log-only)

**Acceptance Criteria**:

- [ ] Mutating system value produces audit entry when audit enabled
- [ ] Override hide produces audit or structured log
- [ ] Failure paths log enough context (codelist code, account id) without PII leakage

**Dependencies**: F2.2, F2.4

**Testing Requirements**:

- Tests with audit hooks enabled if project has pattern (`pytest -m enable_audit_hooks`)
- Log assertion tests where applicable

## Phase 5 Definition of Done 🟧 **PLANNED**

- [ ] Security isolation suite green
- [ ] Performance notes and indexes verified
- [ ] Import/export available for superadmin
- [ ] Historical inactive semantics documented and tested
- [ ] Docs and runbooks complete
- [ ] Audit/logging wired for mutations
- [ ] Launch readiness review completed

---

# Overall Project Definition of Done

## Requirements Met

- [ ] First-class codelist subsystem exists (not tenant collection fan-out)
- [ ] System-shared codelists available to all accounts via effective API
- [ ] Account-private codelists supported
- [ ] Per-account hide/default overrides without duplicating master values
- [ ] Multi-language labels (at least EN + JA path) on values
- [ ] Stable submission `code` stored in business data; labels resolved at read time
- [ ] Admin UI workspace to manage codelists, values, labels, overrides
- [ ] Cloud control plane / console uses codelists for regions; collection fan-out **removed** (breaking)
- [ ] Server-side validation prevents invalid region codes
- [ ] Documentation covers concepts, API, and operations; no legacy dual-path docs

## Quality Gates

- [ ] Unit test coverage for domain service effective resolution ≥ 80% on new modules
- [ ] Integration tests for API authz and cross-account isolation pass
- [ ] Admin UI lint, typecheck, and component tests pass
- [ ] Control-plane setup + console create-project smoke pass without region fan-out
- [ ] Security review of isolation model completed
- [ ] No regression in existing multi-tenant collection isolation

## Documentation Deliverables

- [ ] This PRD maintained as source of phased delivery
- [ ] Concept doc: Codelists / controlled dictionaries
- [ ] API reference for codelist endpoints
- [ ] Admin UI usage notes (empty states + code vs label)
- [ ] Control-plane runbook with codelist-only catalog setup (no fan-out)
- [ ] Changelog entries for SnackBase and control-plane (**breaking**)

## Success Metrics

- [ ] Zero per-account inserts required when adding a new system region
- [ ] New customer account can create a project selecting `eu-01` without running `seed --account`
- [ ] Effective values API p95 < 100ms for ≤500 values on staging-class hardware
- [ ] Cross-account isolation tests: 0 known leaks for private lists/overrides
- [ ] Operators can fully manage `regions` from Admin UI without SQL or ad-hoc scripts
- [ ] Zero remaining production readers of a tenant `regions` collection for catalog

---

## Version History

| Version | Date       | Changes |
| ------- | ---------- | ------- |
| 1.0     | 2026-07-25 | Initial PRD: CDISC-inspired first-class codelists, effective resolution, Admin UI workspace, control-plane cutover |
| 1.1     | 2026-07-25 | Compatibility policy: no backward compatibility; breaking cutover; hard-remove fan-out/dual SoT |

---

## Assumptions

1. Codelists are **core system tables**, not user-created collections under normal `account_id` record isolation.
2. System account id remains `00000000-0000-0000-0000-000000000000` (`SY0000`).
3. Business data (e.g. `projects.region`) stores the **submission code string**, not label text and not necessarily value UUID.
4. MVP default language is `en`; JA labels are supported by the model even if not all seed rows include JA on day one.
5. MVP `regions` list is **not extensible** by accounts; private extension of shared lists is supported by the model but optional per list flag.
6. Account admin role is the minimum role for private list mutation and overrides; finer RBAC can come later.
7. Full CDISC CT package import, context bindings, and regulatory version pinning are **non-goals for v1** beyond schema hooks (`external_code`, `version`).
8. Control-plane collections for organizations/projects/environments remain tenant collections; the **region catalog** moves to codelists and the old catalog path is **removed**.
9. Admin UI is the primary management surface; Cloud Console is primarily a consumer of effective values.
10. **No backward compatibility** for control-plane region catalog: breaking changes to seeds, scripts, Console loaders, and any collection-based region APIs are acceptable.
11. Existing environments may need a one-time re-seed/bootstrap of system codelists after upgrade; no long-lived dual-read migration layer is required.
12. Field option `codelist` and rule macro `@in_codelist` may partially slip to post-Phase-4 without blocking Cloud region cutover (feature scope, not compatibility).

## Risks and Mitigations

1. **Risk**: Engineers reintroduce shared dims as collections.  
   **Mitigation**: Hard-delete fan-out code; docs + Admin empty states; code review checklist.

2. **Risk**: Renaming submission codes breaks stored data.  
   **Mitigation**: Immutable code after create; soft-retire; label-only edits encouraged. (This is product data stability, not API backward-compat.)

3. **Risk**: Effective resolution N+1 or slow joins.  
   **Mitigation**: Batch label load; indexes; Phase 5 benchmark.

4. **Risk**: Call sites break when collection `regions` is removed.  
   **Mitigation**: Acceptable—update Console, seeds, tests, and docs in the same Phase 4 delivery; no compatibility shim.

5. **Risk**: Overbuilding CDISC fidelity delays Cloud value.  
   **Mitigation**: Phases 1–4 prioritize regions cutover; CT import is Phase 5.

6. **Risk**: Account extensions collide semantically with system codes.  
   **Mitigation**: Uniqueness on `(codelist_id, code, account_id)`; effective merge prefers clear scope badges; non-extensible default for platform lists.

## Open Questions

1. Should account-owned codelists with the same `code` as a system list shadow the system list, or be forbidden?
2. Should overrides allow per-account label overrides in v1, or only visibility/default/sort?
3. Is `is_extensible=true` required for any Cloud MVP list, or only future app enums?
4. Should effective API be available to non-admin authenticated users by default (recommended: yes for pickers)?
5. Do we need superadmin API keys (already planned elsewhere) as the preferred automation path for CT bootstrap in CI?
6. Timeline priority: Admin UI (Phase 3) before Console cutover (Phase 4), or thin API-only cutover first if Cloud urgency is higher?
