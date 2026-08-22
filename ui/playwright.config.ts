import { defineConfig, devices } from '@playwright/test';

const isPlatformProject = process.env.PLAYWRIGHT_PLATFORM === 'true';

/**
 * Playwright E2E test configuration with dual-mode parity gate (F4.7).
 *
 * Self-host (default): Vite dev server against local SnackBase instance.
 * Platform: set PLAYWRIGHT_PLATFORM=true and PLATFORM_BASE_URL.
 */
export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['html', { outputFolder: 'playwright-report' }], ['list']],
  outputDir: 'test-results',

  use: {
    baseURL: isPlatformProject
      ? process.env.PLATFORM_BASE_URL ?? 'http://localhost:5173'
      : 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'self-host',
      testMatch: /^(?!.*\.platform\.).*\.test\.ts$/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'platform',
      testMatch: /^(?!.*\.selfhost\.).*\.test\.ts$/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],

  webServer: isPlatformProject
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:5173',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },

  globalSetup: isPlatformProject ? undefined : './e2e/global-setup.ts',
  globalTeardown: isPlatformProject ? undefined : './e2e/global-teardown.ts',
});
