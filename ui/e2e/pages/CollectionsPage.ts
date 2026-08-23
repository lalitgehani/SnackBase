import { BasePage } from './BasePage.js'

/**
 * Page object for the Collections workspace (/admin/collections).
 * Create flow is full-page at /admin/collections/new (not a modal).
 */
export class CollectionsPage extends BasePage {
  readonly url = '/admin/collections'

  // Locators
  readonly heading = () => this.page.getByRole('heading', { name: /collections/i })
  readonly createButton = () =>
    this.page.getByTestId('collections-new-collection').first()
  readonly rail = () => this.page.getByTestId('collection-browser-rail')
  readonly emptyState = () => this.page.getByText(/no collections/i)
  readonly newPage = () => this.page.getByTestId('collection-new-page')

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
   * Create a collection via the full-page create flow.
   *
   * @param name    Collection name (alphanumeric + underscores, 3-64 chars).
   * @param fields  Array of schema fields to add via SchemaColumnTable.
   */
  async createCollection(
    name: string,
    fields: Array<{ name: string; type?: string }>,
  ) {
    await this.page
      .locator(
        '[data-testid="collection-browser-rail"], [data-testid="collection-browser-rail-collapsed"]',
      )
      .first()
      .waitFor({ state: 'visible', timeout: 10_000 })
    await this.createButton().waitFor({ state: 'visible', timeout: 10_000 })
    await this.createButton().click()
    await this.page.waitForURL('**/admin/collections/new**', { timeout: 10_000 })
    await this.newPage().waitFor({ state: 'visible' })

    await this.page.locator('#collection-name').fill(name)

    for (let i = 0; i < fields.length; i++) {
      await this.page.getByTestId('schema-add-field').click()
      await this.page.locator(`#field-${i}-name`).fill(fields[i].name)

      if (fields[i].type && fields[i].type !== 'text') {
        await this.page.locator(`#field-${i}-type`).click()
        await this.page.getByRole('option', { name: fields[i].type, exact: true }).click()
      }
    }

    await this.page.getByRole('button', { name: /^create collection$/i }).click()

    // Success toast + navigate to schema tab
    await this.page.waitForURL(new RegExp(`/admin/collections/${name}`), {
      timeout: 30_000,
    })
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
   *
   * CollectionDetailLayout navigates to /admin/collections after a successful
   * delete (replace), which unmounts the success dialog — so we wait for that
   * navigation rather than a "Done" button.
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

    // Auto-navigate to workspace list after delete; dialog may unmount first
    await this.page.waitForURL(/\/admin\/collections\/?$/, { timeout: 30_000 })
    await this.waitForPageReady()
  }
}
