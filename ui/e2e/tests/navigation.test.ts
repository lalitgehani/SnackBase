/**
 * FT4.5: Navigation & Layout E2E Smoke Tests
 *
 * Verifies that sidebar navigation links resolve to the correct pages,
 * pages render without console errors, header titles are accurate,
 * the sidebar toggle works on mobile, and back-navigation functions correctly.
 *
 * Prerequisites:
 *   - SnackBase backend running at http://localhost:8000
 *   - Superadmin exists: `uv run python -m snackbase create-superadmin`
 *   - Run tests with: npm run test:e2e
 */

import { test, expect } from '../fixtures.js'

// ---------------------------------------------------------------------------
// Sidebar nav items: { label, url } — mirrors AppSidebar items (no superadminOnly guard)
// ---------------------------------------------------------------------------
const NAV_ITEMS = [
  { label: 'Dashboard', url: '/admin/dashboard' },
  { label: 'Configuration', url: '/admin/configuration' },
  { label: 'Accounts', url: '/admin/accounts' },
  { label: 'Users', url: '/admin/users' },
  { label: 'Invitations', url: '/admin/invitations' },
  { label: 'Groups', url: '/admin/groups' },
  { label: 'Collections', url: '/admin/collections' },
  { label: 'Roles', url: '/admin/roles' },
  { label: 'Audit Logs', url: '/admin/audit-logs' },
  { label: 'Migrations', url: '/admin/migrations' },
  { label: 'Macros', url: '/admin/macros' },
] as const

// Header titles as returned by AdminLayout's getPageTitle()
const PAGE_TITLES: Record<string, string> = {
  '/admin/dashboard': 'Dashboard',
  '/admin/accounts': 'Accounts',
  '/admin/users': 'Users',
  '/admin/groups': 'Groups',
  '/admin/collections': 'Collections',
  '/admin/roles': 'Roles',
  '/admin/audit-logs': 'Audit Logs',
  '/admin/migrations': 'Migrations',
  '/admin/macros': 'Macros',
  // Falls through to default in getPageTitle()
  '/admin/configuration': 'Admin',
  '/admin/invitations': 'Admin',
}

// ---------------------------------------------------------------------------
// 1. Sidebar navigation links resolve to correct pages
// ---------------------------------------------------------------------------

test.describe('Sidebar navigation links', () => {
  test('all nav links resolve to correct pages', async ({ page, authenticatedPage }) => {
    for (const item of NAV_ITEMS) {
      // Click the sidebar link by its visible text label
      await page.getByRole('link', { name: item.label, exact: true }).click()
      await page.waitForURL(`**${item.url}`, { timeout: 10_000 })
      await expect(page).toHaveURL(new RegExp(item.url.replace(/\//g, '\\/')))
    }
  })

  test('active sidebar link is highlighted for current page', async ({ page, authenticatedPage }) => {
    // Navigate to Accounts and verify the link has the active state
    await page.goto('/admin/accounts')
    await page.waitForURL('**/admin/accounts', { timeout: 10_000 })

    // SidebarMenuButton renders with data-active="true" when isActive=true
    const accountsLink = page.getByRole('link', { name: 'Accounts', exact: true })
    await expect(accountsLink).toBeVisible()
    // The active state is applied via aria-current or a data attribute by Radix/shadcn
    const activeState = await accountsLink.getAttribute('data-active')
    expect(activeState).toBe('true')
  })
})

// ---------------------------------------------------------------------------
// 2. Each page renders without console errors
// ---------------------------------------------------------------------------

test.describe('Pages render without console errors', () => {
  test('navigating through all pages produces no JavaScript errors', async ({
    page,
    authenticatedPage,
  }) => {
    const jsErrors: string[] = []

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text()
        // Exclude noisy network/API errors (4xx/5xx) that are expected in a live-backend
        // E2E environment and don't indicate JavaScript runtime failures.
        const isNetworkError =
          /failed to fetch|net::err_|404|401|403|500|xhr|http|api\//i.test(text)
        if (!isNetworkError) {
          jsErrors.push(text)
        }
      }
    })

    for (const item of NAV_ITEMS) {
      await page.goto(item.url)
      await page.waitForLoadState('networkidle')
    }

    expect(
      jsErrors,
      `Unexpected JavaScript console errors:\n${jsErrors.join('\n')}`,
    ).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// 3. Page titles update correctly in header
// ---------------------------------------------------------------------------

test.describe('Page header titles', () => {
  for (const [url, expectedTitle] of Object.entries(PAGE_TITLES)) {
    test(`header shows "${expectedTitle}" when on ${url}`, async ({ page, authenticatedPage }) => {
      await page.goto(url)
      await page.waitForURL(`**${url}`, { timeout: 10_000 })
      await page.waitForLoadState('networkidle')

      // AdminLayout renders the title in an <h2> inside the header
      const header = page.locator('header').getByRole('heading', { level: 2 })
      await expect(header).toHaveText(expectedTitle)
    })
  }
})

// ---------------------------------------------------------------------------
// 4. Responsive sidebar toggle (mobile viewport)
// ---------------------------------------------------------------------------

test.describe('Responsive sidebar toggle', () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test('sidebar trigger button is visible on mobile', async ({ page, authenticatedPage }) => {
    const trigger = page.locator('[data-sidebar="trigger"]')
    await expect(trigger).toBeVisible()
  })

  test('clicking sidebar trigger opens the sidebar on mobile', async ({
    page,
    authenticatedPage,
  }) => {
    // On mobile the sidebar is rendered as a Sheet (off-canvas); it starts closed.
    const mobileSheet = page.locator('[data-mobile="true"]')
    await expect(mobileSheet).toBeHidden()

    // Click the trigger to open
    await page.locator('[data-sidebar="trigger"]').click()

    // The Sheet should now be visible and contain sidebar navigation
    await expect(mobileSheet).toBeVisible({ timeout: 5_000 })
    await expect(mobileSheet.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible()
  })

  test('pressing Escape closes the sidebar on mobile', async ({
    page,
    authenticatedPage,
  }) => {
    const mobileSheet = page.locator('[data-mobile="true"]')

    // Open via trigger
    await page.locator('[data-sidebar="trigger"]').click()
    await expect(mobileSheet).toBeVisible({ timeout: 5_000 })

    // Close via Escape — Radix Sheet closes on Escape key press
    await page.keyboard.press('Escape')
    await expect(mobileSheet).toBeHidden({ timeout: 5_000 })
  })

  test('clicking the sheet overlay closes the sidebar on mobile', async ({
    page,
    authenticatedPage,
  }) => {
    const mobileSheet = page.locator('[data-mobile="true"]')
    const overlay = page.locator('[data-slot="sheet-overlay"]')

    // Open via trigger
    await page.locator('[data-sidebar="trigger"]').click()
    await expect(mobileSheet).toBeVisible({ timeout: 5_000 })

    // Click the backdrop overlay to dismiss the sheet
    await overlay.click()
    await expect(mobileSheet).toBeHidden({ timeout: 5_000 })
  })

  test('sidebar nav links work on mobile viewport', async ({ page, authenticatedPage }) => {
    // Open sidebar
    await page.locator('[data-sidebar="trigger"]').click()
    const mobileSheet = page.locator('[data-mobile="true"]')
    await expect(mobileSheet).toBeVisible({ timeout: 5_000 })

    // Click a nav link inside the mobile sidebar
    await mobileSheet.getByRole('link', { name: 'Collections', exact: true }).click()
    await page.waitForURL('**/admin/collections', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/collections/)
  })
})

// ---------------------------------------------------------------------------
// 5. Back navigation from nested pages
// ---------------------------------------------------------------------------

test.describe('Back navigation', () => {
  test('browser back button navigates from collections to previous page', async ({
    page,
    authenticatedPage,
  }) => {
    // Start on dashboard
    await page.goto('/admin/dashboard')
    await page.waitForURL('**/admin/dashboard', { timeout: 10_000 })

    // Navigate to collections
    await page.goto('/admin/collections')
    await page.waitForURL('**/admin/collections', { timeout: 10_000 })

    // Press browser back
    await page.goBack()
    await page.waitForURL('**/admin/dashboard', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/dashboard/)
  })

  test('browser forward button works after going back', async ({ page, authenticatedPage }) => {
    await page.goto('/admin/dashboard')
    await page.waitForURL('**/admin/dashboard', { timeout: 10_000 })

    await page.goto('/admin/accounts')
    await page.waitForURL('**/admin/accounts', { timeout: 10_000 })

    // Go back to dashboard
    await page.goBack()
    await page.waitForURL('**/admin/dashboard', { timeout: 10_000 })

    // Go forward to accounts
    await page.goForward()
    await page.waitForURL('**/admin/accounts', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/accounts/)
  })

  test('"Collections" back-button on records page navigates to collections list', async ({
    page,
    authenticatedPage,
  }) => {
    // First create a test collection via direct API call to have something to navigate to,
    // OR navigate to the records page for a known collection if any exists.
    // Since we cannot guarantee a collection exists, we test the "Back" button
    // by navigating directly to a records URL and checking if the button is present.
    await page.goto('/admin/collections/test_nav_col/records')
    await page.waitForLoadState('networkidle')

    // The RecordsPage always renders a "Collections" back button (ArrowLeft icon + "Collections")
    const backButton = page.getByRole('button', { name: /collections/i })
    await expect(backButton).toBeVisible({ timeout: 10_000 })

    // Clicking it should navigate back to /admin/collections
    await backButton.click()
    await page.waitForURL('**/admin/collections', { timeout: 10_000 })
    await expect(page).toHaveURL(/admin\/collections/)
  })
})
