export const WORKBENCH_PAGES = [
  { id: 'overview', label: '总览' },
  { id: 'chapters', label: '章节' },
  { id: 'outline', label: '大纲' },
  { id: 'settings', label: '设定' },
]

export const DEFAULT_WORKBENCH_PAGE = 'overview'
const WORKBENCH_PAGE_IDS = new Set(WORKBENCH_PAGES.map(page => page.id))
const IDLE_TASK = {
  status: 'idle',
  task: null,
  step: null,
  updatedAt: null,
  logs: [],
  result: null,
  error: null,
}

export function normalizeWorkbenchPage(page) {
  return WORKBENCH_PAGE_IDS.has(page) ? page : DEFAULT_WORKBENCH_PAGE
}

export function createInitialWorkbenchState(summary = null) {
  return {
    page: DEFAULT_WORKBENCH_PAGE,
    summary,
    currentTask: { ...IDLE_TASK },
    chatMessages: [],
    suggestedActions: [],
  }
}

export function buildOverviewModel(summary) {
  if (!summary) {
    return {
      project: null,
      progress: null,
      recentTasks: [],
      recentChanges: [],
      nextSuggestions: [],
    }
  }

  return {
    project: summary.project ?? null,
    progress: summary.progress ?? null,
    recentTasks: summary.recent_tasks ?? [],
    recentChanges: summary.recent_changes ?? [],
    nextSuggestions: summary.next_suggestions ?? [],
  }
}

export function buildTopBarModel({ page, summary, currentTask } = {}) {
  const normalizedTask = currentTask ?? IDLE_TASK
  return {
    title: summary?.project?.title ?? '未加载项目',
    pages: WORKBENCH_PAGES,
    activePage: normalizeWorkbenchPage(page),
    taskBadge: {
      status: normalizedTask.status ?? 'idle',
      label: normalizedTask.task ?? '空闲',
    },
  }
}

export function buildRightSidebarModel({
  context = null,
  chatMessages = [],
  suggestedActions = [],
  currentTask = null,
  chatPending = false,
  activePage = null,
} = {}) {
  const task = currentTask ?? IDLE_TASK
  const completionNotice =
    task.status === 'completed' && task.actionType
      ? buildCompletionNotice({ activePage, actionType: task.actionType, summary: task.result?.summary })
      : null
  const recoveryTips = buildFailureRecoveryTips(task)

  return {
    context,
    chatMessages,
    suggestedActions,
    currentTask: {
      ...IDLE_TASK,
      ...task,
      logs: task.logs ?? [],
      result: task.result ?? null,
      error: task.error ?? null,
      completionNotice,
      recoveryTips,
    },
    chatPending,
  }
}

export function resolveTargetPage(actionType) {
  if (actionType === 'write_chapter' || actionType === 'review_chapter') return 'chapters'
  if (actionType === 'plan_outline') return 'outline'
  if (actionType === 'inspect_setting') return 'settings'
  return null
}

const PAGE_LABELS = { chapters: '章节页', outline: '大纲页', settings: '设定页' }

export function buildCompletionNotice({ activePage, actionType, summary } = {}) {
  const targetPage = resolveTargetPage(actionType)
  const fallbackSummary = summary || '任务已完成'

  if (!targetPage) {
    return { hint: null, message: fallbackSummary, targetPage: null }
  }

  if (activePage === targetPage) {
    return {
      hint: 'refresh',
      message: `${fallbackSummary}，当前页面已刷新。`,
      targetPage,
    }
  }

  const label = PAGE_LABELS[targetPage] || '对应页面'
  return {
    hint: 'navigate',
    message: `${fallbackSummary}，可前往${label}查看结果。`,
    targetPage,
  }
}

export function buildFailureRecoveryTips(task) {
  if (!task || task.status !== 'failed') return []

  return [
    '返回当前页面继续编辑，确认内容未被意外修改。',
    '检查当前选中文件是否已保存，未保存的修改可能导致任务失败。',
    '重新发送聊天需求或重试该动作，必要时调整描述后再次执行。',
  ]
}

export function shouldConfirmAction(context) {
  return context?.dirty === true
}

export function shouldConfirmNavigation(context) {
  return context?.dirty === true
}

export function buildChatReplyModel(response, fallbackContext = null) {
  const scope = response?.scope ?? {
    page: fallbackContext?.page ?? null,
    selectedPath: fallbackContext?.selectedPath ?? null,
  }

  return {
    reply: response?.reply ?? '已收到。',
    reason: response?.reason ?? '',
    scope,
    suggestedActions: response?.suggested_actions ?? [],
  }
}
