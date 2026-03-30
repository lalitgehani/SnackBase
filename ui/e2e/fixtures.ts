import { test as base } from '@playwright/test'
import { LoginPage } from './pages/LoginPage.js'
import { DashboardPage } from './pages/DashboardPage.js'
import { CollectionsPage } from './pages/CollectionsPage.js'
import { RecordsPage } from './pages/RecordsPage.js'

/**
 * Extended test fixtures that provide pre-instantiated page objects.
 *
 * Usage:
 *   import { test, expect } from '@/e2e/fixtures'
 *
 *   test('my test', async ({ loginPage, dashboardPage }) => {
 *     await loginPage.navigate()
 *     ...
 *   })
 */

type PageFixtures = {
  loginPage: LoginPage
  dashboardPage: DashboardPage
  collectionsPage: CollectionsPage
  /** Factory: returns a RecordsPage for the given collection name. */
  recordsPage: (collectionName: string) => RecordsPage
  /** Navigates to login and authenticates as superadmin before the test body */
  authenticatedPage: { loginPage: LoginPage; dashboardPage: DashboardPage }
}

export const test = base.extend<PageFixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page))
  },

  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page))
  },

  collectionsPage: async ({ page }, use) => {
    await use(new CollectionsPage(page))
  },

  recordsPage: async ({ page }, use) => {
    await use((collectionName: string) => new RecordsPage(page, collectionName))
  },

  authenticatedPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page)
    await loginPage.loginAsSuperadmin()
    // Wait for redirect to dashboard after successful login
    await page.waitForURL('**/admin/dashboard', { timeout: 10_000 })
    await use({ loginPage, dashboardPage: new DashboardPage(page) })
  },
})

export { expect } from '@playwright/test'
