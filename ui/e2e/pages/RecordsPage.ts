import type { Page, Locator } from '@playwright/test'
import { BasePage } from './BasePage.js'

/**
 * Page object for the records management page
 * (/admin/collections/{collectionName}/records).
 */
export class RecordsPage extends BasePage {
  readonly collectionName: string

  constructor(page: Page, collectionName: string) {
    super(page)
    this.collectionName = collectionName
  }

  get url() {
    return `/admin/collections/${this.collectionName}/records`
  }

  // Locators
  readonly heading = () => this.page.getByRole('heading', { name: this.collectionName })
  // Two "Create Record" buttons can exist simultaneously: one in the page header
  // and one in the empty-state card. The header button is first in DOM order.
  readonly createButton = () =>
    this.page.getByRole('button', { name: /create record/i }).first()
  readonly recordRows = () => this.page.locator('tbody tr')
  readonly emptyState = () => this.page.getByText(/no records yet/i)
  readonly backButton = () => this.page.getByRole('button', { name: /collections/i })

  async navigate() {
    await this.goto(this.url)
    await this.waitForPageReady()
  }

  /** Return the row that contains the given text (matches anywhere in the row). */
  rowByText(text: string): Locator {
    return this.recordRows().filter({ hasText: text })
  }

  /** Open the Create Record dialog by clicking the header button. */
  async openCreateDialog() {
    await this.createButton().click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })
  }

  /**
   * Fill and submit the Create Record dialog.
   *
   * @param fieldValues  Map of field name → value for text/number fields.
   * @param selectFirstAccount  When true, select the first account in the
   *   account picker (required when logged in as superadmin).
   */
  async submitCreateDialog(
    fieldValues: Record<string, string>,
    selectFirstAccount = true,
  ) {
    const dialog = this.page.getByRole('dialog')

    // Superadmin account selector ─────────────────────────────────────────────
    if (selectFirstAccount) {
      // The trigger has id="account-select" and role="combobox"
      await dialog.locator('#account-select').click()
      // Radix Select renders options in a portal attached to <body>
      await this.page.waitForSelector('[role="option"]', { state: 'visible' })
      await this.page.getByRole('option').first().click()
    }

    // Fill schema fields ───────────────────────────────────────────────────────
    for (const [fieldName, value] of Object.entries(fieldValues)) {
      // DynamicFieldInput renders with id="field-{fieldName}"
      await dialog.locator(`#field-${fieldName}`).fill(value)
    }

    // Submit via the form button ───────────────────────────────────────────────
    await dialog.getByRole('button', { name: /create record/i }).click()
    // Dialog closes on success
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }

  /**
   * Click the Edit (pencil) button on a specific row and submit the edit dialog.
   *
   * @param rowLocator  The row locator (use `rowByText()`).
   * @param fieldValues  Map of field name → new value.
   */
  async editRecord(rowLocator: Locator, fieldValues: Record<string, string>) {
    // Action buttons in the row: [View(0), Edit(1), Delete(2)]
    await rowLocator.getByRole('button').nth(1).click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')
    for (const [fieldName, value] of Object.entries(fieldValues)) {
      const input = dialog.locator(`#field-${fieldName}`)
      await input.clear()
      await input.fill(value)
    }

    await dialog.getByRole('button', { name: /save changes/i }).click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }

  /**
   * Click the Delete (trash) button on a specific row and confirm deletion.
   *
   * @param rowLocator  The row locator (use `rowByText()`).
   */
  async deleteRecord(rowLocator: Locator) {
    // Action buttons in the row: [View(0), Edit(1), Delete(2)]
    await rowLocator.getByRole('button').nth(2).click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')
    await dialog.getByRole('button', { name: /delete record/i }).click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }
}
