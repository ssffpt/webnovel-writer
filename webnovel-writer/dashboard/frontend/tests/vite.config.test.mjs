import test from 'node:test'
import assert from 'node:assert/strict'

const configModulePath = new URL('../vite.config.js', import.meta.url)

async function loadViteConfig() {
  const mod = await import(configModulePath)
  return mod.default
}

test('vite dev proxy forwards /api to the dashboard default backend port', async () => {
  const config = await loadViteConfig()

  assert.equal(config.server?.proxy?.['/api'], 'http://127.0.0.1:8765')
})
