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

  /** Return the row locator for a collection by name. */
  rowByName(name: string) {
    return this.collectionRows().filter({ hasText: name })
  }

  /** Click a collection row to navigate to its records page (legacy helper). */
  async openCollection(name: string) {
    await this.page.getByRole('link', { name }).click()
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
    // Open dialog
    await this.createButton().click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')

    // Fill collection name
    await dialog.locator('#collection-name').fill(name)

    // Add schema fields via SchemaBuilder
    for (let i = 0; i < fields.length; i++) {
      // Click "Add Field" to append a new field row
      await dialog.getByRole('button', { name: /add field/i }).click()

      // Fill field name — input id follows the pattern field-{index}-name
      await dialog.locator(`#field-${i}-name`).fill(fields[i].name)

      // Optionally change the field type (defaults to "text")
      if (fields[i].type && fields[i].type !== 'text') {
        await dialog.locator(`#field-${i}-type`).click()
        await this.page.getByRole('option', { name: fields[i].type }).click()
      }
    }

    // Submit the form
    await dialog.getByRole('button', { name: /^create collection$/i }).click()

    // Wait for success state ("created successfully" message) then dismiss
    await this.page.waitForSelector('text=created successfully', { timeout: 30_000 })
    await dialog.getByRole('button', { name: /done/i }).click()

    // Dialog should close and the list should refresh
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }

  /**
   * Click the "Manage records" (Database icon) button on a collection row.
   * Navigates to /admin/collections/{name}/records.
   */
  async openManageRecords(name: string) {
    const row = this.rowByName(name)
    // The Database icon button has title="Manage records"
    await row.getByTitle('Manage records').click()
    await this.page.waitForURL(`**/collections/${name}/records`, { timeout: 10_000 })
    await this.waitForPageReady()
  }

  /**
   * Delete a collection using the Delete dialog (requires typing the name).
   *
   * @param name  The collection name to delete.
   */
  async deleteCollection(name: string) {
    const row = this.rowByName(name)
    // The Trash2 icon button has title="Delete collection"
    await row.getByTitle('Delete collection').click()
    await this.page.waitForSelector('[role="alertdialog"]', { state: 'visible' })

    // Type the collection name to confirm deletion
    await this.page.locator('#confirm-name').fill(name)

    // Click the destructive Delete button
    await this.page.getByRole('button', { name: /^delete collection$/i }).click()

    // Wait for success state then dismiss
    await this.page.waitForSelector('text=deleted successfully', { timeout: 30_000 })
    await this.page.getByRole('button', { name: /done/i }).click()

    // Dialog closes and list refreshes
    await this.page.waitForSelector('[role="alertdialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }
}
