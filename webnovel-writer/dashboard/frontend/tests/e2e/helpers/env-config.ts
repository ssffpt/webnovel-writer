import path from 'node:path'
import { config } from 'dotenv'

function loadEnv(): void {
  const testEnv = process.env.TEST_ENV
  if (!testEnv) {
    throw new Error(
      'TEST_ENV is not set. Please set TEST_ENV before running E2E tests.\n' +
        'Examples:\n' +
        '  TEST_ENV=local    npx playwright test\n' +
        '  TEST_ENV=dev      npx playwright test\n' +
        '  TEST_ENV=test     npx playwright test',
    )
  }

  const basePath = path.resolve(__dirname, '..')
  config({ path: path.join(basePath, '.env'), override: false })
  config({ path: path.join(basePath, `.env.${testEnv}`), override: false })
}

loadEnv()

export interface EnvConfig {
  baseUrl: string
  apiBaseUrl: string
  authFile: string
  testDataPrefix: string
}

let cached: EnvConfig | null = null

export function getEnvConfig(): EnvConfig {
  if (cached) return cached

  const baseUrl = process.env.BASE_URL
  if (!baseUrl) throw new Error('BASE_URL is not set in environment or .env file')

  const apiBaseUrl = process.env.API_BASE_URL || baseUrl
  const authFile = process.env.AUTH_FILE || 'e2e/.auth/user.json'
  const testDataPrefix = process.env.TEST_DATA_PREFIX || 'e2e_'

  cached = { baseUrl, apiBaseUrl, authFile, testDataPrefix }
  return cached
}
