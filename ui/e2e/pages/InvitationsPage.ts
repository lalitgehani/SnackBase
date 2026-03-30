import { BasePage } from './BasePage.js'

/**
 * Page object for the invitations management page (/admin/invitations).
 */
export class InvitationsPage extends BasePage {
  readonly url = '/admin/invitations'

  // Locators
  readonly heading = () => this.page.getByRole('heading', { name: /invitations/i })
  readonly inviteButton = () => this.page.getByRole('button', { name: /invite user/i })
  readonly invitationRows = () => this.page.locator('tbody tr')

  async navigate() {
    await this.goto(this.url)
    await this.waitForPageReady()
  }

  /** Return the row locator for an invitation by recipient email. */
  rowByEmail(email: string) {
    return this.invitationRows().filter({ hasText: email })
  }

  /**
   * Send an invitation via the Invite User dialog.
   *
   * @param email        Recipient email address.
   * @param accountName  Optional partial account name to select in the account dropdown.
   *                     When provided, waits for the account combobox to appear and selects the match.
   */
  async sendInvitation(email: string, accountName?: string) {
    await this.inviteButton().click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')

    await dialog.locator('#email').fill(email)

    if (accountName) {
      // The account SelectTrigger has no id — locate by role="combobox" within dialog.
      // It only renders when showAccountSelect is true (accounts loaded successfully).
      const accountCombobox = dialog.getByRole('combobox')
      await accountCombobox.waitFor({ state: 'visible', timeout: 10_000 })
      await accountCombobox.click()
      await this.page.waitForSelector('[role="option"]', { state: 'visible' })
      await this.page.getByRole('option', { name: new RegExp(accountName, 'i') }).click()
    }

    await dialog.getByRole('button', { name: /send invitation/i }).click()

    // Dialog closes on success
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }

  /**
   * Cancel a pending invitation by recipient email.
   * Handles the native window.confirm() browser dialog automatically.
   *
   * @param email  Recipient email of the invitation to cancel.
   */
  async cancelInvitation(email: string) {
    const row = this.rowByEmail(email)

    // Accept the native confirm() dialog before clicking the button
    this.page.once('dialog', (dialog) => dialog.accept())

    await row.getByTitle('Cancel Invitation').click()
    await this.waitForPageReady()
  }
}
