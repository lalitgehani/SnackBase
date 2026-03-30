import type { Page } from '@playwright/test'
import { BasePage } from './BasePage.js'

/**
 * Page object for the login page (/admin/login).
 */
export class LoginPage extends BasePage {
  readonly url = '/admin/login'

  // Locators
  readonly emailInput = () => this.page.getByLabel(/email/i)
  readonly passwordInput = () => this.page.getByLabel(/password/i)
  readonly submitButton = () => this.page.getByRole('button', { name: /^login$|^logging in/i })
  /** Error message displayed on login failure */
  readonly errorMessage = () => this.page.locator('[class*="bg-destructive"] p')

  async navigate() {
    await this.goto(this.url)
  }

  async login(email: string, password: string) {
    await this.emailInput().fill(email)
    await this.passwordInput().fill(password)
    await this.submitButton().click()
  }

  async loginAsSuperadmin() {
    const email = process.env.E2E_SUPERADMIN_EMAIL ?? 'admin@admin.com'
    const password = process.env.E2E_SUPERADMIN_PASSWORD ?? 'Admin@123456'
    await this.navigate()
    await this.login(email, password)
  }
}
