import type { Page } from '@playwright/test'
import { BasePage } from './BasePage.js'

/**
 * Page object for the accounts management page (/admin/accounts).
 */
export class AccountsPage extends BasePage {
  readonly url = '/admin/accounts'

  // Locators
  readonly heading = () => this.page.getByRole('heading', { name: /^accounts$/i })
  readonly createButton = () => this.page.getByRole('button', { name: /create account/i })
  readonly accountRows = () => this.page.locator('tbody tr')
  readonly emptyState = () => this.page.getByText(/no accounts yet/i)

  async navigate() {
    await this.goto(this.url)
    await this.waitForPageReady()
  }

  /** Return the row locator for an account by display name. */
  rowByName(name: string) {
    return this.accountRows().filter({ hasText: name })
  }

  /**
   * Create an account via the Create Account dialog.
   *
   * @param name  Display name for the account.
   * @param slug  Optional slug (auto-generated if omitted).
   */
  async createAccount(name: string, slug?: string) {
    await this.createButton().click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')

    await dialog.locator('#name').fill(name)
    if (slug) {
      await dialog.locator('#slug').fill(slug)
    }

    await dialog.getByRole('button', { name: /^create account$/i }).click()

    // Dialog closes on success
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }

  /**
   * Delete an account using the confirmation dialog (requires typing the name).
   *
   * @param name  The account display name to delete (used for row lookup and confirmation).
   */
  async deleteAccount(name: string) {
    const row = this.rowByName(name)
    await row.getByTitle('Delete account').click()
    await this.page.waitForSelector('[role="alertdialog"]', { state: 'visible' })

    // Type the account name to confirm deletion
    await this.page.locator('#confirm-name').fill(name)

    // Click the destructive Delete button
    await this.page.getByRole('button', { name: /^delete account$/i }).click()

    // Dialog closes on success
    await this.page.waitForSelector('[role="alertdialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }
}
