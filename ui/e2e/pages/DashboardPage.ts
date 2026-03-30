import type { Page } from '@playwright/test'
import { BasePage } from './BasePage.js'

/**
 * Page object for the dashboard page (/admin/dashboard).
 */
export class DashboardPage extends BasePage {
  readonly url = '/admin/dashboard'

  // Locators
  readonly statsCards = () => this.page.locator('[data-testid="stat-card"]')
  readonly heading = () => this.page.getByRole('heading', { name: /dashboard/i })

  async navigate() {
    await this.goto(this.url)
    await this.waitForPageReady()
  }
}
