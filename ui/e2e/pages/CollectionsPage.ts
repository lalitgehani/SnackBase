import type { Page } from '@playwright/test'
import { BasePage } from './BasePage.js'

/**
 * Page object for the Collections workspace (/admin/collections).
 */
export class CollectionsPage extends BasePage {
  readonly url = '/admin/collections'

  // Locators
  readonly heading = () => this.page.getByRole('heading', { name: /collections/i })
  readonly createButton = () =>
    this.page.getByRole('button', { name: /new collection|create collection/i }).first()
  readonly rail = () => this.page.getByTestId('collection-browser-rail')
  readonly emptyState = () => this.page.getByText(/no collections/i)

  async navigate() {
    await this.goto(this.url)
    await this.waitForPageReady()
  }

  /** Return the rail link for a collection by name. */
  rowByName(name: string) {
    return this.page.getByRole('link', { name: new RegExp(name, 'i') })
  }

  /** Click a collection in the browser rail (opens default tab). */
  async openCollection(name: string) {
    await this.rowByName(name).click()
    await this.waitForPageReady()
  }

  /**
   * Create a collection via the Create Collection dialog.
   *
   * @param name    Collection name (alphanumeric + underscores, 3-64 chars).
   * @param fields  Array of schema fields to add via SchemaBuilder.
   */
  async createCollection(
    name: string,
    fields: Array<{ name: string; type?: string }>,
  ) {
    // Open dialog (workspace rail or empty-state CTA)
    await this.createButton().click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')

    // Fill collection name
    await dialog.locator('#collection-name').fill(name)

    // Add schema fields via SchemaBuilder
    for (let i = 0; i < fields.length; i++) {
      await dialog.getByRole('button', { name: /add field/i }).click()
      await dialog.locator(`#field-${i}-name`).fill(fields[i].name)

      if (fields[i].type && fields[i].type !== 'text') {
        await dialog.locator(`#field-${i}-type`).click()
        await this.page.getByRole('option', { name: fields[i].type }).click()
      }
    }

    await dialog.getByRole('button', { name: /^create collection$/i }).click()

    await this.page.waitForSelector('text=created successfully', { timeout: 30_000 })
    await dialog.getByRole('button', { name: /done/i }).click()

    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }

  /**
   * Open a collection and land on the Data tab.
   * Navigates via the rail, then ensures Data tab if needed.
   */
  async openManageRecords(name: string) {
    await this.openCollection(name)
    // After create with 0 records, default tab is Schema — switch to Data
    const dataUrl = new RegExp(`/admin/collections/${name}/(data|schema)`)
    await this.page.waitForURL(dataUrl, { timeout: 10_000 })
    if (!this.page.url().includes('/data')) {
      await this.page.getByRole('link', { name: /^data$/i }).click()
      await this.page.waitForURL(`**/collections/${name}/data`, { timeout: 10_000 })
    }
    await this.waitForPageReady()
  }

  /**
   * Delete a collection using the header Delete action.
   */
  async deleteCollection(name: string) {
    await this.openCollection(name)
    await this.page.waitForURL(new RegExp(`/admin/collections/${name}`), {
      timeout: 10_000,
    })

    await this.page.getByRole('button', { name: /^delete$/i }).click()
    await this.page.waitForSelector('[role="alertdialog"]', { state: 'visible' })

    await this.page.locator('#confirm-name').fill(name)
    await this.page.getByRole('button', { name: /^delete collection$/i }).click()

    await this.page.waitForSelector('text=deleted successfully', { timeout: 30_000 })
    await this.page.getByRole('button', { name: /done/i }).click()

    await this.page.waitForSelector('[role="alertdialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }
}
