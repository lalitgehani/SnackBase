/**
 * Theme persistence smoke — Dark / Light Mode Phase 4 (PRD F4.2).
 *
 * Verifies that appearance preference survives reload via localStorage key
 * `snackbase.theme`, and that the FOUC boot script + next-themes stay in sync.
 *
 * Uses the public login page ModeToggle so these tests do not depend on
 * authenticated admin chrome (they still run under globalSetup which needs
 * a healthy backend for the rest of the suite).
 */

import { test, expect } from '../fixtures.js'

const STORAGE_KEY = 'snackbase.theme'

async function openThemeMenu(page: import('@playwright/test').Page) {
  const toggle = page.getByRole('button', { name: /toggle theme/i })
  await expect(toggle).toBeVisible()
  await expect(toggle).toBeEnabled()
  await toggle.click()
}

async function selectTheme(
  page: import('@playwright/test').Page,
  label: RegExp,
) {
  await openThemeMenu(page)
  const option = page.getByRole('menuitemradio', { name: label })
  await expect(option).toBeVisible()
  await option.click()
}

async function getStoredTheme(page: import('@playwright/test').Page) {
  return page.evaluate((key) => localStorage.getItem(key), STORAGE_KEY)
}

async function htmlHasDarkClass(page: import('@playwright/test').Page) {
  return page.evaluate(() => document.documentElement.classList.contains('dark'))
}

test.describe('Theme preference persistence (PRD Phase 4)', () => {
  test.beforeEach(async ({ loginPage, page }) => {
    await loginPage.navigate()
    await page.evaluate((key) => localStorage.removeItem(key), STORAGE_KEY)
    // Re-navigate so FOUC script and provider start from a clean preference
    await loginPage.navigate()
  })

  test('selecting Dark persists across reload', async ({ page, loginPage }) => {
    await selectTheme(page, /^dark$/i)

    await expect.poll(async () => getStoredTheme(page)).toBe('dark')
    await expect.poll(async () => htmlHasDarkClass(page)).toBe(true)

    await page.reload()
    await expect(page.getByRole('button', { name: /toggle theme/i })).toBeVisible()

    expect(await getStoredTheme(page)).toBe('dark')
    expect(await htmlHasDarkClass(page)).toBe(true)
    // Login form still usable after themed reload
    await expect(loginPage.emailInput()).toBeVisible()
  })

  test('selecting Light persists across reload', async ({ page }) => {
    // Start from dark so we can observe the light flip
    await page.evaluate((key) => localStorage.setItem(key, 'dark'), STORAGE_KEY)
    await page.reload()
    await expect.poll(async () => htmlHasDarkClass(page)).toBe(true)

    await selectTheme(page, /^light$/i)

    await expect.poll(async () => getStoredTheme(page)).toBe('light')
    await expect.poll(async () => htmlHasDarkClass(page)).toBe(false)

    await page.reload()
    await expect(page.getByRole('button', { name: /toggle theme/i })).toBeVisible()

    expect(await getStoredTheme(page)).toBe('light')
    expect(await htmlHasDarkClass(page)).toBe(false)
  })

  test('selecting System follows color scheme and persists', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' })
    await selectTheme(page, /^system$/i)

    await expect.poll(async () => getStoredTheme(page)).toBe('system')
    await expect.poll(async () => htmlHasDarkClass(page)).toBe(true)

    await page.reload()
    expect(await getStoredTheme(page)).toBe('system')
    expect(await htmlHasDarkClass(page)).toBe(true)

    // When OS is light, system preference resolves to light
    await page.emulateMedia({ colorScheme: 'light' })
    await page.reload()
    expect(await getStoredTheme(page)).toBe('system')
    expect(await htmlHasDarkClass(page)).toBe(false)
  })

  test('clearing storage returns to system default behavior', async ({ page }) => {
    await selectTheme(page, /^dark$/i)
    await expect.poll(async () => getStoredTheme(page)).toBe('dark')

    await page.evaluate((key) => localStorage.removeItem(key), STORAGE_KEY)
    await page.emulateMedia({ colorScheme: 'light' })
    await page.reload()

    expect(await getStoredTheme(page)).toBeNull()
    // No stored preference + light OS → not dark
    expect(await htmlHasDarkClass(page)).toBe(false)

    await page.emulateMedia({ colorScheme: 'dark' })
    await page.reload()
    expect(await getStoredTheme(page)).toBeNull()
    expect(await htmlHasDarkClass(page)).toBe(true)
  })

  test('theme toggle is keyboard reachable on login', async ({ page }) => {
    const toggle = page.getByRole('button', { name: /toggle theme/i })
    await expect(toggle).toBeEnabled()

    await toggle.focus()
    await expect(toggle).toBeFocused()

    await page.keyboard.press('Enter')
    await expect(page.getByRole('menuitemradio', { name: /^light$/i })).toBeVisible()
    await expect(page.getByRole('menuitemradio', { name: /^dark$/i })).toBeVisible()
    await expect(page.getByRole('menuitemradio', { name: /^system$/i })).toBeVisible()

    // Selected state is exposed as radio (non-color cue)
    const dark = page.getByRole('menuitemradio', { name: /^dark$/i })
    await dark.click()
    await expect.poll(async () => getStoredTheme(page)).toBe('dark')
  })
})
