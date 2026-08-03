/**
 * Function Code Editor browser coverage.
 *
 * Requires the SnackBase backend at http://localhost:8000 and a superadmin.
 */
import { request } from '@playwright/test'
import { test, expect } from '../fixtures.js'

const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://localhost:8000'
const SUPERADMIN_EMAIL = process.env.E2E_SUPERADMIN_EMAIL ?? 'admin@admin.com'
const SUPERADMIN_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD ?? 'Admin@123456'
const SYSTEM_ACCOUNT_ID = 'SY0000'
const FN_SLUG = 'e2e_code_editor'

async function getToken(): Promise<string> {
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  const res = await ctx.post('/api/v1/auth/login', {
    data: {
      account: SYSTEM_ACCOUNT_ID,
      email: SUPERADMIN_EMAIL,
      password: SUPERADMIN_PASSWORD,
    },
  })
  const body = await res.json()
  await ctx.dispose()
  return body.token as string
}

async function ensureFunction(token: string) {
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  const headers = { Authorization: `Bearer ${token}` }
  await ctx.delete(`/api/v1/functions/${FN_SLUG}`, { headers })
  const create = await ctx.post('/api/v1/functions', {
    headers,
    data: {
      name: 'E2E Code Editor',
      slug: FN_SLUG,
      auth_required: true,
      entrypoint: 'handler.py',
    },
  })
  if (!create.ok()) {
    throw new Error(`create function failed: ${create.status()} ${await create.text()}`)
  }
  const deploy = await ctx.post(`/api/v1/functions/${FN_SLUG}/deploy`, {
    headers,
    data: {
      entrypoint: 'handler.py',
      dependencies: [],
      files: {
        'handler.py':
          'from snackbase_fn import Request, Response\n\ndef handler(req: Request) -> Response:\n    return Response.json({"ok": True})\n',
        'utils.py': 'def helper() -> int:\n    return 42\n',
        'requirements.txt': '',
      },
    },
  })
  if (!deploy.ok()) {
    throw new Error(`deploy failed: ${deploy.status()} ${await deploy.text()}`)
  }
  await ctx.dispose()
}

test.describe('Function code editor', () => {
  test.beforeAll(async () => {
    const token = await getToken()
    await ensureFunction(token)
  })

  test.afterAll(async () => {
    try {
      const token = await getToken()
      const ctx = await request.newContext({ baseURL: BACKEND_URL })
      await ctx.delete(`/api/v1/functions/${FN_SLUG}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      await ctx.dispose()
    } catch {
      // best-effort cleanup
    }
  })

  test('loads CodeMirror, supports typing, search, and multi-file state', async ({
    authenticatedPage,
    page,
  }) => {
    void authenticatedPage
    await page.goto(`/admin/functions/${FN_SLUG}`)
    await expect(page.getByRole('heading', { name: 'E2E Code Editor' })).toBeVisible()
    await expect(page.getByTestId('code-editor')).toBeVisible({ timeout: 15_000 })

    const content = page.locator('.cm-content')
    await content.click()
    await page.keyboard.type('\n# e2e-marker\n')
    await expect(content).toContainText('e2e-marker')

    // Search panel (Mod-f)
    await page.keyboard.press('Meta+f')
    const search = page.locator('.cm-textfield').first()
    await expect(search).toBeVisible({ timeout: 5_000 })
    await search.fill('handler')
    await page.keyboard.press('Enter')
    await expect(page.locator('.cm-searchMatch').first()).toBeVisible({ timeout: 5_000 })
    await page.keyboard.press('Escape')

    // Switch files and back — content preserved
    await page.getByRole('button', { name: /^utils\.py/ }).click()
    await expect(page.getByTestId('code-editor')).toHaveAttribute('data-path', 'utils.py')
    await expect(content).toContainText('helper')
    await page.getByRole('button', { name: /^handler\.py/ }).click()
    await expect(content).toContainText('e2e-marker')

    // Tab indentation
    await content.click()
    await page.keyboard.press('End')
    await page.keyboard.press('Enter')
    await page.keyboard.press('Tab')
    await expect(content).toContainText('    ')
  })

  test('warns on navigation when dirty', async ({ authenticatedPage, page }) => {
    void authenticatedPage
    await page.goto(`/admin/functions/${FN_SLUG}`)
    await expect(page.getByTestId('code-editor')).toBeVisible({ timeout: 15_000 })

    const content = page.locator('.cm-content')
    await content.click()
    await page.keyboard.type('\n# dirty-marker\n')
    await expect(page.getByTestId('unsaved-changes')).toBeVisible()

    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm')
      await dialog.dismiss()
    })
    await page.getByRole('link', { name: /Functions/i }).first().click()
    await expect(page).toHaveURL(new RegExp(`/admin/functions/${FN_SLUG}`))
  })

  test('keyboard reaches file tabs and editor; a11y scan has no critical issues', async ({
    authenticatedPage,
    page,
  }) => {
    void authenticatedPage
    const { AxeBuilder } = await import('@axe-core/playwright')

    await page.goto(`/admin/functions/${FN_SLUG}`)
    await expect(page.getByTestId('code-editor')).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: /^handler\.py/ }).focus()
    await expect(page.getByRole('button', { name: /^handler\.py/ })).toBeFocused()
    await page.keyboard.press('Tab')
    // Move into editor content
    await page.locator('.cm-content').focus()
    await expect(page.locator('.cm-content')).toBeFocused()

    const results = await new AxeBuilder({ page })
      .include('[data-testid="code-editor"]')
      .include('[role="group"][aria-label="Source files"]')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()
    const critical = results.violations.filter((v) => v.impact === 'critical')
    expect(critical, JSON.stringify(critical, null, 2)).toEqual([])
  })

  test('repeated open/close does not leave stale editor hosts', async ({
    authenticatedPage,
    page,
  }) => {
    void authenticatedPage
    for (let i = 0; i < 3; i++) {
      await page.goto(`/admin/functions/${FN_SLUG}`)
      await expect(page.getByTestId('code-editor')).toBeVisible({ timeout: 15_000 })
      await page.goto('/admin/functions')
      await expect(page.getByTestId('code-editor')).toHaveCount(0)
    }
  })
})
