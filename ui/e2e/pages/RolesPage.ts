import { BasePage } from './BasePage.js'

/**
 * Page object for the roles management page (/admin/roles).
 */
export class RolesPage extends BasePage {
  readonly url = '/admin/roles'

  // Locators
  readonly heading = () => this.page.getByRole('heading', { name: /roles/i })
  readonly createButton = () => this.page.getByRole('button', { name: /create role/i })
  readonly roleRows = () => this.page.locator('tbody tr')

  async navigate() {
    await this.goto(this.url)
    await this.waitForPageReady()
  }

  /** Return the row locator for a role by name. */
  rowByName(name: string) {
    return this.roleRows().filter({ hasText: name })
  }

  /**
   * Create a role via the Create Role dialog.
   *
   * @param name         Role name.
   * @param description  Optional role description.
   */
  async createRole(name: string, description?: string) {
    await this.createButton().click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')

    await dialog.locator('#name').fill(name)
    if (description) {
      await dialog.locator('#description').fill(description)
    }

    await dialog.getByRole('button', { name: /^create role$/i }).click()

    // Dialog closes on success
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }
}
