import test from 'node:test'
import assert from 'node:assert/strict'

const modulePath = new URL('../src/workbench/data.js', import.meta.url)

async function loadWorkbenchDataModule() {
  return import(modulePath)
}

test('normalizeWorkbenchPage falls back to overview for unknown page ids', async () => {
  const { normalizeWorkbenchPage } = await loadWorkbenchDataModule()

  assert.equal(normalizeWorkbenchPage('chapters'), 'chapters')
  assert.equal(normalizeWorkbenchPage('overview'), 'overview')
  assert.equal(normalizeWorkbenchPage('dashboard'), 'overview')
  assert.equal(normalizeWorkbenchPage(undefined), 'overview')
  assert.equal(normalizeWorkbenchPage(null), 'overview')
})

test('buildTopBarModel derives title, pages, activePage and task badge', async () => {
  const { buildTopBarModel, WORKBENCH_PAGES } = await loadWorkbenchDataModule()

  const model = buildTopBarModel({
    page: 'outline',
    summary: { project: { title: '测试小说' } },
    currentTask: { status: 'running', task: '生成章纲' },
  })

  assert.equal(model.title, '测试小说')
  assert.equal(model.activePage, 'outline')
  assert.deepEqual(model.pages, WORKBENCH_PAGES)
  assert.deepEqual(model.taskBadge, {
    status: 'running',
    label: '生成章纲',
  })
})

test('buildTopBarModel falls back to default title and idle badge', async () => {
  const { buildTopBarModel } = await loadWorkbenchDataModule()

  const model = buildTopBarModel({
    page: 'invalid-page',
    summary: null,
    currentTask: null,
  })

  assert.equal(model.title, '未加载项目')
  assert.equal(model.activePage, 'overview')
  assert.deepEqual(model.taskBadge, {
    status: 'idle',
    label: '空闲',
  })
})

test('buildRightSidebarModel preserves context and normalizes empty collections', async () => {
  const { buildRightSidebarModel } = await loadWorkbenchDataModule()

  const model = buildRightSidebarModel({
    context: {
      page: 'chapters',
      selectedPath: '正文/第001章.md',
      dirty: true,
    },
    chatMessages: [{ role: 'user', content: '帮我续写' }],
    suggestedActions: [{ type: 'write_chapter', label: '生成当前章节' }],
    currentTask: { status: 'pending', task: '生成当前章节', step: '等待确认', updatedAt: 'now' },
  })

  assert.deepEqual(model.context, {
    page: 'chapters',
    selectedPath: '正文/第001章.md',
    dirty: true,
  })
  assert.deepEqual(model.chatMessages, [{ role: 'user', content: '帮我续写' }])
  assert.deepEqual(model.suggestedActions, [{ type: 'write_chapter', label: '生成当前章节' }])
  assert.deepEqual(model.currentTask, {
    status: 'pending',
    task: '生成当前章节',
    step: '等待确认',
    updatedAt: 'now',
    logs: [],
    result: null,
    error: null,
    completionNotice: null,
    recoveryTips: [],
  })
  assert.equal(model.chatPending, false)
})

test('buildRightSidebarModel provides stable empty defaults', async () => {
  const { buildRightSidebarModel } = await loadWorkbenchDataModule()

  const model = buildRightSidebarModel({})

  assert.deepEqual(model.context, null)
  assert.deepEqual(model.chatMessages, [])
  assert.deepEqual(model.suggestedActions, [])
  assert.deepEqual(model.currentTask, {
    status: 'idle',
    task: null,
    step: null,
    updatedAt: null,
    logs: [],
    result: null,
    error: null,
    completionNotice: null,
    recoveryTips: [],
  })
  assert.equal(model.chatPending, false)
})
