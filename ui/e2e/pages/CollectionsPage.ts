import type { Page } from '@playwright/test'
import { BasePage } from './BasePage.js'

/**
 * Page object for the collections list page (/admin/collections).
 */
export class CollectionsPage extends BasePage {
  readonly url = '/admin/collections'

  // Locators
  readonly heading = () => this.page.getByRole('heading', { name: /collections/i })
  readonly createButton = () => this.page.getByRole('button', { name: /create collection/i })
  readonly collectionRows = () => this.page.locator('tbody tr')
  readonly emptyState = () => this.page.getByText(/no collections/i)

  async navigate() {
    await this.goto(this.url)
    await this.waitForPageReady()
  }

  /** Click a collection row to navigate to its records page */
  async openCollection(name: string) {
    await this.page.getByRole('link', { name }).click()
  }
}
