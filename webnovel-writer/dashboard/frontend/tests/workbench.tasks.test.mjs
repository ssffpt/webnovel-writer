import test from 'node:test'
import assert from 'node:assert/strict'

const modulePath = new URL('../src/workbench/data.js', import.meta.url)

async function loadWorkbenchDataModule() {
  return import(modulePath)
}

test('buildRightSidebarModel preserves task logs and error state', async () => {
  const { buildRightSidebarModel } = await loadWorkbenchDataModule()

  const model = buildRightSidebarModel({
    currentTask: {
      status: 'failed',
      task: '检查当前设定冲突',
      step: '执行失败',
      updatedAt: '2026-04-14T10:00:00Z',
      logs: [
        { createdAt: '2026-04-14T09:59:58Z', message: '任务开始执行' },
        { createdAt: '2026-04-14T09:59:59Z', message: '检查当前设定冲突 执行失败' },
      ],
      result: null,
      error: '检查当前设定冲突 执行失败',
    },
  })

  assert.deepEqual(model.currentTask, {
    status: 'failed',
    task: '检查当前设定冲突',
    step: '执行失败',
    updatedAt: '2026-04-14T10:00:00Z',
    logs: [
      { createdAt: '2026-04-14T09:59:58Z', message: '任务开始执行' },
      { createdAt: '2026-04-14T09:59:59Z', message: '检查当前设定冲突 执行失败' },
    ],
    result: null,
    error: '检查当前设定冲突 执行失败',
    completionNotice: null,
    recoveryTips: [
      '返回当前页面继续编辑，确认内容未被意外修改。',
      '检查当前选中文件是否已保存，未保存的修改可能导致任务失败。',
      '重新发送聊天需求或重试该动作，必要时调整描述后再次执行。',
    ],
  })
})

test('buildRightSidebarModel preserves completed task result summary', async () => {
  const { buildRightSidebarModel } = await loadWorkbenchDataModule()

  const model = buildRightSidebarModel({
    currentTask: {
      status: 'completed',
      task: '生成当前卷纲',
      step: '执行完成',
      updatedAt: '2026-04-14T10:00:00Z',
      logs: [
        { createdAt: '2026-04-14T09:59:58Z', message: '任务开始执行' },
        { createdAt: '2026-04-14T10:00:00Z', message: '任务执行完成' },
      ],
      result: {
        summary: '生成当前卷纲 已完成（已执行 preflight + 文件校验）',
      },
      error: null,
    },
  })

  assert.equal(model.currentTask.status, 'completed')
  assert.equal(model.currentTask.result.summary, '生成当前卷纲 已完成（已执行 preflight + 文件校验）')
  assert.equal(model.currentTask.error, null)
  assert.equal(model.currentTask.logs.length, 2)
})

