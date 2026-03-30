# E2E Tests — SnackBase Admin UI

Playwright-based end-to-end tests that verify critical user flows in a real browser against the running application.

## Prerequisites

1. **Backend running** at `http://localhost:8000`:
   ```bash
   cd /path/to/snackBase
   uv run python -m snackbase serve
   ```

2. **Superadmin exists** (one-time setup):
   ```bash
   uv run python -m snackbase create-superadmin
   ```
   Default credentials used by the tests: `admin@admin.com` / `Admin@123456`

3. **Node dependencies installed** (from `ui/`):
   ```bash
   npm install
   npx playwright install chromium
   ```

## Running Tests

```bash
# From ui/
npm run test:e2e               # Run all E2E tests (headless)
npm run test:e2e:ui            # Run with Playwright UI (interactive)
npm run test:e2e:report        # Open last HTML report
```

The Vite dev server starts automatically before tests run (via `webServer` in `playwright.config.ts`). If a dev server is already running on port 5173 it will be reused.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `E2E_BACKEND_URL` | `http://localhost:8000` | SnackBase backend URL |
| `E2E_SUPERADMIN_EMAIL` | `admin@admin.com` | Superadmin login email |
| `E2E_SUPERADMIN_PASSWORD` | `Admin@123456` | Superadmin login password |

Override via shell or a `.env.e2e` file:
```bash
E2E_BACKEND_URL=http://localhost:9000 npm run test:e2e
```

## Test Suites

| File | PRD Ref | What it covers |
|------|---------|----------------|
| `tests/smoke.test.ts` | — | Playwright setup sanity check (no backend needed) |
| `tests/auth.test.ts` | FT4.2 | Login, logout, protected route redirects, session persistence |
| `tests/collections.test.ts` | FT4.3 | Collection + record full CRUD lifecycle |
| `tests/user-management.test.ts` | FT4.4 | Accounts, users, roles, invitations |
| `tests/navigation.test.ts` | FT4.5 | Sidebar nav, console errors, page titles, mobile sidebar, back/forward |

## Global Setup & Teardown

`global-setup.ts` runs once before all tests:
- Authenticates as superadmin
- Creates a dedicated test account (`e2e-test-account`)
- Creates a test collection (`e2e_test_items`)
- Writes state to `e2e/.e2e-state.json` for teardown

`global-teardown.ts` runs once after all tests:
- Deletes the test collection and test account
- Removes `e2e/.e2e-state.json`

Individual test suites (`collections.test.ts`, `user-management.test.ts`) manage their own test data independently and clean up via `beforeAll`/`afterAll` hooks.

## Page Object Model

Reusable page objects live in `e2e/pages/`:

```
BasePage.ts         — base class with shared navigation helpers
LoginPage.ts        — login form interactions
DashboardPage.ts    — dashboard page
CollectionsPage.ts  — collections list (create, delete, open records)
RecordsPage.ts      — records list (create, edit, delete)
AccountsPage.ts     — accounts list (create, delete)
UsersPage.ts        — users list (create, edit role)
RolesPage.ts        — roles list (create)
InvitationsPage.ts  — invitations list (send, cancel)
```

Custom fixtures (authenticated page, pre-instantiated page objects) are defined in `e2e/fixtures.ts`.

## CI

Tests run with `retries: 2` in CI. Artifacts (`test-results/`, `playwright-report/`) are excluded from git via `.gitignore`.

To run in CI without a pre-existing dev server:
```bash
CI=true npm run test:e2e
```
