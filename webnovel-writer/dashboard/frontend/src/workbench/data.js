export const WORKBENCH_PAGES = [
  { id: 'overview', label: '总览', number: '①' },
  { id: 'outline', label: '大纲', number: '②' },
  { id: 'settings', label: '设定', number: '③' },
  { id: 'chapters', label: '章节', number: '④' },
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

export const PAGE_LABELS = { chapters: '章节页', outline: '大纲页', settings: '设定页' }

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

export function getProjectStatus(projectInfo) {
  if (!projectInfo) return 'no-project';
  const pi = projectInfo.project_info || projectInfo.project || {};
  if (!pi.title || !pi.genre) return 'incomplete';
  return 'ready';
}

export function getNextSuggestion(summary) {
  if (!summary) return null;
  const progress = summary.progress || {};
  const chapter = progress.current_chapter || 0;
  if (chapter === 0) {
    return { text: '开始写第1章', action: 'write_chapter', params: { chapter: 1 } };
  }
  return { text: `写第${chapter + 1}章`, action: 'write_chapter', params: { chapter: chapter + 1 } };
}

export const ENTITY_TYPE_MAP = {
  '角色': { label: '人物', icon: '👤' },
  '势力': { label: '势力', icon: '🏛' },
  '地点': { label: '地点', icon: '📍' },
  '物品': { label: '物品', icon: '💎' },
  '招式': { label: '招式', icon: '⚔️' },
};
export const ENTITY_FILTER_CATEGORIES = ['全部', '人物', '势力', '地点', '物品', '招式'];
// 前端筛选标签的 type 映射（显示名 → 数据库 type 值）
export const FILTER_TO_DB_TYPE = {
  '人物': '角色',
  '势力': '势力',
  '地点': '地点',
  '物品': '物品',
  '招式': '招式',
};

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
