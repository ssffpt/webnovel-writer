import { test as setup, chromium } from '@playwright/test'
import path from 'node:path'
import fs from 'node:fs'

// 本应用（网文创作工作台）目前无登录认证流程。
// auth.setup.ts 保留作未来扩展。
// 目前基于 storageState 的认证对匿名应用不适用，故置为空操作。

setup('auth setup (placeholder)', async () => {
  // 若未来添加登录认证，在此处实现：
  // 1. 导航到登录页
  // 2. 填写凭据
  // 3. 点击登录
  // 4. 保存 storageState
  const authDir = path.resolve(__dirname, '..', '.auth')
  fs.mkdirSync(authDir, { recursive: true })
  // 空文件占位，保证后续 test 可正常读取 auth file 路径
  const authFile = path.join(authDir, 'user.json')
  if (!fs.existsSync(authFile)) {
    fs.writeFileSync(authFile, JSON.stringify({ cookies: [], origins: [] }), 'utf-8')
  }
})
