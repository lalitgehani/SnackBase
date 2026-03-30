/**
 * FT4.2: Authentication E2E Flow
 *
 * Verifies the complete login/logout flow, session persistence, and protected
 * route redirection in a real browser against the running application.
 *
 * Prerequisites:
 *   - SnackBase backend running at http://localhost:8000
 *   - Superadmin exists: `uv run python -m snackbase create-superadmin`
 *   - Run tests with: npm run test:e2e
 */

import { test, expect } from '../fixtures.js'

test.describe('Authentication E2E Flow', () => {
  // ---------------------------------------------------------------------------
  // Login
  // ---------------------------------------------------------------------------

  test('user can log in with valid credentials and see dashboard', async ({
    loginPage,
    page,
  }) => {
    await loginPage.loginAsSuperadmin()
    await page.waitForURL('**/admin/dashboard', { timeout: 15_000 })
    await expect(page).toHaveURL(/admin\/dashboard/)
  })

  test('login with invalid credentials stays on the login page', async ({ loginPage, page }) => {
    await loginPage.navigate()
    await loginPage.login('notauser@example.com', 'wrongpassword')
    // The 401 response interceptor finds no refreshToken and redirects back to
    // /admin/login, so the user is never authenticated and stays on the login page.
    await page.waitForURL('**/admin/login', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/login/)
    await expect(loginPage.emailInput()).toBeVisible()
  })

  test('client-side validation error shown when email is missing', async ({ loginPage }) => {
    await loginPage.navigate()
    // Submit with no email — react-hook-form + Zod fires before any network call.
    // Leaving the email input empty avoids browser native constraint validation
    // (which would otherwise suppress react-hook-form's error for type="email" inputs).
    await loginPage.passwordInput().fill('somepassword')
    await loginPage.submitButton().click()
    // FieldError renders with role="alert" when Zod finds the email invalid
    await expect(loginPage.page.getByRole('alert')).toBeVisible({ timeout: 5_000 })
    await expect(loginPage.page.getByText(/invalid email address/i)).toBeVisible({ timeout: 5_000 })
  })

  // ---------------------------------------------------------------------------
  // Navigation (requires authenticated session)
  // ---------------------------------------------------------------------------

  test('logged-in user can navigate between pages', async ({ page, authenticatedPage }) => {
    // Start on dashboard after login
    await expect(page).toHaveURL(/admin\/dashboard/)

    // Navigate to accounts page
    await page.goto('/admin/accounts')
    await page.waitForURL('**/admin/accounts', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/accounts/)

    // Navigate to collections page
    await page.goto('/admin/collections')
    await page.waitForURL('**/admin/collections', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/collections/)

    // Navigate back to dashboard
    await page.goto('/admin/dashboard')
    await page.waitForURL('**/admin/dashboard', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/dashboard/)
  })

  // ---------------------------------------------------------------------------
  // Logout
  // ---------------------------------------------------------------------------

  test('logout clears session and redirects to login', async ({ page, authenticatedPage }) => {
    await expect(page).toHaveURL(/admin\/dashboard/)

    // Open the user menu in the sidebar footer and click "Log out"
    await page.locator('[data-sidebar="footer"]').getByRole('button').first().click()
    await page.getByRole('menuitem', { name: /log out/i }).click()

    // Should redirect to login page
    await page.waitForURL('**/admin/login', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/login/)

    // Auth is cleared — attempting to navigate to a protected page should redirect to login
    await page.goto('/admin/dashboard')
    await page.waitForURL('**/admin/login', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/login/)
  })

  test('logout clears auth state in localStorage', async ({ page, authenticatedPage }) => {
    // Verify we are authenticated before logout
    const beforeLogout = await page.evaluate(() => {
      const raw = localStorage.getItem('auth-storage')
      return raw ? JSON.parse(raw) : null
    })
    expect(beforeLogout?.state?.isAuthenticated).toBe(true)
    expect(beforeLogout?.state?.token).not.toBeNull()

    // Logout
    await page.locator('[data-sidebar="footer"]').getByRole('button').first().click()
    await page.getByRole('menuitem', { name: /log out/i }).click()
    await page.waitForURL('**/admin/login', { timeout: 10_000 })

    // Zustand persist re-writes the key with nulled values after logout,
    // so the key stays but isAuthenticated must be false and token must be null.
    const afterLogout = await page.evaluate(() => {
      const raw = localStorage.getItem('auth-storage')
      return raw ? JSON.parse(raw) : null
    })
    // Either the key was removed entirely OR the persisted state has no auth
    if (afterLogout !== null) {
      expect(afterLogout.state.isAuthenticated).toBe(false)
      expect(afterLogout.state.token).toBeNull()
    }
  })

  // ---------------------------------------------------------------------------
  // Protected route redirect
  // ---------------------------------------------------------------------------

  test('direct navigation to protected page redirects to login when unauthenticated', async ({
    page,
  }) => {
    // No login — navigate directly to a protected page
    await page.goto('/admin/dashboard')
    await page.waitForURL('**/admin/login', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/login/)
  })

  test('multiple protected routes all redirect to login when unauthenticated', async ({
    page,
  }) => {
    const protectedRoutes = [
      '/admin/accounts',
      '/admin/users',
      '/admin/collections',
      '/admin/roles',
    ]

    for (const route of protectedRoutes) {
      await page.goto(route)
      await page.waitForURL('**/admin/login', { timeout: 10_000 })
      await expect(page).toHaveURL(/admin\/login/, {
        message: `Expected ${route} to redirect to login`,
      })
    }
  })

  // ---------------------------------------------------------------------------
  // Session persistence
  // ---------------------------------------------------------------------------

  test('session persists across page refresh', async ({ page, authenticatedPage }) => {
    await expect(page).toHaveURL(/admin\/dashboard/)

    // Reload — Zustand persist middleware should restore session from localStorage
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Should remain on dashboard, not redirected to login
    await expect(page).toHaveURL(/admin\/dashboard/)
  })

  test('session persists after navigating away and back', async ({ page, authenticatedPage }) => {
    // Navigate to a different page
    await page.goto('/admin/accounts')
    await page.waitForURL('**/admin/accounts', { timeout: 10_000 })

    // Hard-reload to simulate revisiting the app
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Should remain authenticated on the accounts page
    await expect(page).toHaveURL(/admin\/accounts/)
  })
})
