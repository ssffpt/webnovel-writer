import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,  // init wizard tests need sequential execution
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  timeout: 60_000,
  reporter: [['list']],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
        viewport: { width: 1440, height: 900 },
      },
      testMatch: /.*\.spec\.ts/,
    },
  ],

  // E2E tests need both Vite dev server (5173) and FastAPI backend (8765).
  // The Vite proxy forwards /api/* to 8765.
  // We only start the Vite dev server here; the backend must be started separately.
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: true,
    timeout: 30_000,
    env: {
      VITE_API_PROXY_TARGET: 'http://127.0.0.1:8765',
    },
  },
})
