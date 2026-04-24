import { describe, it, expect } from 'vitest'
import {
  normalizeWorkbenchPage,
  createInitialWorkbenchState,
  buildOverviewModel,
  buildTopBarModel,
  buildRightSidebarModel,
  resolveTargetPage,
  buildCompletionNotice,
  buildFailureRecoveryTips,
  shouldConfirmAction,
  shouldConfirmNavigation,
  getProjectStatus,
  getNextSuggestion,
  buildChatReplyModel,
  WORKBENCH_PAGES,
  DEFAULT_WORKBENCH_PAGE,
  PAGE_LABELS,
  OUTLINE_FIXED_NODES,
  volumeLabel,
  volumeRangeText,
} from '@/workbench/data.js'

// --- normalizeWorkbenchPage ---

describe('normalizeWorkbenchPage', () => {
  it('returns the page id when it is valid', () => {
    expect(normalizeWorkbenchPage('overview')).toBe('overview')
    expect(normalizeWorkbenchPage('outline')).toBe('outline')
    expect(normalizeWorkbenchPage('settings')).toBe('settings')
    expect(normalizeWorkbenchPage('chapters')).toBe('chapters')
  })

  it('returns overview for unknown page id', () => {
    expect(normalizeWorkbenchPage('unknown')).toBe('overview')
    expect(normalizeWorkbenchPage('')).toBe('overview')
    expect(normalizeWorkbenchPage(null)).toBe('overview')
    expect(normalizeWorkbenchPage(undefined)).toBe('overview')
  })
})

// --- createInitialWorkbenchState ---

describe('createInitialWorkbenchState', () => {
  it('returns default state with overview as page when no args given', () => {
    const state = createInitialWorkbenchState()
    expect(state.page).toBe(DEFAULT_WORKBENCH_PAGE)
    expect(state.summary).toBe(null)
    expect(state.currentTask).toEqual({
      status: 'idle',
      task: null,
      step: null,
      updatedAt: null,
      logs: [],
      result: null,
      error: null,
    })
    expect(state.chatMessages).toEqual([])
    expect(state.suggestedActions).toEqual([])
  })

  it('sets summary when provided', () => {
    const summary = { project: { title: '测试' } }
    const state = createInitialWorkbenchState(summary)
    expect(state.summary).toBe(summary)
  })
})

// --- buildOverviewModel ---

describe('buildOverviewModel', () => {
  it('returns empty model when summary is null', () => {
    const model = buildOverviewModel(null)
    expect(model.project).toBe(null)
    expect(model.progress).toBe(null)
    expect(model.recentTasks).toEqual([])
    expect(model.recentChanges).toEqual([])
    expect(model.nextSuggestions).toEqual([])
  })

  it('maps fields from summary when provided', () => {
    const summary = {
      project: { title: '我的小说', genre: '玄幻' },
      progress: { current_chapter: 3, total_words: 50000 },
      recent_tasks: [{ id: 1, description: '写作任务' }],
      recent_changes: [{ id: 2, description: '修改大纲' }],
      next_suggestions: [{ text: '开始写第4章' }],
    }
    const model = buildOverviewModel(summary)
    expect(model.project).toEqual({ title: '我的小说', genre: '玄幻' })
    expect(model.progress).toEqual({ current_chapter: 3, total_words: 50000 })
    expect(model.recentTasks).toEqual([{ id: 1, description: '写作任务' }])
    expect(model.recentChanges).toEqual([{ id: 2, description: '修改大纲' }])
    expect(model.nextSuggestions).toEqual([{ text: '开始写第4章' }])
  })

  it('handles summary with missing fields', () => {
    const summary = { project: { title: '小说' } }
    const model = buildOverviewModel(summary)
    expect(model.project).toEqual({ title: '小说' })
    expect(model.progress).toBe(null)
    expect(model.recentTasks).toEqual([])
    expect(model.recentChanges).toEqual([])
    expect(model.nextSuggestions).toEqual([])
  })
})

// --- buildTopBarModel ---

describe('buildTopBarModel', () => {
  it('uses project title when available', () => {
    const model = buildTopBarModel({
      page: 'chapters',
      summary: { project: { title: '仙侠小说' } },
      currentTask: null,
    })
    expect(model.title).toBe('仙侠小说')
    expect(model.pages).toBe(WORKBENCH_PAGES)
    expect(model.activePage).toBe('chapters')
    expect(model.taskBadge).toEqual({ status: 'idle', label: '空闲' })
  })

  it('falls back to 未加载项目 when no project title', () => {
    const model = buildTopBarModel({ page: 'outline', summary: {}, currentTask: null })
    expect(model.title).toBe('未加载项目')
  })

  it('uses currentTask status and label when provided', () => {
    const model = buildTopBarModel({
      summary: {},
      currentTask: { status: 'running', task: '正在写入第3章' },
    })
    expect(model.taskBadge).toEqual({ status: 'running', label: '正在写入第3章' })
  })

  it('defaults to idle when currentTask is missing status', () => {
    const model = buildTopBarModel({ summary: {}, currentTask: {} })
    expect(model.taskBadge).toEqual({ status: 'idle', label: '空闲' })
  })
})

// --- buildRightSidebarModel ---

describe('buildRightSidebarModel', () => {
  it('returns model with empty arrays when no args', () => {
    const model = buildRightSidebarModel()
    expect(model.chatMessages).toEqual([])
    expect(model.suggestedActions).toEqual([])
    expect(model.currentTask.logs).toEqual([])
    expect(model.currentTask.result).toBe(null)
    expect(model.currentTask.error).toBe(null)
  })

  it('merges provided currentTask fields', () => {
    const model = buildRightSidebarModel({
      currentTask: {
        status: 'completed',
        actionType: 'write_chapter',
        result: { summary: '第1章已完成' },
      },
      chatMessages: [{ text: '你好' }],
    })
    expect(model.chatMessages).toEqual([{ text: '你好' }])
    expect(model.currentTask.status).toBe('completed')
    expect(model.currentTask.result).toEqual({ summary: '第1章已完成' })
    expect(model.currentTask.completionNotice).not.toBe(null)
  })

  it('builds completionNotice when task is completed with actionType', () => {
    const model = buildRightSidebarModel({
      activePage: 'overview',
      currentTask: {
        status: 'completed',
        actionType: 'write_chapter',
        result: { summary: '第2章已完成' },
      },
    })
    expect(model.currentTask.completionNotice).toEqual({
      hint: 'navigate',
      message: '第2章已完成，可前往章节页查看结果。',
      targetPage: 'chapters',
    })
  })

  it('builds recoveryTips when task status is failed', () => {
    const model = buildRightSidebarModel({
      currentTask: { status: 'failed', error: '网络错误' },
    })
    expect(model.currentTask.recoveryTips).toHaveLength(3)
    expect(model.currentTask.recoveryTips[0]).toContain('继续编辑')
  })

  it('returns empty recoveryTips when task is not failed', () => {
    const model = buildRightSidebarModel({
      currentTask: { status: 'running' },
    })
    expect(model.currentTask.recoveryTips).toEqual([])
  })
})

// --- resolveTargetPage ---

describe('resolveTargetPage', () => {
  it('returns chapters for write_chapter and review_chapter', () => {
    expect(resolveTargetPage('write_chapter')).toBe('chapters')
    expect(resolveTargetPage('review_chapter')).toBe('chapters')
  })

  it('returns outline for plan_outline', () => {
    expect(resolveTargetPage('plan_outline')).toBe('outline')
  })

  it('returns settings for inspect_setting', () => {
    expect(resolveTargetPage('inspect_setting')).toBe('settings')
  })

  it('returns null for unknown actionType', () => {
    expect(resolveTargetPage('unknown')).toBe(null)
    expect(resolveTargetPage(null)).toBe(null)
    expect(resolveTargetPage(undefined)).toBe(null)
  })
})

// --- buildCompletionNotice ---

describe('buildCompletionNotice', () => {
  it('uses fallbackSummary when no targetPage', () => {
    const notice = buildCompletionNotice({ activePage: 'overview', actionType: 'unknown' })
    expect(notice.hint).toBe(null)
    expect(notice.message).toBe('任务已完成')
    expect(notice.targetPage).toBe(null)
  })

  it('returns refresh hint when activePage equals targetPage', () => {
    const notice = buildCompletionNotice({
      activePage: 'chapters',
      actionType: 'write_chapter',
      summary: '第1章已完成',
    })
    expect(notice.hint).toBe('refresh')
    expect(notice.message).toBe('第1章已完成，当前页面已刷新。')
    expect(notice.targetPage).toBe('chapters')
  })

  it('returns navigate hint when activePage differs from targetPage', () => {
    const notice = buildCompletionNotice({
      activePage: 'overview',
      actionType: 'write_chapter',
      summary: '第2章已完成',
    })
    expect(notice.hint).toBe('navigate')
    expect(notice.message).toBe('第2章已完成，可前往章节页查看结果。')
    expect(notice.targetPage).toBe('chapters')
  })

  it('uses custom summary in message', () => {
    const notice = buildCompletionNotice({
      activePage: 'overview',
      actionType: 'plan_outline',
      summary: '大纲已生成',
    })
    expect(notice.message).toBe('大纲已生成，可前往大纲页查看结果。')
  })
})

// --- buildFailureRecoveryTips ---

describe('buildFailureRecoveryTips', () => {
  it('returns 3 tips when task status is failed', () => {
    const tips = buildFailureRecoveryTips({ status: 'failed' })
    expect(tips).toHaveLength(3)
    expect(tips[0]).toContain('继续编辑')
    expect(tips[1]).toContain('检查当前选中文件')
    expect(tips[2]).toContain('重新发送')
  })

  it('returns empty array when task is null', () => {
    expect(buildFailureRecoveryTips(null)).toEqual([])
  })

  it('returns empty array when task status is not failed', () => {
    expect(buildFailureRecoveryTips({ status: 'running' })).toEqual([])
    expect(buildFailureRecoveryTips({ status: 'completed' })).toEqual([])
    expect(buildFailureRecoveryTips({ status: 'idle' })).toEqual([])
  })
})

// --- shouldConfirmAction / shouldConfirmNavigation ---

describe('shouldConfirmAction', () => {
  it('returns true when context.dirty is true', () => {
    expect(shouldConfirmAction({ dirty: true })).toBe(true)
  })

  it('returns false when context.dirty is false or missing', () => {
    expect(shouldConfirmAction({ dirty: false })).toBe(false)
    expect(shouldConfirmAction({})).toBe(false)
    expect(shouldConfirmAction(null)).toBe(false)
    expect(shouldConfirmAction(undefined)).toBe(false)
  })
})

describe('shouldConfirmNavigation', () => {
  it('returns true when context.dirty is true', () => {
    expect(shouldConfirmNavigation({ dirty: true })).toBe(true)
  })

  it('returns false otherwise', () => {
    expect(shouldConfirmNavigation({ dirty: false })).toBe(false)
    expect(shouldConfirmNavigation({})).toBe(false)
    expect(shouldConfirmNavigation(null)).toBe(false)
  })
})

// --- getProjectStatus ---

describe('getProjectStatus', () => {
  it('returns no-project when projectInfo is null', () => {
    expect(getProjectStatus(null)).toBe('no-project')
  })

  it('returns no-project when project_info is empty', () => {
    expect(getProjectStatus({ project_info: {} })).toBe('no-project')
    expect(getProjectStatus({ project: {} })).toBe('no-project')
  })

  it('returns no-project when all key fields are missing', () => {
    expect(getProjectStatus({ project_info: { title: '', genre: '' } })).toBe('no-project')
  })

  it('returns incomplete when title is missing', () => {
    expect(getProjectStatus({ project_info: { genre: '玄幻' } })).toBe('incomplete')
  })

  it('returns incomplete when genre is missing', () => {
    expect(getProjectStatus({ project_info: { title: '小说' } })).toBe('incomplete')
  })

  it('returns ready when title and genre are present', () => {
    expect(getProjectStatus({ project_info: { title: '小说', genre: '玄幻' } })).toBe('ready')
  })

  it('also works with project key', () => {
    expect(getProjectStatus({ project: { title: '小说', genre: '都市' } })).toBe('ready')
  })
})

// --- getNextSuggestion ---

describe('getNextSuggestion', () => {
  it('returns null when summary is null', () => {
    expect(getNextSuggestion(null)).toBe(null)
  })

  it('returns 开始写第1章 when progress is missing or empty (treats as chapter 0)', () => {
    // {} | {} = {}, then current_chapter || 0 = 0
    const suggestion = getNextSuggestion({})
    expect(suggestion).toEqual({
      text: '开始写第1章',
      action: 'write_chapter',
      params: { chapter: 1 },
    })
  })

  it('returns 开始写第1章 when current_chapter is 0', () => {
    const suggestion = getNextSuggestion({ progress: { current_chapter: 0 } })
    expect(suggestion).toEqual({
      text: '开始写第1章',
      action: 'write_chapter',
      params: { chapter: 1 },
    })
  })

  it('returns 开始写第1章 when current_chapter is undefined', () => {
    const suggestion = getNextSuggestion({ progress: {} })
    expect(suggestion).toEqual({
      text: '开始写第1章',
      action: 'write_chapter',
      params: { chapter: 1 },
    })
  })

  it('returns 写第N章 when current_chapter > 0', () => {
    const suggestion = getNextSuggestion({ progress: { current_chapter: 3 } })
    expect(suggestion).toEqual({
      text: '写第4章',
      action: 'write_chapter',
      params: { chapter: 4 },
    })
  })
})

// --- buildChatReplyModel ---

describe('buildChatReplyModel', () => {
  it('uses response.reply and response.reason when provided', () => {
    const model = buildChatReplyModel({
      reply: '好的，正在写第3章。',
      reason: '根据上下文，用户正在创作。',
      suggested_actions: [{ label: '继续' }],
    })
    expect(model.reply).toBe('好的，正在写第3章。')
    expect(model.reason).toBe('根据上下文，用户正在创作。')
    expect(model.suggestedActions).toEqual([{ label: '继续' }])
  })

  it('uses fallback when reply is missing', () => {
    const model = buildChatReplyModel({})
    expect(model.reply).toBe('已收到。')
    expect(model.reason).toBe('')
  })

  it('uses fallbackContext for scope when response.scope is missing', () => {
    const model = buildChatReplyModel(
      { reply: '收到' },
      { page: 'chapters', selectedPath: '/chapters/1' }
    )
    expect(model.scope).toEqual({ page: 'chapters', selectedPath: '/chapters/1' })
  })

  it('prefers response.scope over fallbackContext', () => {
    const model = buildChatReplyModel(
      { reply: '收到', scope: { page: 'outline' } },
      { page: 'chapters' }
    )
    expect(model.scope.page).toBe('outline')
  })

  it('handles null response and null fallbackContext', () => {
    const model = buildChatReplyModel(null, null)
    expect(model.reply).toBe('已收到。')
    expect(model.scope).toEqual({ page: null, selectedPath: null })
  })
})

// --- Exported constants ---

describe('exported constants', () => {
  it('WORKBENCH_PAGES has 4 pages', () => {
    expect(WORKBENCH_PAGES).toHaveLength(4)
    expect(WORKBENCH_PAGES.map(p => p.id)).toEqual(['overview', 'outline', 'settings', 'chapters'])
  })

  it('DEFAULT_WORKBENCH_PAGE is overview', () => {
    expect(DEFAULT_WORKBENCH_PAGE).toBe('overview')
  })

  it('PAGE_LABELS maps page ids to labels', () => {
    expect(PAGE_LABELS).toEqual({ chapters: '章节页', outline: '大纲页', settings: '设定页' })
  })
})

// --- OUTLINE_FIXED_NODES ---

describe('OUTLINE_FIXED_NODES', () => {
  it('has exactly 2 fixed nodes', () => {
    expect(OUTLINE_FIXED_NODES).toHaveLength(2)
  })

  it('contains master and highlights nodes', () => {
    const keys = OUTLINE_FIXED_NODES.map(n => n.key)
    expect(keys).toContain('master')
    expect(keys).toContain('highlights')
  })

  it('master node has correct path and label', () => {
    const master = OUTLINE_FIXED_NODES.find(n => n.key === 'master')
    expect(master.label).toBe('总纲')
    expect(master.path).toBe('大纲/总纲.md')
  })

  it('highlights node has correct path and label', () => {
    const highlights = OUTLINE_FIXED_NODES.find(n => n.key === 'highlights')
    expect(highlights.label).toBe('爽点规划')
    expect(highlights.path).toBe('大纲/爽点规划.md')
  })
})

// --- volumeLabel ---

describe('volumeLabel', () => {
  it('returns 第N卷 format', () => {
    expect(volumeLabel({ number: 1 })).toBe('第1卷')
    expect(volumeLabel({ number: 5 })).toBe('第5卷')
    expect(volumeLabel({ number: 12 })).toBe('第12卷')
  })
})

// --- volumeRangeText ---

describe('volumeRangeText', () => {
  it('returns empty string when chapter_range is missing', () => {
    expect(volumeRangeText({})).toBe('')
    expect(volumeRangeText({ chapter_range: null })).toBe('')
    expect(volumeRangeText({ chapter_range: undefined })).toBe('')
  })

  it('returns undefined-undefined章 when chapter_range is empty array (destructures to undefined)', () => {
    expect(volumeRangeText({ chapter_range: [] })).toBe('undefined-undefined章')
  })

  it('formats single chapter as N-N章', () => {
    expect(volumeRangeText({ chapter_range: [3, 3] })).toBe('3-3章')
  })

  it('formats range as start-end章', () => {
    expect(volumeRangeText({ chapter_range: [1, 5] })).toBe('1-5章')
    expect(volumeRangeText({ chapter_range: [10, 20] })).toBe('10-20章')
  })
})
