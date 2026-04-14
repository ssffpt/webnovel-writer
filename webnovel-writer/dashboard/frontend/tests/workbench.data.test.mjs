import test from 'node:test'
import assert from 'node:assert/strict'

const modulePath = new URL('../src/workbench/data.js', import.meta.url)

async function loadWorkbenchDataModule() {
  return import(modulePath)
}

test('WORKBENCH_PAGES exposes the four top-level workbench pages in order', async () => {
  const { WORKBENCH_PAGES } = await loadWorkbenchDataModule()

  assert.deepEqual(WORKBENCH_PAGES, [
    { id: 'overview', label: '总览' },
    { id: 'chapters', label: '章节' },
    { id: 'outline', label: '大纲' },
    { id: 'settings', label: '设定' },
  ])
})

test('DEFAULT_WORKBENCH_PAGE is overview', async () => {
  const { DEFAULT_WORKBENCH_PAGE } = await loadWorkbenchDataModule()

  assert.equal(DEFAULT_WORKBENCH_PAGE, 'overview')
})

test('createInitialWorkbenchState builds the shell defaults from summary data', async () => {
  const { createInitialWorkbenchState } = await loadWorkbenchDataModule()

  const state = createInitialWorkbenchState({
    project: { title: '测试小说' },
    recent_tasks: [{ id: 't-1', title: '最近任务' }],
  })

  assert.equal(state.page, 'overview')
  assert.deepEqual(state.summary, {
    project: { title: '测试小说' },
    recent_tasks: [{ id: 't-1', title: '最近任务' }],
  })
  assert.deepEqual(state.currentTask, {
    status: 'idle',
    task: null,
    step: null,
    updatedAt: null,
    logs: [],
    result: null,
    error: null,
  })
  assert.deepEqual(state.chatMessages, [])
  assert.deepEqual(state.suggestedActions, [])
})

test('createInitialWorkbenchState falls back safely when summary is missing', async () => {
  const { createInitialWorkbenchState } = await loadWorkbenchDataModule()

  const state = createInitialWorkbenchState()

  assert.equal(state.page, 'overview')
  assert.equal(state.summary, null)
  assert.deepEqual(state.currentTask, {
    status: 'idle',
    task: null,
    step: null,
    updatedAt: null,
    logs: [],
    result: null,
    error: null,
  })
  assert.deepEqual(state.chatMessages, [])
  assert.deepEqual(state.suggestedActions, [])
})

test('buildOverviewModel returns stable empty lists for a missing summary', async () => {
  const { buildOverviewModel } = await loadWorkbenchDataModule()

  const model = buildOverviewModel(null)

  assert.deepEqual(model, {
    project: null,
    progress: null,
    recentTasks: [],
    recentChanges: [],
    nextSuggestions: [],
  })
})
