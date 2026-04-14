import test from 'node:test'
import assert from 'node:assert/strict'

const modulePath = new URL('../src/workbench/data.js', import.meta.url)

async function loadPhase4Module() {
  return import(modulePath)
}

// ── resolveTargetPage ────────────────────────────────────────────────

test('resolveTargetPage maps write_chapter to chapters', async () => {
  const { resolveTargetPage } = await loadPhase4Module()
  assert.equal(resolveTargetPage('write_chapter'), 'chapters')
})

test('resolveTargetPage maps review_chapter to chapters', async () => {
  const { resolveTargetPage } = await loadPhase4Module()
  assert.equal(resolveTargetPage('review_chapter'), 'chapters')
})

test('resolveTargetPage maps plan_outline to outline', async () => {
  const { resolveTargetPage } = await loadPhase4Module()
  assert.equal(resolveTargetPage('plan_outline'), 'outline')
})

test('resolveTargetPage maps inspect_setting to settings', async () => {
  const { resolveTargetPage } = await loadPhase4Module()
  assert.equal(resolveTargetPage('inspect_setting'), 'settings')
})

test('resolveTargetPage returns null for unknown action type', async () => {
  const { resolveTargetPage } = await loadPhase4Module()
  assert.equal(resolveTargetPage('unknown_action'), null)
})

test('resolveTargetPage returns null when action type is missing', async () => {
  const { resolveTargetPage } = await loadPhase4Module()
  assert.equal(resolveTargetPage(null), null)
  assert.equal(resolveTargetPage(undefined), null)
})

// ── buildCompletionNotice ────────────────────────────────────────────

test('buildCompletionNotice returns in-page refresh hint when already on target page', async () => {
  const { buildCompletionNotice } = await loadPhase4Module()

  const notice = buildCompletionNotice({
    activePage: 'chapters',
    actionType: 'write_chapter',
    summary: '生成章节内容 已完成',
  })

  assert.equal(notice.hint, 'refresh')
  assert.ok(notice.message.includes('当前页面已刷新'))
  assert.ok(notice.message.includes('生成章节内容 已完成'))
  assert.equal(notice.targetPage, 'chapters')
})

test('buildCompletionNotice returns navigate hint when not on target page', async () => {
  const { buildCompletionNotice } = await loadPhase4Module()

  const notice = buildCompletionNotice({
    activePage: 'overview',
    actionType: 'write_chapter',
    summary: '生成章节内容 已完成',
  })

  assert.equal(notice.hint, 'navigate')
  assert.ok(notice.message.includes('章节页'))
  assert.ok(notice.message.includes('查看结果'))
  assert.equal(notice.targetPage, 'chapters')
})

test('buildCompletionNotice returns navigate hint for outline from chapters page', async () => {
  const { buildCompletionNotice } = await loadPhase4Module()

  const notice = buildCompletionNotice({
    activePage: 'chapters',
    actionType: 'plan_outline',
    summary: '生成大纲 已完成',
  })

  assert.equal(notice.hint, 'navigate')
  assert.ok(notice.message.includes('大纲页'))
  assert.ok(notice.message.includes('查看结果'))
  assert.equal(notice.targetPage, 'outline')
})

test('buildCompletionNotice returns navigate hint for settings from outline page', async () => {
  const { buildCompletionNotice } = await loadPhase4Module()

  const notice = buildCompletionNotice({
    activePage: 'outline',
    actionType: 'inspect_setting',
    summary: '设定检查 已完成',
  })

  assert.equal(notice.hint, 'navigate')
  assert.ok(notice.message.includes('设定页'))
  assert.ok(notice.message.includes('查看结果'))
  assert.equal(notice.targetPage, 'settings')
})

test('buildCompletionNotice falls back when action type has no target page', async () => {
  const { buildCompletionNotice } = await loadPhase4Module()

  const notice = buildCompletionNotice({
    activePage: 'chapters',
    actionType: 'unknown_action',
    summary: '任务已完成',
  })

  assert.equal(notice.hint, null)
  assert.equal(notice.targetPage, null)
  assert.ok(notice.message.includes('任务已完成'))
})

test('buildCompletionNotice uses default summary when none provided', async () => {
  const { buildCompletionNotice } = await loadPhase4Module()

  const notice = buildCompletionNotice({
    activePage: 'chapters',
    actionType: 'write_chapter',
  })

  assert.equal(notice.hint, 'refresh')
  assert.ok(notice.message.includes('任务已完成'))
  assert.ok(notice.message.includes('当前页面已刷新'))
})

// ── buildFailureRecoveryTips ─────────────────────────────────────────

test('buildFailureRecoveryTips returns actionable recovery suggestions', async () => {
  const { buildFailureRecoveryTips } = await loadPhase4Module()

  const tips = buildFailureRecoveryTips({
    status: 'failed',
    task: '生成章节内容',
    error: '执行失败',
  })

  assert.ok(Array.isArray(tips))
  assert.ok(tips.length >= 3)
})

test('buildFailureRecoveryTips includes "return to edit" suggestion', async () => {
  const { buildFailureRecoveryTips } = await loadPhase4Module()

  const tips = buildFailureRecoveryTips({
    status: 'failed',
    task: '生成章节内容',
    error: '执行失败',
  })

  const hasEditTip = tips.some(t => t.includes('编辑') || t.includes('继续'))
  assert.ok(hasEditTip, 'should include a tip about returning to edit')
})

test('buildFailureRecoveryTips includes "check save state" suggestion', async () => {
  const { buildFailureRecoveryTips } = await loadPhase4Module()

  const tips = buildFailureRecoveryTips({
    status: 'failed',
    task: '生成章节内容',
    error: '执行失败',
  })

  const hasSaveTip = tips.some(t => t.includes('保存'))
  assert.ok(hasSaveTip, 'should include a tip about checking save state')
})

test('buildFailureRecoveryTips includes "retry" suggestion', async () => {
  const { buildFailureRecoveryTips } = await loadPhase4Module()

  const tips = buildFailureRecoveryTips({
    status: 'failed',
    task: '生成章节内容',
    error: '执行失败',
  })

  const hasRetryTip = tips.some(t => t.includes('重试') || t.includes('重新'))
  assert.ok(hasRetryTip, 'should include a tip about retrying')
})

test('buildFailureRecoveryTips returns empty array for non-failed task', async () => {
  const { buildFailureRecoveryTips } = await loadPhase4Module()

  const tips = buildFailureRecoveryTips({
    status: 'completed',
    task: '生成章节内容',
    error: null,
  })

  assert.deepEqual(tips, [])
})

test('buildFailureRecoveryTips returns empty array for idle task', async () => {
  const { buildFailureRecoveryTips } = await loadPhase4Module()

  const tips = buildFailureRecoveryTips({
    status: 'idle',
    task: null,
    error: null,
  })

  assert.deepEqual(tips, [])
})

// ── buildRightSidebarModel Phase 4 extensions ────────────────────────

test('buildRightSidebarModel includes completionNotice for completed task', async () => {
  const { buildRightSidebarModel } = await loadPhase4Module()

  const model = buildRightSidebarModel({
    currentTask: {
      status: 'completed',
      task: '生成章节内容',
      step: '执行完成',
      updatedAt: '2026-04-14T10:00:00Z',
      logs: [],
      result: { summary: '生成章节内容 已完成' },
      error: null,
      actionType: 'write_chapter',
    },
    activePage: 'overview',
  })

  assert.ok(model.currentTask.completionNotice)
  assert.equal(model.currentTask.completionNotice.hint, 'navigate')
  assert.ok(model.currentTask.completionNotice.message.includes('章节页'))
  assert.equal(model.currentTask.completionNotice.targetPage, 'chapters')
})

test('buildRightSidebarModel includes refresh hint when already on target page', async () => {
  const { buildRightSidebarModel } = await loadPhase4Module()

  const model = buildRightSidebarModel({
    currentTask: {
      status: 'completed',
      task: '生成章节内容',
      step: '执行完成',
      updatedAt: '2026-04-14T10:00:00Z',
      logs: [],
      result: { summary: '生成章节内容 已完成' },
      error: null,
      actionType: 'write_chapter',
    },
    activePage: 'chapters',
  })

  assert.ok(model.currentTask.completionNotice)
  assert.equal(model.currentTask.completionNotice.hint, 'refresh')
  assert.ok(model.currentTask.completionNotice.message.includes('当前页面已刷新'))
})

test('buildRightSidebarModel includes recoveryTips for failed task', async () => {
  const { buildRightSidebarModel } = await loadPhase4Module()

  const model = buildRightSidebarModel({
    currentTask: {
      status: 'failed',
      task: '生成章节内容',
      step: '执行失败',
      updatedAt: '2026-04-14T10:00:00Z',
      logs: [],
      result: null,
      error: '执行失败',
    },
  })

  assert.ok(Array.isArray(model.currentTask.recoveryTips))
  assert.ok(model.currentTask.recoveryTips.length >= 3)
})

test('buildRightSidebarModel has no completionNotice for running task', async () => {
  const { buildRightSidebarModel } = await loadPhase4Module()

  const model = buildRightSidebarModel({
    currentTask: {
      status: 'running',
      task: '生成章节内容',
      step: '执行中',
      updatedAt: '2026-04-14T10:00:00Z',
      logs: [],
      result: null,
      error: null,
      actionType: 'write_chapter',
    },
    activePage: 'chapters',
  })

  assert.equal(model.currentTask.completionNotice, null)
})

test('buildRightSidebarModel has no recoveryTips for idle task', async () => {
  const { buildRightSidebarModel } = await loadPhase4Module()

  const model = buildRightSidebarModel({
    currentTask: {
      status: 'idle',
    },
  })

  assert.deepEqual(model.currentTask.recoveryTips, [])
})

// ── shouldConfirmAction ──────────────────────────────────────────────

test('shouldConfirmAction returns true when context is dirty', async () => {
  const { shouldConfirmAction } = await loadPhase4Module()

  assert.equal(shouldConfirmAction({ dirty: true }), true)
})

test('shouldConfirmAction returns false when context is not dirty', async () => {
  const { shouldConfirmAction } = await loadPhase4Module()

  assert.equal(shouldConfirmAction({ dirty: false }), false)
})

test('shouldConfirmAction returns false when context is null', async () => {
  const { shouldConfirmAction } = await loadPhase4Module()

  assert.equal(shouldConfirmAction(null), false)
})

test('shouldConfirmAction returns false when context is undefined', async () => {
  const { shouldConfirmAction } = await loadPhase4Module()

  assert.equal(shouldConfirmAction(undefined), false)
})

test('shouldConfirmAction returns false when context lacks dirty field', async () => {
  const { shouldConfirmAction } = await loadPhase4Module()

  assert.equal(shouldConfirmAction({}), false)
})

// ── shouldConfirmNavigation ──────────────────────────────────────────

test('shouldConfirmNavigation returns true when context is dirty', async () => {
  const { shouldConfirmNavigation } = await loadPhase4Module()

  assert.equal(shouldConfirmNavigation({ dirty: true }), true)
})

test('shouldConfirmNavigation returns false when context is not dirty', async () => {
  const { shouldConfirmNavigation } = await loadPhase4Module()

  assert.equal(shouldConfirmNavigation({ dirty: false }), false)
})

test('shouldConfirmNavigation returns false when context is null', async () => {
  const { shouldConfirmNavigation } = await loadPhase4Module()

  assert.equal(shouldConfirmNavigation(null), false)
})
