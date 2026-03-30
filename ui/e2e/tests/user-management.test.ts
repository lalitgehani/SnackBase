/**
 * FT4.4: User Management E2E Flow
 *
 * Verifies the complete user management workflow — creating accounts, users,
 * roles, and invitations — end-to-end in a real browser against the running
 * application.
 *
 * Prerequisites:
 *   - SnackBase backend running at http://localhost:8000
 *   - Superadmin exists: `uv run python -m snackbase create-superadmin`
 *   - Global setup has completed (seeds test account)
 *   - Run tests with: npm run test:e2e
 *
 * Test order (describe.serial — each test depends on the previous):
 *   1. Create a new account
 *   2. Create a user in that account
 *   3. Create a role and assign it to the user
 *   4. Send an invitation
 *   5. Invitation appears in invitations list
 *   6. Cancel the invitation
 *   7. Delete the test account (cleanup)
 */

import { request } from '@playwright/test'
import { test, expect } from '../fixtures.js'

// ── Test constants ─────────────────────────────────────────────────────────────

const ACCOUNT_NAME = 'E2E FT44 Account'
const ACCOUNT_SLUG = 'e2e-ft44-account'

/** User to create inside the test account. */
const USER_EMAIL = 'e2e-ft44-user@test.example'

/**
 * Password that satisfies the complexity rules:
 *   - At least 12 characters
 *   - Uppercase, lowercase, digit, special character
 */
const USER_PASSWORD = 'TestFt44@User!'

/** Role to create and assign to the test user. */
const ROLE_NAME = 'e2e_ft44_editor'

/** Email address used for the invitation test. */
const INVITE_EMAIL = 'e2e-ft44-invite@test.example'

const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://localhost:8000'
const SUPERADMIN_EMAIL = process.env.E2E_SUPERADMIN_EMAIL ?? 'admin@admin.com'
const SUPERADMIN_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD ?? 'Admin@123456'
const SYSTEM_ACCOUNT_ID = 'SY0000'

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Authenticate and return a superadmin bearer token via the API. */
async function getSuperadminToken(): Promise<string> {
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  const res = await ctx.post('/api/v1/auth/login', {
    data: {
      account: SYSTEM_ACCOUNT_ID,
      email: SUPERADMIN_EMAIL,
      password: SUPERADMIN_PASSWORD,
    },
  })
  const body = await res.json()
  await ctx.dispose()
  return body.token as string
}

/** Best-effort API cleanup — remove the test account if it still exists. */
async function cleanupTestAccount(token: string) {
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  const authHeaders = { Authorization: `Bearer ${token}` }

  // List accounts and find the test account by slug
  const listRes = await ctx.get('/api/v1/accounts/', {
    headers: authHeaders,
    params: { page_size: 200 },
  })

  if (listRes.ok()) {
    const body = await listRes.json()
    const account = (body.items ?? []).find(
      (a: { slug: string }) => a.slug === ACCOUNT_SLUG,
    )
    if (account) {
      await ctx.delete(`/api/v1/accounts/${account.id}`, {
        headers: authHeaders,
      })
    }
  }

  await ctx.dispose()
}

/** Best-effort API cleanup — remove the test role if it still exists. */
async function cleanupTestRole(token: string) {
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  const authHeaders = { Authorization: `Bearer ${token}` }

  const listRes = await ctx.get('/api/v1/roles/', { headers: authHeaders })

  if (listRes.ok()) {
    const body = await listRes.json()
    const role = (body.items ?? []).find(
      (r: { name: string }) => r.name === ROLE_NAME,
    )
    if (role) {
      await ctx.delete(`/api/v1/roles/${role.id}`, { headers: authHeaders })
    }
  }

  await ctx.dispose()
}

// ── Test suite ─────────────────────────────────────────────────────────────────

test.describe.serial('FT4.4: User Management E2E Flow', () => {
  // Best-effort pre-suite cleanup of any leftover state from a previous failed run
  test.beforeAll(async () => {
    try {
      const token = await getSuperadminToken()
      await cleanupTestAccount(token)
      await cleanupTestRole(token)
    } catch {
      // Ignore — state may not exist yet, or the backend may be warming up.
    }
  })

  // Best-effort post-suite cleanup
  test.afterAll(async () => {
    try {
      const token = await getSuperadminToken()
      await cleanupTestAccount(token)
      await cleanupTestRole(token)
    } catch {
      // Best-effort: do not fail the suite on cleanup errors.
    }
  })

  // ── 1. Create account ──────────────────────────────────────────────────────

  test('superadmin can create a new account', async ({
    page,
    authenticatedPage,
    accountsPage,
  }) => {
    await accountsPage.navigate()

    await accountsPage.createAccount(ACCOUNT_NAME, ACCOUNT_SLUG)

    // Still on the accounts page and the new account row is visible
    await expect(page).toHaveURL(/\/admin\/accounts/)
    await expect(accountsPage.rowByName(ACCOUNT_NAME)).toBeVisible({ timeout: 10_000 })
  })

  // ── 2. Create user ─────────────────────────────────────────────────────────

  test('superadmin can create a user in that account', async ({
    page,
    authenticatedPage,
    usersPage,
  }) => {
    await usersPage.navigate()

    await usersPage.createUser({
      email: USER_EMAIL,
      password: USER_PASSWORD,
      accountName: ACCOUNT_NAME,
      roleName: 'admin', // use the seeded default role for initial creation
    })

    // Still on the users page and the new user row is visible
    await expect(page).toHaveURL(/\/admin\/users/)
    await expect(usersPage.rowByEmail(USER_EMAIL)).toBeVisible({ timeout: 10_000 })
  })

  // ── 3. Create role and assign to user ──────────────────────────────────────

  test('superadmin can create and assign a role', async ({
    page,
    authenticatedPage,
    rolesPage,
    usersPage,
  }) => {
    // Step 3a: Create the new role
    await rolesPage.navigate()

    await rolesPage.createRole(ROLE_NAME, 'E2E test role for FT4.4')

    // Newly created role row should be present in the roles table
    await expect(rolesPage.rowByName(ROLE_NAME)).toBeVisible({ timeout: 10_000 })

    // Step 3b: Assign the new role to the test user
    await usersPage.navigate()

    await usersPage.editUserRole(USER_EMAIL, ROLE_NAME)

    // The user row should now show the new role name
    await expect(usersPage.rowByEmail(USER_EMAIL)).toBeVisible({ timeout: 10_000 })
    await expect(usersPage.rowByEmail(USER_EMAIL)).toContainText(ROLE_NAME)
  })

  // ── 4. Send invitation ─────────────────────────────────────────────────────

  test('superadmin can send an invitation', async ({
    page,
    authenticatedPage,
    invitationsPage,
  }) => {
    await invitationsPage.navigate()

    await invitationsPage.sendInvitation(INVITE_EMAIL, ACCOUNT_NAME)

    // Still on the invitations page
    await expect(page).toHaveURL(/\/admin\/invitations/)
  })

  // ── 5. Invitation appears in list ──────────────────────────────────────────

  test('invitation appears in the invitations list', async ({
    authenticatedPage,
    invitationsPage,
  }) => {
    await invitationsPage.navigate()

    const row = invitationsPage.rowByEmail(INVITE_EMAIL)
    await expect(row).toBeVisible({ timeout: 10_000 })

    // The invitation should start with a "Pending" status
    await expect(row).toContainText(/pending/i)
  })

  // ── 6. Cancel invitation ───────────────────────────────────────────────────

  test('superadmin can cancel an invitation', async ({
    authenticatedPage,
    invitationsPage,
  }) => {
    await invitationsPage.navigate()

    // Verify the invitation is still pending before cancelling
    const row = invitationsPage.rowByEmail(INVITE_EMAIL)
    await expect(row).toBeVisible({ timeout: 10_000 })

    await invitationsPage.cancelInvitation(INVITE_EMAIL)

    // After cancellation the invitation should either disappear (if filtered out)
    // or show a "Cancelled" status badge. Reload to get fresh state.
    await invitationsPage.navigate()

    // The cancelled invitation may still appear with a "cancelled" badge, or be
    // hidden depending on the current status filter. Either outcome is acceptable.
    // We just verify there is no pending Cancel Invitation button for that email.
    const updatedRow = invitationsPage.rowByEmail(INVITE_EMAIL)
    if (await updatedRow.isVisible()) {
      // If still visible it must be in a non-pending state (no Cancel button)
      await expect(updatedRow.getByTitle('Cancel Invitation')).toHaveCount(0)
    }
    // If the row is gone, the cancellation was successful
  })

  // ── 7. Delete test account ─────────────────────────────────────────────────

  test('superadmin can delete the test account (cleanup)', async ({
    page,
    authenticatedPage,
    accountsPage,
  }) => {
    await accountsPage.navigate()

    // Verify the account is still in the list
    const row = accountsPage.rowByName(ACCOUNT_NAME)
    await expect(row).toBeVisible({ timeout: 10_000 })

    // Delete via the confirmation dialog (requires typing the account name)
    await accountsPage.deleteAccount(ACCOUNT_NAME)

    // Account should no longer appear in the list
    await expect(accountsPage.rowByName(ACCOUNT_NAME)).toHaveCount(0)

    // Still on the accounts page
    await expect(page).toHaveURL(/\/admin\/accounts/)
  })
})
