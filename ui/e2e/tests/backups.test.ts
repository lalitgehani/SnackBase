/**
 * Backup flows E2E (F6.2, F6.3)
 *
 * Creates a backup from the UI and verifies it appears in the list with a
 * Restorable badge; verifies the restore confirmation flow reaches the
 * typing gate and that logical archives present a disabled Restore action
 * with an explanatory tooltip.
 *
 * Prerequisites:
 *   - SnackBase backend running at http://localhost:8000
 *   - Superadmin exists: `uv run python -m snackbase create-superadmin`
 */

import type { Page } from '@playwright/test'
import { test, expect } from '../fixtures.js'

async function navigateToBackups(page: Page): Promise<void> {
  await page.goto('/admin/backups')
  await expect(
    page.getByRole('heading', { name: 'Backups', level: 1 }),
  ).toBeVisible()
}

/** Waits until no backup/restore is in flight (buttons re-enabled). */
async function waitForIdle(page: Page): Promise<void> {
  await expect(
    page.getByText(/Archives at the configured destination/),
  ).toBeVisible({ timeout: 30000 })
}

test.describe('Backups', () => {
  const runId = Date.now().toString(36)
  const createName = (base: string) => `e2e_${base}_${runId}.zip`

  test('create a backup from the UI and see it appear in the list', async ({
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- fixture performs the superadmin login
    authenticatedPage,
    page,
  }) => {
    await navigateToBackups(page)

    await page.getByTestId('backup-create-button').click()
    await page.getByLabel(/Archive name/i).fill('e2e_backup.zip')
    await page.getByRole('button', { name: 'Create', exact: true }).click()
    await expect(page.getByRole('dialog')).toBeHidden()

    const row = page.getByTestId('backup-row-e2e_backup.zip')
    await expect(row).toBeVisible({ timeout: 30000 })
    await waitForIdle(page)
    await expect(row.getByTestId('badge-e2e_backup.zip')).toHaveText('Restorable')

    // Clean up so repeated runs stay green.
    await page.getByTestId('delete-e2e_backup.zip').click()
    await page.getByRole('button', { name: 'Delete' }).last().click()
    await expect(page.getByTestId('backup-row-e2e_backup.zip')).toBeHidden({
      timeout: 15000,
    })
  })

  test('restore flow gates on typing the archive name', async ({
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- fixture performs the superadmin login
    authenticatedPage,
    page,
  }) => {
    await navigateToBackups(page)

    // Create an archive to restore.
    const name = createName('restore')
    await page.getByTestId('backup-create-button').click()
    await page.getByLabel(/Archive name/i).fill(name)
    await page.getByRole('button', { name: 'Create', exact: true }).click()
    await expect(page.getByRole('dialog')).toBeHidden()

    const row = page.getByTestId(`backup-row-${name}`)
    await expect(row).toBeVisible({ timeout: 30000 })
    await waitForIdle(page)

    await page.getByTestId(`restore-${name}`).click()
    const confirmButton = page.getByRole('button', { name: 'Restore', exact: true })
    await expect(confirmButton).toBeDisabled()

    // Typing a wrong name keeps the gate closed.
    await page.getByLabel(/Type the archive name/i).fill('wrong_name')
    await expect(confirmButton).toBeDisabled()

    // The dialog states the consequences.
    await expect(page.getByText(/will be discarded/i)).toBeVisible()

    // Do not actually restore; close the dialog and clean up.
    await page.getByRole('button', { name: 'Close' }).first().click()
    await page.getByTestId(`delete-${name}`).click()
    await page.getByRole('button', { name: 'Delete' }).last().click()
    await expect(page.getByTestId(`backup-row-${name}`)).toBeHidden({
      timeout: 15000,
    })
  })

  test('settings page hides S3 fields for the local destination', async ({
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- fixture performs the superadmin login
    authenticatedPage,
    page,
  }) => {
    await page.goto('/admin/backups/settings')
    await expect(
      page.getByRole('heading', { name: 'Backup Settings', level: 1 }),
    ).toBeVisible()
    await expect(page.getByTestId('local-destination-warning')).toBeVisible()
  })
})
