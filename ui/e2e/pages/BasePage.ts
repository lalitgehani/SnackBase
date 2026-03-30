import type { Page } from '@playwright/test'

/**
 * Base page object that all page models extend.
 * Provides common navigation helpers and shared utilities.
 */
export class BasePage {
  constructor(protected readonly page: Page) {}

  /** Navigate to a URL relative to the base URL */
  async goto(path: string) {
    await this.page.goto(path)
  }

  /** Wait for the main content area to be visible */
  async waitForPageReady() {
    await this.page.waitForLoadState('networkidle')
  }

  /** Get the current page title from the browser */
  async getTitle() {
    return this.page.title()
  }
}
