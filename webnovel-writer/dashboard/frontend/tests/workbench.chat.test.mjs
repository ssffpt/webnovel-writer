import test from 'node:test'
import assert from 'node:assert/strict'

const modulePath = new URL('../src/workbench/data.js', import.meta.url)

async function loadWorkbenchDataModule() {
  return import(modulePath)
}

test('buildChatReplyModel preserves reply, reason, scope and suggestedActions', async () => {
  const { buildChatReplyModel } = await loadWorkbenchDataModule()

  const response = {
    reply: '我会优先继续当前大纲规划。',
    suggested_actions: [
      { type: 'plan_outline', label: '生成当前卷纲', params: { path: '大纲/卷一.md' } },
    ],
    reason: '当前位于大纲页，且你希望继续，因此优先推荐大纲规划动作。',
    scope: { page: 'outline', selectedPath: '大纲/卷一.md' },
  }

  const model = buildChatReplyModel(response)

  assert.equal(model.reply, '我会优先继续当前大纲规划。')
  assert.equal(model.reason, '当前位于大纲页，且你希望继续，因此优先推荐大纲规划动作。')
  assert.deepEqual(model.scope, { page: 'outline', selectedPath: '大纲/卷一.md' })
  assert.deepEqual(model.suggestedActions, [
    { type: 'plan_outline', label: '生成当前卷纲', params: { path: '大纲/卷一.md' } },
  ])
})

test('buildChatReplyModel falls back to context when scope is missing', async () => {
  const { buildChatReplyModel } = await loadWorkbenchDataModule()

  const response = {
    reply: '已收到。',
    suggested_actions: [],
    reason: '根据当前聊天内容生成建议动作。',
    scope: null,
  }

  const fallbackContext = { page: 'chapters', selectedPath: '正文/第001章.md' }
  const model = buildChatReplyModel(response, fallbackContext)

  assert.deepEqual(model.scope, { page: 'chapters', selectedPath: '正文/第001章.md' })
})

test('buildChatReplyModel provides stable defaults for empty response', async () => {
  const { buildChatReplyModel } = await loadWorkbenchDataModule()

  const model = buildChatReplyModel(null)

  assert.equal(model.reply, '已收到。')
  assert.equal(model.reason, '')
  assert.deepEqual(model.scope, { page: null, selectedPath: null })
  assert.deepEqual(model.suggestedActions, [])
})

test('buildChatReplyModel maps suggested_actions to suggestedActions', async () => {
  const { buildChatReplyModel } = await loadWorkbenchDataModule()

  const response = {
    reply: '已识别为章节写作需求。',
    suggested_actions: [
      { type: 'write_chapter', label: '生成当前章节', params: { path: null } },
      { type: 'review_chapter', label: '审查当前章节', params: { path: null } },
    ],
    reason: '关键词匹配',
    scope: { page: 'chapters', selectedPath: null },
  }

  const model = buildChatReplyModel(response)

  assert.equal(model.suggestedActions.length, 2)
  assert.equal(model.suggestedActions[0].type, 'write_chapter')
  assert.equal(model.suggestedActions[1].type, 'review_chapter')
})
