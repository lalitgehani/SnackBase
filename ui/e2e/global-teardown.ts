/**
 * Playwright Global Teardown
 *
 * Runs once after all E2E tests. Removes the test data created in global-setup
 * so the backend stays clean between runs.
 */

import { request } from '@playwright/test'
import { existsSync, readFileSync, unlinkSync } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import type { E2EState } from './global-setup.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://localhost:8000'
const STATE_FILE = path.join(__dirname, '.e2e-state.json')

export default async function globalTeardown() {
  if (!existsSync(STATE_FILE)) {
    console.warn('E2E teardown: state file not found, skipping cleanup.')
    return
  }

  const state: E2EState = JSON.parse(readFileSync(STATE_FILE, 'utf-8'))
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  const authHeaders = { Authorization: `Bearer ${state.superadminToken}` }

  // ── 1. Delete test collection ─────────────────────────────────────────────
  const collectionRes = await ctx.delete(
    `/api/v1/collections/${state.testCollectionName}`,
    { headers: authHeaders },
  )
  if (!collectionRes.ok() && collectionRes.status() !== 404) {
    console.warn(
      `E2E teardown: failed to delete collection "${state.testCollectionName}" (${collectionRes.status()})`,
    )
  }

  // ── 2. Delete test account ────────────────────────────────────────────────
  const accountRes = await ctx.delete(
    `/api/v1/accounts/${state.testAccountId}`,
    { headers: authHeaders },
  )
  if (!accountRes.ok() && accountRes.status() !== 404) {
    console.warn(
      `E2E teardown: failed to delete account "${state.testAccountId}" (${accountRes.status()})`,
    )
  }

  // ── 3. Clean up state file ────────────────────────────────────────────────
  unlinkSync(STATE_FILE)

  await ctx.dispose()

  console.log('✔ E2E teardown complete — test data removed.')
}
