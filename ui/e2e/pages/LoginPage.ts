import type { Page } from '@playwright/test'
import { BasePage } from './BasePage.js'

/**
 * Page object for the login page (/admin/login).
 */
export class LoginPage extends BasePage {
  readonly url = '/admin/login'

  // Locators
  readonly accountSlugInput = () => this.page.getByLabel(/account/i)
  readonly emailInput = () => this.page.getByLabel(/email/i)
  readonly passwordInput = () => this.page.getByLabel(/password/i)
  readonly submitButton = () => this.page.getByRole('button', { name: /sign in|login/i })
  readonly errorMessage = () => this.page.getByRole('alert')

  async navigate() {
    await this.goto(this.url)
  }

  async login(accountSlug: string, email: string, password: string) {
    await this.accountSlugInput().fill(accountSlug)
    await this.emailInput().fill(email)
    await this.passwordInput().fill(password)
    await this.submitButton().click()
  }

  async loginAsSuperadmin() {
    // Superadmin belongs to the system account (account ID: SY0000)
    const accountId = process.env.E2E_SYSTEM_ACCOUNT_ID ?? 'SY0000'
    const email = process.env.E2E_SUPERADMIN_EMAIL ?? 'admin@admin.com'
    const password = process.env.E2E_SUPERADMIN_PASSWORD ?? 'Admin@123456'
    await this.navigate()
    await this.login(accountId, email, password)
  }
}
