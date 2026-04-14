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
} = {}) {
  return {
    context,
    chatMessages,
    suggestedActions,
    currentTask: {
      ...IDLE_TASK,
      ...(currentTask ?? {}),
      logs: currentTask?.logs ?? [],
      result: currentTask?.result ?? null,
      error: currentTask?.error ?? null,
    },
    chatPending,
  }
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
