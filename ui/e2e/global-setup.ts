/**
 * Playwright Global Setup
 *
 * Runs once before all E2E tests. Seeds test data in the running SnackBase
 * backend (http://localhost:8000) so tests have a known starting state.
 *
 * Prerequisites:
 *   - Backend must be running: uv run python -m snackbase serve
 *   - A superadmin must already exist: uv run python -m snackbase create-superadmin
 *
 * Environment variables consumed:
 *   E2E_SUPERADMIN_EMAIL    (default: admin@admin.com)
 *   E2E_SUPERADMIN_PASSWORD (default: Admin@123456)
 *   E2E_BACKEND_URL         (default: http://localhost:8000)
 */

import { request } from '@playwright/test'
import { writeFileSync } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://localhost:8000'
const SUPERADMIN_EMAIL = process.env.E2E_SUPERADMIN_EMAIL ?? 'admin@admin.com'
const SUPERADMIN_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD ?? 'Admin@123456'
// Superadmin belongs to the system account (ID format: SY0000)
const SYSTEM_ACCOUNT_ID = 'SY0000'

/** Shared state file written by setup and read by teardown */
const STATE_FILE = path.join(__dirname, '.e2e-state.json')

export interface E2EState {
  superadminToken: string
  testAccountId: string
  testAccountSlug: string
  testCollectionName: string
}

export default async function globalSetup() {
  const ctx = await request.newContext({ baseURL: BACKEND_URL })

  // ── 1. Authenticate as superadmin ────────────────────────────────────────
  const loginRes = await ctx.post('/api/v1/auth/login', {
    data: {
      account: SYSTEM_ACCOUNT_ID,
      email: SUPERADMIN_EMAIL,
      password: SUPERADMIN_PASSWORD,
    },
  })

  if (!loginRes.ok()) {
    const body = await loginRes.text()
    throw new Error(
      `E2E setup: superadmin login failed (${loginRes.status()}): ${body}\n` +
        'Make sure the backend is running and a superadmin exists.',
    )
  }

  const { token: superadminToken } = await loginRes.json()

  const authHeaders = { Authorization: `Bearer ${superadminToken}` }

  // ── 2. Create a dedicated test account ────────────────────────────────────
  const accountRes = await ctx.post('/api/v1/accounts/', {
    headers: authHeaders,
    data: {
      name: 'E2E Test Account',
      slug: 'e2e-test-account',
    },
  })

  if (!accountRes.ok()) {
    const body = await accountRes.text()
    throw new Error(`E2E setup: failed to create test account (${accountRes.status()}): ${body}`)
  }

  const testAccount = await accountRes.json()

  // ── 3. Create a test collection ───────────────────────────────────────────
  const collectionName = 'e2e_test_items'
  const collectionRes = await ctx.post('/api/v1/collections/', {
    headers: authHeaders,
    data: {
      name: collectionName,
      fields: [
        { name: 'title', type: 'text', required: true },
        { name: 'active', type: 'boolean', required: false },
      ],
    },
  })

  if (!collectionRes.ok()) {
    // Collection might already exist from a previous failed run — that's OK.
    const body = await collectionRes.text()
    console.warn(`E2E setup: collection creation returned ${collectionRes.status()}: ${body}`)
  }

  // ── 4. Persist state for teardown ─────────────────────────────────────────
  const state: E2EState = {
    superadminToken,
    testAccountId: testAccount.id,
    testAccountSlug: testAccount.slug,
    testCollectionName: collectionName,
  }

  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2))

  await ctx.dispose()

  console.log(
    `✔ E2E setup complete — test account: ${testAccount.slug} (${testAccount.id})`,
  )
}
