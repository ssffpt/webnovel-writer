import { test as base } from '@playwright/test'
import { getEnvConfig } from '../helpers/env-config.js'

export const test = base.extend<{
  env: ReturnType<typeof getEnvConfig>
}>({
  env: async ({}, use) => {
    const env = getEnvConfig()
    await use(env)
  },
})

export { expect } from '@playwright/test'
