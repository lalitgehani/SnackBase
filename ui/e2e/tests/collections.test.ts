/**
 * FT4.3: Collection & Record Management E2E Flow
 *
 * Verifies the complete data management workflow — creating a collection,
 * browsing its records page, and performing full CRUD on records — in a real
 * browser against the running application.
 *
 * Prerequisites:
 *   - SnackBase backend running at http://localhost:8000
 *   - Superadmin exists: `uv run python -m snackbase create-superadmin`
 *   - Global setup has seeded a test account (e2e-test-account)
 *   - Run tests with: npm run test:e2e
 *
 * Test order (describe.serial — each test depends on the previous):
 *   1. Create collection with schema
 *   2. Collection appears in list
 *   3. Navigate to records page
 *   4. Create a record
 *   5. Record appears in list
 *   6. Edit a record
 *   7. Delete a record
 *   8. Delete the collection (cleanup)
 */

import { request } from '@playwright/test'
import { test, expect } from '../fixtures.js'

// ── Test constants ─────────────────────────────────────────────────────────────

/** Unique collection name for this test suite. */
const COLLECTION_NAME = 'e2e_ft43_items'

/** Schema field used in all record operations. */
const FIELD_NAME = 'title'

/** Initial record value used in create / verify tests. */
const RECORD_INITIAL = 'E2E Record Title'

/** Updated value used in the edit test. */
const RECORD_UPDATED = 'E2E Updated Title'

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

/** Best-effort API cleanup — remove the test collection if it still exists. */
async function cleanupCollection(token: string) {
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  await ctx.delete(`/api/v1/collections/${COLLECTION_NAME}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  await ctx.dispose()
}

// ── Test suite ─────────────────────────────────────────────────────────────────

test.describe.serial('FT4.3: Collection & Record Management E2E Flow', () => {
  // Remove any leftover collection from a previous failed run before the suite
  // starts, and again after it completes for best-effort cleanup.
  test.beforeAll(async () => {
    try {
      const token = await getSuperadminToken()
      await cleanupCollection(token)
    } catch {
      // Ignore — collection may not exist yet or backend may be warming up.
    }
  })

  test.afterAll(async () => {
    try {
      const token = await getSuperadminToken()
      await cleanupCollection(token)
    } catch {
      // Best-effort: do not fail the suite on cleanup errors.
    }
  })

  // ── 1. Create collection ───────────────────────────────────────────────────

  test('superadmin can create a new collection with schema fields', async ({
    page,
    authenticatedPage,
    collectionsPage,
  }) => {
    await collectionsPage.navigate()

    await collectionsPage.createCollection(COLLECTION_NAME, [
      { name: FIELD_NAME, type: 'text' },
    ])

    // The dialog should have closed and the page is ready
    await expect(page).toHaveURL(/\/admin\/collections$/)
  })

  // ── 2. Collection appears in list ──────────────────────────────────────────

  test('created collection appears in the collections list', async ({
    authenticatedPage,
    collectionsPage,
  }) => {
    await collectionsPage.navigate()

    // Wait for table to load and verify the new collection is present
    const row = collectionsPage.rowByName(COLLECTION_NAME)
    await expect(row).toBeVisible({ timeout: 10_000 })
    await expect(row).toContainText(COLLECTION_NAME)
  })

  // ── 3. Navigate to records page ────────────────────────────────────────────

  test('user can navigate to the collection records page', async ({
    page,
    authenticatedPage,
    collectionsPage,
    recordsPage,
  }) => {
    await collectionsPage.navigate()

    // Click "Manage records" (Database icon) on the collection row
    await collectionsPage.openManageRecords(COLLECTION_NAME)

    await expect(page).toHaveURL(
      new RegExp(`/admin/collections/${COLLECTION_NAME}/records`),
    )

    // The page heading should show the collection name
    const rp = recordsPage(COLLECTION_NAME)
    await expect(rp.heading()).toBeVisible({ timeout: 10_000 })
  })

  // ── 4. Create a record ─────────────────────────────────────────────────────

  test('user can create a record with valid data', async ({
    page,
    authenticatedPage,
    recordsPage,
  }) => {
    const rp = recordsPage(COLLECTION_NAME)
    await rp.navigate()

    // Empty state should be visible before any record exists
    await expect(rp.emptyState()).toBeVisible({ timeout: 10_000 })

    // Open Create Record dialog and fill the form
    await rp.openCreateDialog()
    await rp.submitCreateDialog(
      { [FIELD_NAME]: RECORD_INITIAL },
      true, // select first account (superadmin context)
    )

    // After creation the dialog closes and we stay on the records page
    await expect(page).toHaveURL(
      new RegExp(`/admin/collections/${COLLECTION_NAME}/records`),
    )
  })

  // ── 5. Record appears in list ──────────────────────────────────────────────

  test('created record appears in the records list', async ({
    authenticatedPage,
    recordsPage,
  }) => {
    const rp = recordsPage(COLLECTION_NAME)
    await rp.navigate()

    // The record row containing the initial title should be visible
    const row = rp.rowByText(RECORD_INITIAL)
    await expect(row).toBeVisible({ timeout: 10_000 })
  })

  // ── 6. Edit a record ───────────────────────────────────────────────────────

  test('user can edit a record and see updated values', async ({
    authenticatedPage,
    recordsPage,
  }) => {
    const rp = recordsPage(COLLECTION_NAME)
    await rp.navigate()

    const row = rp.rowByText(RECORD_INITIAL)
    await expect(row).toBeVisible({ timeout: 10_000 })

    // Edit the record — update the title field
    await rp.editRecord(row, { [FIELD_NAME]: RECORD_UPDATED })

    // The updated value should now appear in the table
    const updatedRow = rp.rowByText(RECORD_UPDATED)
    await expect(updatedRow).toBeVisible({ timeout: 10_000 })

    // The old value should no longer be present
    await expect(rp.rowByText(RECORD_INITIAL)).toHaveCount(0)
  })

  // ── 7. Delete a record ─────────────────────────────────────────────────────

  test('user can delete a record with confirmation', async ({
    authenticatedPage,
    recordsPage,
  }) => {
    const rp = recordsPage(COLLECTION_NAME)
    await rp.navigate()

    const row = rp.rowByText(RECORD_UPDATED)
    await expect(row).toBeVisible({ timeout: 10_000 })

    // Delete the record via the confirmation dialog
    await rp.deleteRecord(row)

    // Empty state should reappear (no more records)
    await expect(rp.emptyState()).toBeVisible({ timeout: 10_000 })
  })

  // ── 8. Delete the collection ───────────────────────────────────────────────

  test('user can delete the collection (cleanup)', async ({
    page,
    authenticatedPage,
    collectionsPage,
  }) => {
    await collectionsPage.navigate()

    // Verify collection is still in the list
    const row = collectionsPage.rowByName(COLLECTION_NAME)
    await expect(row).toBeVisible({ timeout: 10_000 })

    // Delete via the confirmation dialog (requires typing the collection name)
    await collectionsPage.deleteCollection(COLLECTION_NAME)

    // Collection should no longer appear in the list
    await expect(collectionsPage.rowByName(COLLECTION_NAME)).toHaveCount(0)

    // Still on the collections page
    await expect(page).toHaveURL(/\/admin\/collections$/)
  })
})
