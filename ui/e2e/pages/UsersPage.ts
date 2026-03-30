import { BasePage } from './BasePage.js'

/**
 * Page object for the users management page (/admin/users).
 */
export class UsersPage extends BasePage {
  readonly url = '/admin/users'

  // Locators
  readonly heading = () => this.page.getByRole('heading', { name: /^users$/i })
  readonly createButton = () => this.page.getByRole('button', { name: /create user/i })
  readonly userRows = () => this.page.locator('tbody tr')

  async navigate() {
    await this.goto(this.url)
    await this.waitForPageReady()
  }

  /** Return the row locator for a user by email. */
  rowByEmail(email: string) {
    return this.userRows().filter({ hasText: email })
  }

  /**
   * Create a user via the Create User dialog.
   *
   * @param opts.email        User email address.
   * @param opts.password     Password (must meet complexity requirements).
   * @param opts.accountName  Partial account name to match in the account dropdown.
   * @param opts.roleName     Role name to select (exact or partial match).
   */
  async createUser(opts: {
    email: string
    password: string
    accountName: string
    roleName: string
  }) {
    await this.createButton().click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')

    // Wait for the form to finish loading (spinner disappears, email input appears)
    await dialog.locator('#email').waitFor({ state: 'visible', timeout: 15_000 })

    // Fill credentials
    await dialog.locator('#email').fill(opts.email)
    await dialog.locator('#password').fill(opts.password)
    await dialog.locator('#confirmPassword').fill(opts.password)

    // Select account — SelectTrigger has id="account"
    await dialog.locator('#account').click()
    await this.page.waitForSelector('[role="option"]', { state: 'visible' })
    await this.page.getByRole('option', { name: new RegExp(opts.accountName, 'i') }).click()

    // Select role — SelectTrigger has id="role"
    await dialog.locator('#role').click()
    await this.page.waitForSelector('[role="option"]', { state: 'visible' })
    await this.page.getByRole('option', { name: new RegExp(`^${opts.roleName}$`, 'i') }).click()

    await dialog.getByRole('button', { name: /^create user$/i }).click()

    // Dialog closes on success
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }

  /**
   * Edit a user's role via the Edit User dialog.
   *
   * @param email       Email of the user to edit.
   * @param roleName    New role name to assign.
   */
  async editUserRole(email: string, roleName: string) {
    const row = this.rowByEmail(email)
    await row.getByTitle('Edit user').click()
    await this.page.waitForSelector('[role="dialog"]', { state: 'visible' })

    const dialog = this.page.getByRole('dialog')

    // Wait for roles to load — the role SelectTrigger has id="role"
    await dialog.locator('#role').waitFor({ state: 'visible', timeout: 15_000 })

    await dialog.locator('#role').click()
    await this.page.waitForSelector('[role="option"]', { state: 'visible' })
    await this.page.getByRole('option', { name: new RegExp(`^${roleName}$`, 'i') }).click()

    await dialog.getByRole('button', { name: /^update user$/i }).click()

    // Dialog closes on success
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden' })
    await this.waitForPageReady()
  }
}
