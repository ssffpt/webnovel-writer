import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { outputFolder: 'e2e/reports' }], ['list']],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    // Smoke tests — critical path only (no auth required)
    {
      name: 'chromium:smoke',
      use: {
        executablePath: '/Users/liushuang/Library/Caches/ms-playwright/chromium-1208/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
        viewport: { width: 1440, height: 900 },
        browserName: 'chromium',
      },
      testMatch: /.*\.spec\.ts/,
      testIgnore: [/regression/, /handover/],
    },

    // Regression tests — full suite
    {
      name: 'chromium:regression',
      use: {
        executablePath: '/Users/liushuang/Library/Caches/ms-playwright/chromium-1208/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
        viewport: { width: 1440, height: 900 },
        browserName: 'chromium',
      },
      testMatch: /.*regression.*\.spec\.ts/,
    },
  ],

  webServer: {
    command: 'cd .. && npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
