import { Page } from '@playwright/test'

/**
 * BasePage — 所有 POM 的基类，提供跨页面通用方法。
 */
export abstract class BasePage {
  readonly page: Page

  constructor(page: Page) {
    this.page = page
  }

  /**
   * 等待页面加载完成（基础实现，可被子类重写）
   */
  async waitForLoad(): Promise<void> {
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * 通用 toast/dialog 关闭（若无则 no-op）
   */
  protected async dismissAnyModal(): Promise<void> {
    const overlay = this.page.locator('.conflict-dialog-overlay')
    if (await overlay.isVisible()) {
      const continueBtn = this.page.getByRole('button', { name: '继续' })
      if (await continueBtn.isVisible()) {
        await continueBtn.click()
        await this.page.waitForSelector('.conflict-dialog-overlay', { state: 'hidden' })
      }
    }
  }
}
