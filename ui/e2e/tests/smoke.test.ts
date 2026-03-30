/**
 * Smoke test — verifies that the Playwright setup works end-to-end:
 *   - The Vite dev server starts
 *   - The app loads at the base URL
 *   - The login page is reachable
 *
 * This test does NOT require a running backend.
 */

import { test, expect } from '../fixtures.js'

test.describe('Playwright smoke test', () => {
  test('app loads and redirects unauthenticated users to login', async ({ page }) => {
    await page.goto('/')
    // The app redirects unauthenticated requests to /admin/login
    await page.waitForURL('**/admin/**')
    await expect(page).toHaveURL(/admin/)
  })

  test('login page renders', async ({ loginPage }) => {
    await loginPage.navigate()
    await expect(loginPage.emailInput()).toBeVisible()
    await expect(loginPage.passwordInput()).toBeVisible()
    await expect(loginPage.submitButton()).toBeVisible()
  })
})
