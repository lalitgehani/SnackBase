/**
 * One-off docs screenshot capture for the backup walkthrough (docs/backups.md).
 * Run: node scripts/capture-backup-docs.mjs  (from ui/, backend on :8000, dev server on :5173)
 */
import { chromium } from '@playwright/test';

const BASE = 'http://localhost:5173';
const OUT = '../docs/images';
const API = 'http://localhost:8000';

async function login(page) {
  await page.goto(`${BASE}/admin/login`);
  await page.getByLabel(/email/i).fill('admin@admin.com');
  await page.getByLabel(/password/i).fill('Admin@123456');
  await page.getByRole('button', { name: /^login$|^logging in/i }).click();
  await page.waitForURL('**/admin/dashboard**', { timeout: 15000 });
}

async function createArchive(name) {
  const login = await fetch(`${API}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@admin.com', password: 'Admin@123456', account: 'SY0000' }),
  }).then((r) => r.json());
  await fetch(`${API}/api/v1/backups`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${login.access_token ?? login.token}`,
    },
    body: JSON.stringify({ name }),
  });
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await login(page);

  // Seed an archive so the list, badge, and dialog have real content.
  await createArchive('docs_walkthrough.zip');

  await page.goto(`${BASE}/admin/backups`);
  const row = page.getByTestId('backup-row-docs_walkthrough.zip');
  await row.waitFor({ timeout: 30000 });
  await page.getByText(/Archives at the configured destination/).waitFor();
  await page.screenshot({ path: `${OUT}/backups-list.png`, fullPage: true });

  // Restore dialog with the typing gate.
  await page.getByTestId('restore-docs_walkthrough.zip').click();
  await page.getByText(/will be discarded/i).waitFor();
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/backups-restore-dialog.png` });
  await page.getByRole('button', { name: 'Close' }).first().click();

  // Settings page.
  await page.goto(`${BASE}/admin/backups/settings`);
  await page.getByRole('heading', { name: 'Backup Settings', level: 1 }).waitFor();
  await page.getByTestId('cron-preset-0 2 * * *').click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/backups-settings.png`, fullPage: true });

  await browser.close();
  console.log('screenshots captured');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
