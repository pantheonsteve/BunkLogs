import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for the RBAC e2e suite.
 *
 * Assumes the local dev stack is already running:
 *   make up                # postgres, redis, django
 *   make frontend-dev      # vite on :5173
 *   make seed-rbac         # creates the 10 RBAC test users
 *
 * Run:
 *   npm run test:e2e
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: /.*\.spec\.ts/,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false, // tests share a logged-in browser context across pages
  retries: process.env.CI ? 2 : 1,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173',
    headless: true,
    actionTimeout: 7_000,
    navigationTimeout: 15_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
