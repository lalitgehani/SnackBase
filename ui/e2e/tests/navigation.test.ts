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

import type { Locator, Page } from '@playwright/test'
import { test, expect } from '../fixtures.js'

// ---------------------------------------------------------------------------
// Sidebar nav items: { label, url } — mirrors AppSidebar (non-superadminOnly items)
// Grouped in the same order as AppSidebar information architecture.
// ---------------------------------------------------------------------------
const NAV_ITEMS = [
  // Overview
  { label: 'Dashboard', url: '/admin/dashboard' },
  // Data
  { label: 'Collections', url: '/admin/collections' },
  { label: 'Macros', url: '/admin/macros' },
  // Access — accounts → users/groups/roles → invitations → API keys
  { label: 'Accounts', url: '/admin/accounts' },
  { label: 'Users', url: '/admin/users' },
  { label: 'Groups', url: '/admin/groups' },
  { label: 'Roles', url: '/admin/roles' },
  { label: 'Invitations', url: '/admin/invitations' },
  // Automation — hooks → schedules → workflows → jobs
  { label: 'Hooks', url: '/admin/hooks' },
  { label: 'Scheduled Tasks', url: '/admin/scheduled-tasks' },
  { label: 'Workflows', url: '/admin/workflows' },
  // Integrations
  { label: 'Webhooks', url: '/admin/webhooks' },
  { label: 'Endpoints', url: '/admin/endpoints' },
  // System
  { label: 'Configuration', url: '/admin/configuration' },
  { label: 'Audit Logs', url: '/admin/audit-logs' },
  { label: 'Migrations', url: '/admin/migrations' },
] as const

/** Collapsible section labels in AppSidebar (buttons, not links). */
const NAV_SECTIONS = [
  'Data',
  'Access',
  'Automation',
  'Integrations',
  'System',
] as const

/**
 * Expand every collapsed sidebar section so nested nav links are visible.
 *
 * Uses accessible section button names + aria-expanded (Radix CollapsibleTrigger).
 * Optionally scope to the mobile sheet locator so desktop chrome is ignored.
 */
async function expandAllSidebarSections(root: Page | Locator) {
  for (const label of NAV_SECTIONS) {
    const trigger = root.getByRole('button', { name: label, exact: true })
    if ((await trigger.count()) === 0) continue
    const expanded = await trigger.getAttribute('aria-expanded')
    if (expanded === 'true') continue
    await trigger.click()
  }
}

// Header titles as returned by AdminLayout's getPageTitle()
const PAGE_TITLES: Record<string, string> = {
  '/admin/dashboard': 'Dashboard',
  '/admin/collections': 'Collections',
  '/admin/macros': 'Macros',
  '/admin/accounts': 'Accounts',
  '/admin/users': 'Users',
  '/admin/groups': 'Groups',
  '/admin/roles': 'Roles',
  '/admin/invitations': 'Invitations',
  '/admin/hooks': 'Hooks',
  '/admin/scheduled-tasks': 'Scheduled Tasks',
  '/admin/workflows': 'Workflows',
  '/admin/webhooks': 'Webhooks',
  '/admin/endpoints': 'Endpoints',
  '/admin/configuration': 'Configuration',
  '/admin/audit-logs': 'Audit Logs',
  '/admin/migrations': 'Migrations',
}

// ---------------------------------------------------------------------------
// 1. Sidebar navigation links resolve to correct pages
// ---------------------------------------------------------------------------

test.describe('Sidebar navigation links', () => {
  test('all nav links resolve to correct pages', async ({ page, authenticatedPage }) => {
    await expandAllSidebarSections(page)

    for (const item of NAV_ITEMS) {
      // Nested sections may re-collapse after navigation; re-expand as needed
      await expandAllSidebarSections(page)
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
    // Access section auto-opens for the active route
    await expandAllSidebarSections(page)

    // SidebarMenuSubButton renders with data-active="true" when isActive=true
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

    // Focus dialog content so Escape is handled by the Radix Sheet/Dialog layer
    await mobileSheet.focus()
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
    await expect(overlay).toBeVisible({ timeout: 5_000 })

    // Sheet is docked left and covers most of the viewport; click the
    // exposed dimmed strip on the right so the overlay receives the event
    // (top-left lands on the sheet header and is intercepted).
    const box = await overlay.boundingBox()
    expect(box).toBeTruthy()
    await page.mouse.click(box!.x + box!.width - 8, box!.y + box!.height / 2)

    await expect(mobileSheet).toBeHidden({ timeout: 5_000 })
  })

  test('sidebar nav links work on mobile viewport', async ({ page, authenticatedPage }) => {
    // Open sidebar
    await page.locator('[data-sidebar="trigger"]').click()
    const mobileSheet = page.locator('[data-mobile="true"]')
    await expect(mobileSheet).toBeVisible({ timeout: 5_000 })

    // Expand collapsed sections inside the mobile sheet, then navigate
    await expandAllSidebarSections(mobileSheet)

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

  test('sidebar Collections link returns to list from collection data tab', async ({
    page,
    authenticatedPage,
  }) => {
    // Use the collection seeded by global-setup (e2e_test_items).
    // Workspace embeds RecordsPage without the old standalone "← Collections" chrome;
    // the app sidebar Collections link is the primary way back to the list.
    await page.goto('/admin/collections/e2e_test_items/data')
    await page.waitForURL('**/admin/collections/e2e_test_items/data', {
      timeout: 10_000,
    })
    await page.waitForLoadState('networkidle')

    // Data section auto-opens on collection routes; ensure nested link is visible
    await expandAllSidebarSections(page)

    // Sidebar nav link (exact) — not "Refresh collections" or other chrome
    const collectionsNav = page.getByRole('link', { name: 'Collections', exact: true })
    await expect(collectionsNav).toBeVisible({ timeout: 10_000 })
    await collectionsNav.click()

    await page.waitForURL(/\/admin\/collections\/?$/, { timeout: 10_000 })
    await expect(page).toHaveURL(/\/admin\/collections\/?$/)
    await expect(
      page.getByRole('heading', { name: /select a collection/i }),
    ).toBeVisible({ timeout: 10_000 })
  })
})
